# src/generator/cv_full_analyzer.py
"""
Orquesta los 6 entregables del análisis completo ATS:
  A) Diagnóstico de encaje
  B) Tabla de keywords ATS
  C) Plan de cambios priorizado
  D) CV reescrito en texto plano
  E) Dos variantes Resumen + Skills
  F) Checklist ATS final
"""

import json
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Importar prompts
from config.prompts import (
    ATS_SYSTEM_PROMPT,
    DIAGNOSIS_PROMPT,
    KEYWORDS_PROMPT,
    CHANGES_PROMPT,
    CV_REWRITE_PROMPT,
    VARIANTS_PROMPT,
    ATS_CHECKLIST_PROMPT,
    EXTRACT_CV_INSIGHTS_PROMPT,
)

# Importar LM Studio client
try:
    from src.llm.lmstudio_client import lmstudio_client
except ImportError:
    lmstudio_client = None


# ─────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────

def _cv_to_text(cv_data: dict) -> str:
    """Convierte el diccionario de CV parseado a texto plano para los prompts."""
    parts = []

    personal = cv_data.get("personal_info", {})
    if personal:
        parts.append(f"NOMBRE: {personal.get('name', '')}")
        if personal.get("email"):
            parts.append(f"Email: {personal['email']}")
        if personal.get("phone"):
            parts.append(f"Teléfono: {personal['phone']}")
        if personal.get("location"):
            parts.append(f"Ubicación: {personal['location']}")

    summary = cv_data.get("summary") or cv_data.get("profile", "")
    if summary:
        parts.append(f"\nRESUMEN PROFESIONAL:\n{summary}")

    experience = cv_data.get("experience", [])
    if experience:
        parts.append("\nEXPERIENCIA PROFESIONAL:")
        for exp in experience:
            title = exp.get("title", "")
            company = exp.get("company", "")
            period = exp.get("period", "")
            parts.append(f"  {title} | {company} | {period}")
            for desc in (exp.get("description") or [])[:5]:
                if isinstance(desc, str) and desc.strip():
                    parts.append(f"    - {desc.strip()}")

    skills = cv_data.get("skills", {})
    if isinstance(skills, dict):
        tech = skills.get("technical", [])
        other = skills.get("other", [])
        if tech:
            parts.append(f"\nSKILLS TÉCNICAS: {', '.join(tech)}")
        if other:
            parts.append(f"OTRAS SKILLS: {', '.join(other)}")
    elif isinstance(skills, list):
        parts.append(f"\nSKILLS: {', '.join(skills)}")

    education = cv_data.get("education", [])
    if education:
        parts.append("\nEDUCACIÓN:")
        for edu in education:
            if isinstance(edu, dict):
                parts.append(f"  {edu.get('degree', '')} - {edu.get('institution', '')} {edu.get('year', '')}")
            elif isinstance(edu, str):
                parts.append(f"  {edu}")

    projects = cv_data.get("projects", [])
    if projects:
        parts.append("\nPROYECTOS:")
        for proj in projects:
            if isinstance(proj, dict):
                parts.append(f"  {proj.get('name', '')} - {proj.get('description', '')}")

    languages = cv_data.get("languages", [])
    if languages:
        parts.append(f"\nIDIOMAS: {', '.join(languages) if isinstance(languages, list) else languages}")

    raw = cv_data.get("raw_text", "")
    if raw and len("\n".join(parts)) < 300:
        # Fallback si el CV parseado tiene muy poca info
        parts.append(f"\nTEXTO COMPLETO DEL CV:\n{raw[:3000]}")

    return "\n".join(parts)


def _job_to_text(job_data: dict) -> str:
    """Convierte el diccionario de la oferta a texto plano para los prompts."""
    parts = []
    if job_data.get("title"):
        parts.append(f"PUESTO: {job_data['title']}")
    if job_data.get("seniority"):
        parts.append(f"Seniority: {job_data['seniority']}")
    if job_data.get("location"):
        parts.append(f"Ubicación: {job_data['location']}")
    if job_data.get("years_experience"):
        parts.append(f"Años de experiencia requeridos: {job_data['years_experience']}")
    if job_data.get("salary_range"):
        parts.append(f"Salario: {job_data['salary_range']}")
    if job_data.get("must_have"):
        reqs = "\n".join(f"- {r}" for r in job_data["must_have"])
        parts.append(f"\nREQUISITOS OBLIGATORIOS:\n{reqs}")
    if job_data.get("nice_to_have"):
        reqs = "\n".join(f"- {r}" for r in job_data["nice_to_have"])
        parts.append(f"\nREQUISITOS DESEABLES:\n{reqs}")
    if job_data.get("description"):
        parts.append(f"\nDESCRIPCIÓN COMPLETA:\n{job_data['description'][:2000]}")
    if job_data.get("raw_text") and not job_data.get("description"):
        parts.append(f"\nDESCRIPCIÓN:\n{job_data['raw_text'][:2000]}")
    return "\n".join(parts)


def _safe_json(response: str, fallback: dict) -> dict:
    """
    Extrae JSON de la respuesta del LLM con manejo robusto de errores.
    Gestiona:
    - Bloques <think>...</think> (DeepSeek, Qwen-thinking)
    - Bloques markdown ```json ... ```
    - JSON directo
    - Respuesta parcial/truncada
    """
    if not response:
        return fallback

    # 1. Eliminar bloques <think>...</think>
    text = re.sub(r"<think>[\s\S]*?</think>", "", response, flags=re.DOTALL).strip()

    # 2. Extraer contenido de bloque ```json ... ``` o ``` ... ```
    code_block = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.DOTALL)
    if code_block:
        candidate = code_block.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            text = candidate  # intentar parsear el contenido del bloque igualmente

    # 3. Buscar el bloque JSON más externo {…}
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            # Intentar arreglar JSON truncado añadiendo cierres faltantes
            try:
                fixed = candidate + "]}" * candidate.count("[") + "}" * (
                    candidate.count("{") - candidate.count("}")
                )
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

    # 4. Último intento con el texto completo limpio
    try:
        return json.loads(text.strip())
    except Exception:
        logger.warning("No se pudo parsear JSON del LLM, usando fallback.")
        return fallback


def _llm(prompt: str, max_tokens: int = 2000) -> Optional[str]:
    """Llama al LLM con el system prompt de ATS."""
    if lmstudio_client and lmstudio_client.available:
        try:
            return lmstudio_client.chat_completion(
                prompt,
                ATS_SYSTEM_PROMPT,
                temperature=0.4,
                max_tokens=max_tokens,
            )
        except Exception as e:  # noqa: BLE001
            logger.error("Error llamando a LM Studio: %s", e)
    return None


# ─────────────────────────────────────────────────────────
#  Clase principal
# ─────────────────────────────────────────────────────────

class CVFullAnalyzer:
    """
    Genera los 6 entregables del análisis completo ATS a partir de
    cv_data (dict parseado), job_data (dict parseado) y preferencias del usuario.
    """

    def __init__(self):
        self.llm_available = lmstudio_client is not None and lmstudio_client.available

    # ── Extracción automática de logros y stack ──
    def _extract_cv_insights(self, cv_text: str):
        """
        Usa el LLM para extraer logros medibles y stack tecnológico del CV.
        Devuelve (logros_str, stack_str) como cadenas de texto formateadas.
        """
        logger.info("Extrayendo logros y stack del CV automáticamente...")
        prompt = EXTRACT_CV_INSIGHTS_PROMPT.format(cv_text=cv_text)
        response = _llm(prompt)
        if response:
            data = _safe_json(response, {})
            logros_list = data.get("logros", [])
            stack_list = data.get("stack", [])
            if logros_list or stack_list:
                logros_str = "\n".join(f"- {l}" for l in logros_list)
                stack_str = ", ".join(stack_list)
                logger.info(
                    "Extraídos %d logros y %d elementos de stack",
                    len(logros_list),
                    len(stack_list),
                )
                return logros_str, stack_str

        # Fallback: extraer skills técnicas del CV como stack
        skills_section = re.search(
            r"SKILLS[^\n]*\n(.+?)(?=\n[A-Z]{3,}|\Z)", cv_text, re.DOTALL | re.IGNORECASE
        )
        stack_fallback = ""
        if skills_section:
            stack_fallback = skills_section.group(1).strip()[:300]
        return "", stack_fallback

    def analyze(
        self,
        cv_data: dict,
        job_data: dict,
        idioma: str = "ES",
        longitud: str = "2 páginas",
        pais: str = "",
        rol_objetivo: str = "",
        nivel: str = "",
        logros: str = "",
        stack: str = "",
    ) -> Dict[str, object]:
        """
        Ejecuta el análisis completo y devuelve un diccionario con los 6 entregables.

        Returns:
            {
                "A_diagnosis": dict,
                "B_keywords": dict,
                "C_changes": dict,
                "D_cv_rewritten": str,
                "E_variants": dict,
                "F_checklist": dict,
                "llm_used": bool,
            }
        """
        cv_text = _cv_to_text(cv_data)
        job_text = _job_to_text(job_data)

        logger.info("Iniciando análisis completo ATS...")

        # Auto-extraer logros y stack del CV si el usuario no los proporcionó
        if not logros.strip() or not stack.strip():
            logros_auto, stack_auto = self._extract_cv_insights(cv_text)
            if not logros.strip():
                logros = logros_auto
            if not stack.strip():
                stack = stack_auto

        a = self._deliverable_a(cv_text, job_text, idioma, longitud, rol_objetivo, nivel)
        b = self._deliverable_b(cv_text, job_text)
        c = self._deliverable_c(cv_text, job_text, a)
        d = self._deliverable_d(cv_text, job_text, idioma, longitud, rol_objetivo, nivel, logros, stack)
        e = self._deliverable_e(cv_text, job_text, idioma, rol_objetivo, nivel)
        f = self._deliverable_f(job_text, d)

        return {
            "A_diagnosis": a,
            "B_keywords": b,
            "C_changes": c,
            "D_cv_rewritten": d,
            "E_variants": e,
            "F_checklist": f,
            "llm_used": self.llm_available,
        }

    # ── A) Diagnóstico de encaje ─────────────────
    def _deliverable_a(self, cv_text, job_text, idioma, longitud, rol_objetivo, nivel) -> dict:
        logger.info("Generando diagnóstico de encaje (A)...")
        prompt = DIAGNOSIS_PROMPT.format(
            job_offer=job_text,
            cv_text=cv_text,
            idioma=idioma,
            longitud=longitud,
            rol_objetivo=rol_objetivo or "El indicado en la oferta",
            nivel=nivel or "No especificado",
        )
        response = _llm(prompt, max_tokens=1500)
        if response:
            result = _safe_json(response, {})
            if result.get("score") is not None:
                return result

        # Fallback sin LLM
        return self._fallback_diagnosis(cv_text, job_text)

    def _fallback_diagnosis(self, cv_text: str, job_text: str) -> dict:
        """Diagnóstico básico sin LLM basado en solapamiento de palabras."""
        job_words = set(re.findall(r"\b\w{4,}\b", job_text.lower()))
        cv_words = set(re.findall(r"\b\w{4,}\b", cv_text.lower()))
        overlap = job_words & cv_words
        score = min(100, int(len(overlap) / max(len(job_words), 1) * 200))
        return {
            "resumen_oferta": "Oferta procesada en modo básico (LM Studio no disponible). Revisión manual recomendada.",
            "score": score,
            "razon_score": f"Score estimado basado en solapamiento de {len(overlap)} términos comunes.",
            "fortalezas": [{"fortaleza": f"Término común: {w}", "cita_cv": w} for w in list(overlap)[:5]],
            "gaps": [{"gap": f"Término de la oferta no encontrado: {w}", "impacto": "alto"} for w in list(job_words - cv_words)[:5]],
        }

    # ── B) Keywords ATS ──────────────────────────
    def _deliverable_b(self, cv_text: str, job_text: str) -> dict:
        logger.info("Extrayendo keywords ATS (B)...")
        prompt = KEYWORDS_PROMPT.format(job_offer=job_text, cv_text=cv_text)
        response = _llm(prompt, max_tokens=2000)
        if response:
            result = _safe_json(response, {})
            if result.get("keywords"):
                return result

        # Fallback
        return self._fallback_keywords(job_text, cv_text)

    def _fallback_keywords(self, job_text: str, cv_text: str) -> dict:
        words = re.findall(r"\b[A-Za-z][A-Za-zÁÉÍÓÚáéíóú+#.]{3,}\b", job_text)
        # Deduplica manteniendo orden
        seen: set = set()
        unique = [w for w in words if not (w.lower() in seen or seen.add(w.lower()))]
        keywords = []
        for word in unique[:25]:
            estado = "presente" if word.lower() in cv_text.lower() else "ausente"
            keywords.append({
                "keyword": word,
                "categoria": "hard_skill",
                "estado": estado,
                "ubicacion_cv": "Detectado en texto plano" if estado == "presente" else None,
                "sugerencia": "Incorporar naturalmente si aplica a tu experiencia real" if estado == "ausente" else "Ya presente",
            })
        return {"keywords": keywords}

    # ── C) Plan de cambios ───────────────────────
    def _deliverable_c(self, cv_text: str, job_text: str, diagnosis: dict) -> dict:
        logger.info("Generando plan de cambios (C)...")
        diagnosis_summary = (
            f"Score: {diagnosis.get('score', 'N/A')}/100. "
            f"Gaps principales: {', '.join(g['gap'] for g in diagnosis.get('gaps', [])[:3])}"
        )
        prompt = CHANGES_PROMPT.format(
            job_offer=job_text,
            cv_text=cv_text,
            diagnosis_summary=diagnosis_summary,
        )
        response = _llm(prompt, max_tokens=1500)
        if response:
            result = _safe_json(response, {})
            if result.get("cambios"):
                return result

        # Fallback
        return self._fallback_changes(diagnosis)

    def _fallback_changes(self, diagnosis: dict) -> dict:
        cambios = [
            {
                "prioridad": "alto",
                "seccion": "Resumen profesional",
                "que_cambiar": "Alinear el resumen con el título y requisitos principales de la oferta",
                "ejemplo": "Añade el título del puesto objetivo y 2-3 keywords principales en las primeras 2 líneas",
                "impacto": "Alta visibilidad en ATS y primera impresión del reclutador",
            },
            {
                "prioridad": "alto",
                "seccion": "Skills",
                "que_cambiar": "Incluir keywords de la oferta que ya domines",
                "ejemplo": "Reorganiza la sección de skills destacando primero las que coinciden con la oferta",
                "impacto": "Aumenta el score ATS directamente",
            },
        ]
        for gap_item in diagnosis.get("gaps", [])[:3]:
            cambios.append({
                "prioridad": "medio" if gap_item.get("impacto") != "alto" else "alto",
                "seccion": "Experiencia",
                "que_cambiar": f"Reforzar evidencia para: {gap_item['gap']}",
                "ejemplo": "Reformular bullets de experiencia para hacer visible esta competencia si la tienes",
                "impacto": "Reduce gap identificado",
            })
        return {"cambios": cambios}

    # ── D) CV reescrito ──────────────────────────
    def _deliverable_d(
        self,
        cv_text: str,
        job_text: str,
        idioma: str,
        longitud: str,
        rol_objetivo: str,
        nivel: str,
        logros: str,
        stack: str,
    ) -> str:
        logger.info("Reescribiendo CV (D)...")
        prompt = CV_REWRITE_PROMPT.format(
            job_offer=job_text,
            cv_text=cv_text,
            idioma=idioma,
            longitud=longitud,
            rol_objetivo=rol_objetivo or "El indicado en la oferta",
            nivel=nivel or "No especificado",
            logros=logros or "Extraer del CV original",
            stack=stack or "Extraer del CV original",
        )
        response = _llm(prompt, max_tokens=3000)
        if response and len(response.strip()) > 200:
            return self._clean_cv_output(response.strip())

        # Fallback: devolver el cv_text con nota
        return (
            "⚠️ LM Studio no disponible. CV reescrito no generado.\n\n"
            "Para generar el CV reescrito:\n"
            "1. Inicia LM Studio\n"
            "2. Carga un modelo (ej. LLaMA3, Mistral, Qwen)\n"
            "3. Inicia el servidor local\n"
            "4. Repite el análisis\n\n"
            "--- CV ORIGINAL (sin reescribir) ---\n\n"
            + cv_text
        )

    # ── Limpieza de salida del CV ────────────────
    @staticmethod
    def _clean_cv_output(text: str) -> str:
        """
        Elimina artefactos que el LLM añade al CV pero no forman parte de él:
        - Líneas con marcadores [PREGUNTA: ...]
        - Secciones de notas/comentarios/observaciones (### Notas adicionales, etc.)
        - Líneas de meta-comentario ('Este CV está optimizado...', etc.)
        """
        lines = text.split("\n")
        cleaned = []
        skip_section = False

        note_headers = re.compile(
            r"^#+\s*(notas?\s*(adicionales?)?|observaciones?|comentarios?|preguntas?)",
            re.IGNORECASE,
        )
        meta_line = re.compile(
            r"(este cv (est[aá] optimizado|ha sido|fue generado)|cv optimizado para|"
            r"nota\s*:.*ats|recuerda (que|revisar)|para (maximizar|mejorar|aumentar) "
            r"(tu|el) (cv|perfil|encaje))",
            re.IGNORECASE,
        )

        for line in lines:
            stripped = line.strip()
            # Detectar inicio de sección de notas → omitir hasta la próxima sección real
            if note_headers.match(stripped):
                skip_section = True
                continue
            # Nueva sección de nivel similar termina la zona omitida
            if skip_section and re.match(r"^#+\s+\S", stripped):
                skip_section = False
            if skip_section:
                continue
            # Eliminar líneas con [PREGUNTA: ...]
            if re.search(r"\[PREGUNTA:", line, re.IGNORECASE):
                continue
            # Eliminar líneas de meta-comentario
            if meta_line.search(line):
                continue
            cleaned.append(line)

        return "\n".join(cleaned).rstrip()

    # ── E) Variantes Resumen + Skills ────────────
    def _deliverable_e(
        self, cv_text: str, job_text: str, idioma: str, rol_objetivo: str, nivel: str
    ) -> dict:
        logger.info("Generando variantes Resumen+Skills (E)...")
        # Truncar entradas para evitar exceder el contexto y dejar tokens libres
        job_trimmed = job_text[:1500] + ("..." if len(job_text) > 1500 else "")
        cv_trimmed = cv_text[:2000] + ("..." if len(cv_text) > 2000 else "")
        prompt = VARIANTS_PROMPT.format(
            job_offer=job_trimmed,
            cv_text=cv_trimmed,
            idioma=idioma,
            rol_objetivo=rol_objetivo or "El indicado en la oferta",
            nivel=nivel or "No especificado",
        )
        response = _llm(prompt, max_tokens=3500)
        if response:
            result = _safe_json(response, {})
            if result.get("ats_first") and result.get("recruiter_first"):
                return result

        # Fallback
        return {
            "ats_first": {
                "resumen": "⚠️ LM Studio no disponible. Activa LM Studio para generar esta variante.",
                "skills": "Completa con tus skills relevantes para la oferta.",
            },
            "recruiter_first": {
                "resumen": "⚠️ LM Studio no disponible. Activa LM Studio para generar esta variante.",
                "skills": "Completa con tus skills más diferenciadoras.",
            },
        }

    # ── F) Checklist ATS ─────────────────────────
    def _deliverable_f(self, job_text: str, cv_adapted: str) -> dict:
        logger.info("Generando checklist ATS (F)...")
        job_summary = job_text[:600] + ("..." if len(job_text) > 600 else "")
        cv_preview = cv_adapted[:1500] + ("..." if len(cv_adapted) > 1500 else "")
        prompt = ATS_CHECKLIST_PROMPT.format(
            job_offer_summary=job_summary,
            cv_adapted=cv_preview,
        )
        response = _llm(prompt, max_tokens=1200)
        if response:
            result = _safe_json(response, {})
            if result.get("checklist"):
                return result

        # Fallback estático
        return {
            "checklist": [
                {"punto": "Sin tablas ni columnas en el CV", "estado": "advertencia", "detalle": "Verifica que el formato sea texto plano"},
                {"punto": "Secciones estándar presentes (Contacto, Resumen, Experiencia, Skills, Educación)", "estado": "advertencia", "detalle": "Revisa que todas las secciones existan"},
                {"punto": "Keywords del puesto incorporadas", "estado": "advertencia", "detalle": "Compara con la tabla B de keywords"},
                {"punto": "Longitud máx. 2 páginas", "estado": "advertencia", "detalle": "Cuenta las páginas en el editor"},
                {"punto": "Datos de contacto completos", "estado": "advertencia", "detalle": "Nombre, email, teléfono, LinkedIn mínimo"},
                {"punto": "Verbos de acción en experiencia", "estado": "advertencia", "detalle": "Cada bullet debe comenzar con un verbo (Lideré, Desarrollé, Optimicé…)"},
                {"punto": "Sin información inventada o no respaldable", "estado": "ok", "detalle": "Revisa que todo sea verificable"},
                {"punto": "Fechas en formato estándar (MM/AAAA)", "estado": "advertencia", "detalle": "Ej: 03/2022 - 01/2024"},
                {"punto": "Idioma consistente en todo el CV", "estado": "advertencia", "detalle": "No mezclar español e inglés salvo términos técnicos"},
                {"punto": "Sin iconos, gráficos ni imágenes", "estado": "ok", "detalle": "ATS no puede leer elementos visuales"},
            ]
        }
