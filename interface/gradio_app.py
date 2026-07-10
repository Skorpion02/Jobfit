import gradio as gr
import hashlib
import logging
import os
import json
import time
from typing import Dict, Optional, Tuple, List
import tempfile
from pathlib import Path

# Importar nuestros módulos
from src.scraper.job_scraper import JobScraper
from src.auditor.realism_scorer import RealismScorer
from src.extractor.job_parser import JobParser
from src.extractor.cv_parser import CVParser
from src.matcher.semantic_matcher import SemanticMatcher
from src.generator.cv_adapter import CVAdapter
from src.generator.ats_optimizer import ATS_Optimizer # <- Importar el nuevo optimizador
from src.generator.cv_full_analyzer import CVFullAnalyzer  # <- Análisis Pro ATS
from src.utils.cv_utils import normalize_cv_data
from interface import aurora  # tema visual + helpers HTML del rediseño Aurora
import uuid # <- Importar para nombres de archivo únicos

logger = logging.getLogger(__name__)

class JobFitApp:
    def __init__(self):
        self.scraper = JobScraper()
        self.scorer = RealismScorer()
        self.job_parser = JobParser()
        self.cv_parser = CVParser()
        self.matcher = SemanticMatcher()
        self.adapter = CVAdapter()
        self.optimizer = ATS_Optimizer() # <- Instanciar el nuevo optimizador
        self.full_analyzer = CVFullAnalyzer()  # <- Análisis Pro ATS
        
        # Estado de la aplicación
        self.current_job_data = None
        self.current_cv_data = None
        self.current_matching = None
        # Hashes para detectar cambios y evitar re-parseo innecesario
        self._last_job_hash: Optional[str] = None
        self._last_cv_hash: Optional[str] = None
    
    def _clear_cache(self):
        """Limpia solo el matching (depende del par CV+job concreto).
        Los datos parseados de job y CV se reutilizan si el contenido no cambió."""
        self.current_matching = None

    def _clear_all(self):
        """Limpieza completa incluyendo job y CV cacheados."""
        self.current_job_data = None
        self.current_cv_data = None
        self.current_matching = None
        self._last_job_hash = None
        self._last_cv_hash = None

    def _get_job_data(self, job_text: str) -> dict:
        """Parsea la oferta solo si el texto cambió desde la última vez."""
        job_hash = hashlib.md5(job_text.encode()).hexdigest()
        if self._last_job_hash == job_hash and self.current_job_data is not None:
            logger.info("Reutilizando job_data cacheado (hash=%s)", job_hash[:8])
            return self.current_job_data
        self.current_job_data = self.job_parser.extract_job_data(job_text)
        self._last_job_hash = job_hash
        return self.current_job_data

    def _get_cv_data(self, cv_file_path: str) -> dict:
        """Parsea el CV solo si el archivo cambió desde la última vez."""
        try:
            stat = os.stat(cv_file_path)
            cv_hash = hashlib.md5(f"{cv_file_path}:{stat.st_size}:{stat.st_mtime}".encode()).hexdigest()
        except OSError:
            cv_hash = hashlib.md5(cv_file_path.encode()).hexdigest()
        if self._last_cv_hash == cv_hash and self.current_cv_data is not None:
            logger.info("Reutilizando cv_data cacheado (hash=%s)", cv_hash[:8])
            return self.current_cv_data
        file_ext = os.path.splitext(cv_file_path)[1][1:].lower()
        cv_data = self.cv_parser.parse_cv(cv_file_path, file_ext)
        self.current_cv_data = normalize_cv_data(cv_data)
        self._last_cv_hash = cv_hash
        return self.current_cv_data

    # ─────────────────────────────────────────────
    #  ANÁLISIS COMPLETO ATS (Propuesta A → F)
    # ─────────────────────────────────────────────

    def analyze_full_cv(
        self,
        cv_file,
        job_url: str,
        job_text_manual: str,
        idioma: str,
        longitud: str,
        pais: str,
        rol_objetivo: str,
        nivel: str,
        progress: gr.Progress = gr.Progress(),
    ):
        """
        Ejecuta el análisis completo ATS y devuelve los 6 entregables
        formateados para la interfaz Gradio.

        Returns (tuple of 8):
            tab_a_md, tab_b_md, tab_c_md, tab_d_text, tab_e_md, tab_f_md,
            download_cv_txt, status_md
        """
        try:
            _t_start = time.perf_counter()
            logger.info("[ATS] Análisis completo iniciado.")

            progress(0.02, desc="Procesando oferta…")

            # 1. Obtener texto de la oferta
            if job_url.strip():
                job_text = self.scraper.scrape_job_offer(job_url.strip())
                if not job_text:
                    err = "❌ No se pudo extraer el texto de la URL proporcionada."
                    return err, "", "", "", "", "", None, None, err
            elif job_text_manual.strip():
                job_text = job_text_manual.strip()
            else:
                err = "❌ Proporciona una URL o pega el texto de la oferta."
                return err, "", "", "", "", "", None, None, err

            # 2. Parsear oferta (reutiliza caché si el texto no cambió)
            progress(0.06, desc="Extrayendo info estructurada de la oferta con IA…")
            job_data = self._get_job_data(job_text)

            # 3. Parsear CV (reutiliza caché si es el mismo archivo)
            if not cv_file:
                err = "❌ Sube un archivo de CV (PDF, DOCX o TXT)."
                return err, "", "", "", "", "", None, None, err

            progress(0.10, desc="Parseando CV…")
            cv_file_path = cv_file if isinstance(cv_file, str) else cv_file.name
            cv_data = self._get_cv_data(cv_file_path)
            if cv_data is None:
                cv_data = {}

            # 4. Ejecutar análisis completo
            _t_llm_start = time.perf_counter()
            results = self.full_analyzer.analyze(
                cv_data=cv_data,
                job_data=job_data,
                idioma=idioma or "ES",
                longitud=longitud or "2 páginas",
                pais=pais or "",
                rol_objetivo=rol_objetivo or "",
                nivel=nivel or "",
                logros="",
                stack="",
                progress_cb=lambda frac, desc: progress(frac, desc=desc),
            )
            _t_llm_end = time.perf_counter()
            logger.info(
                "[ATS] LLM calls completadas en %.1fs (cache=%s).",
                _t_llm_end - _t_llm_start,
                results.get("_from_cache", False),
            )

            llm_note = (
                "\n> 🤖 **LM Studio activo** — análisis generado con IA\n"
                if results.get("llm_used")
                else "\n> ⚠️ **LM Studio no disponible** — resultados aproximados (modo básico)\n"
            )

            # ── Formatear A) Diagnóstico ──────────
            a = results["A_diagnosis"]
            score = a.get("score", "N/D")
            score_emoji = self._get_score_color(score) if isinstance(score, int) else "⚪"
            fortalezas_md = "\n".join(
                f"- **{f['fortaleza']}** → *\"{f.get('cita_cv', '')}\"*"
                for f in a.get("fortalezas", [])
            )
            gaps_md = "\n".join(
                f"- ({g.get('impacto','?').upper()}) {g['gap']}"
                for g in a.get("gaps", [])
            )
            tab_a = f"""{llm_note}
## A) Diagnóstico de Encaje

### Resumen de la oferta
{a.get('resumen_oferta', 'N/D')}

### Score de alineación: {score_emoji} **{score}/100**
{a.get('razon_score', '')}

### Top 5 Fortalezas
{fortalezas_md}

### Top 5 Gaps / Riesgos
{gaps_md}
"""

            # ── Formatear B) Keywords ─────────────
            b_keywords = results["B_keywords"].get("keywords", [])
            rows = []
            for kw in b_keywords:
                estado_icon = {"presente": "✅", "debil": "⚠️", "ausente": "❌"}.get(
                    kw.get("estado", ""), "❓"
                )
                rows.append(
                    f"| {estado_icon} {kw.get('keyword','')} "
                    f"| {kw.get('categoria','')} "
                    f"| {kw.get('estado','')} "
                    f"| {kw.get('ubicacion_cv') or '—'} "
                    f"| {kw.get('sugerencia','—')} |"
                )
            kw_table = "| Estado | Keyword | Categoría | Estado | Ubicación en CV | Sugerencia |\n"
            kw_table += "|--------|---------|-----------|--------|-----------------|------------|\n"
            kw_table = "| Keyword | Categoría | Estado | Ubicación en CV | Sugerencia |\n"
            kw_table += "|---------|-----------|--------|-----------------|------------|\n"
            kw_table += "\n".join(rows)
            tab_b = f"""{llm_note}
## B) Keywords ATS\n\n{kw_table}\n"""

            # ── Formatear C) Plan de cambios ──────
            cambios = results["C_changes"].get("cambios", [])
            alto = [c for c in cambios if c.get("prioridad") == "alto"]
            medio = [c for c in cambios if c.get("prioridad") == "medio"]
            opcional = [c for c in cambios if c.get("prioridad") == "opcional"]

            def _fmt_cambios(lista):
                return "\n".join(
                    f"- **[{c.get('seccion','?')}]** {c.get('que_cambiar','')}\n"
                    f"  *Ejemplo:* {c.get('ejemplo','')}\n"
                    f"  *Impacto:* {c.get('impacto', '')}"
                    for c in lista
                )

            tab_c = f"""{llm_note}
## C) Plan de Cambios Priorizado

### 🔴 Alto Impacto
{_fmt_cambios(alto) or 'Ninguno'}

### 🟡 Medio Impacto
{_fmt_cambios(medio) or 'Ninguno'}

### 🟢 Opcional
{_fmt_cambios(opcional) or 'Ninguno'}
"""

            # ── D) CV reescrito (texto plano) ─────
            tab_d = results["D_cv_rewritten"]

            # Crear archivos para descarga
            temp_dir = Path(tempfile.gettempdir()) / "jobfit_exports"
            temp_dir.mkdir(exist_ok=True)
            uid = uuid.uuid4()
            txt_path = temp_dir / f"cv_ats_pro_{uid}.txt"
            with open(txt_path, "w", encoding="utf-8") as fh:
                fh.write(tab_d)
            docx_path = temp_dir / f"cv_ats_pro_{uid}.docx"
            self._plain_text_to_docx(tab_d, str(docx_path))

            # ── Formatear E) Variantes ────────────
            e = results["E_variants"]
            tab_e = f"""{llm_note}
## E) Variante 1 — ATS-first
*(Alta densidad de keywords, natural)*

### Resumen
{e.get('ats_first', {}).get('resumen', 'N/D')}

### Skills
{e.get('ats_first', {}).get('skills', 'N/D')}

---

## E) Variante 2 — Recruiter-first
*(Narrativa diferenciadora, más humana)*

### Resumen
{e.get('recruiter_first', {}).get('resumen', 'N/D')}

### Skills
{e.get('recruiter_first', {}).get('skills', 'N/D')}
"""

            # ── Formatear F) Checklist ────────────
            checklist_items = results["F_checklist"].get("checklist", [])
            checklist_md = "\n".join(
                f"- {'✅' if c.get('estado') == 'ok' else '⚠️' if c.get('estado') == 'advertencia' else '❌'} "
                f"**{c.get('punto', '')}**: {c.get('detalle', '')}"
                for c in checklist_items
            )
            ok_count = sum(1 for c in checklist_items if c.get("estado") == "ok")
            total = len(checklist_items)
            tab_f = f"""{llm_note}
## F) Checklist ATS Final

**Estado general: {ok_count}/{total} puntos OK**

{checklist_md}
"""

            status = f"✅ Análisis completo generado {'con LM Studio' if results.get('llm_used') else '(modo básico — activa LM Studio para mejor calidad)'}"
            _t_total = time.perf_counter() - _t_start
            logger.info(
                "[ATS] ✅ Análisis finalizado en %.1fs (LLM=%.1fs, formato+export=%.1fs).",
                _t_total,
                _t_llm_end - _t_llm_start,
                _t_total - (_t_llm_end - _t_llm_start),
            )
            progress(1.0, desc=f"✅ Completado en {_t_total:.0f}s")
            return tab_a, tab_b, tab_c, tab_d, tab_e, tab_f, str(txt_path), str(docx_path), status

        except ValueError as exc:
            # Errores de validación (CV demasiado grande, formato no soportado, etc.)
            _t_total = time.perf_counter() - _t_start
            logger.warning("[ATS] ⚠️ Validación tras %.1fs: %s", _t_total, exc)
            err = f"❌ {exc}"
            return err, "", "", "", "", "", None, None, err
        except Exception as exc:
            _t_total = time.perf_counter() - _t_start
            logger.exception("[ATS] ❌ Error tras %.1fs: %s", _t_total, exc)
            err = (
                "❌ Error procesando el análisis. "
                "Revisa `logs/jobfit.log` para el detalle técnico."
            )
            return err, "", "", "", "", "", None, None, err

    def _plain_text_to_docx(self, text: str, filename: str) -> str:
        """
        Convierte el CV en texto plano (entregable D) a un DOCX limpio y
        compatible con ATS.  Detecta:
        - Líneas de separación (===, ---) → línea decorativa
        - Encabezados de sección EN MAYÚSCULAS → Heading 2 azul
        - Bullets (•, -, *) → List Bullet
        - Resto → párrafo normal
        """
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()

        # Márgenes compactos
        for section in doc.sections:
            from docx.shared import Inches
            section.top_margin = Inches(0.8)
            section.bottom_margin = Inches(0.8)
            section.left_margin = Inches(0.9)
            section.right_margin = Inches(0.9)

        # Estilo base de párrafo
        style = doc.styles["Normal"]
        style.font.name = "Calibri"
        style.font.size = Pt(10.5)

        BLUE = RGBColor(31, 78, 121)
        GREY = RGBColor(89, 89, 89)

        for line in text.splitlines():
            stripped = line.strip()

            # Separadores visuales → línea gris fina
            if set(stripped) <= {"=", "-", "─"} and len(stripped) > 3:
                p = doc.add_paragraph()
                run = p.add_run("─" * 55)
                run.font.color.rgb = RGBColor(200, 200, 200)
                run.font.size = Pt(7)
                continue

            # Encabezado de sección (toda en mayúsculas, sin bullets)
            if (
                stripped
                and stripped == stripped.upper()
                and len(stripped) > 2
                and not stripped.startswith(("•", "-", "*", "|"))
            ):
                p = doc.add_paragraph()
                run = p.add_run(stripped)
                run.bold = True
                run.font.size = Pt(12)
                run.font.color.rgb = BLUE
                continue

            # Bullet
            if stripped.startswith(("•", "- ", "* ")):
                content = stripped.lstrip("•-* ").strip()
                p = doc.add_paragraph(style="List Bullet")
                run = p.add_run(content)
                run.font.size = Pt(10.5)
                continue

            # Línea vacía → espacio
            if not stripped:
                doc.add_paragraph()
                continue

            # Línea de contacto (contiene | entre datos)
            if "|" in stripped and len(stripped.split("|")) >= 2:
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = p.add_run(stripped)
                run.font.size = Pt(10)
                run.font.color.rgb = GREY
                continue

            # Párrafo normal
            p = doc.add_paragraph()
            run = p.add_run(stripped)
            run.font.size = Pt(10.5)

        doc.save(filename)
        return filename

    def get_diagnostics(self):
        """Obtiene información de diagnóstico del sistema"""
        import platform
        from pathlib import Path
        
        diagnostics = []
        
        # Sistema
        diagnostics.append("## 🖥️ Sistema")
        diagnostics.append(f"- **OS:** {platform.system()} {platform.release()}")
        diagnostics.append(f"- **Python:** {platform.python_version()}")
        diagnostics.append("")
        
        # LM Studio
        diagnostics.append("## 🤖 LM Studio")
        try:
            from src.llm.lmstudio_client import lmstudio_client
            from config.settings import settings
            
            diagnostics.append(f"- **URL configurada:** `{settings.lmstudio_base_url}`")
            diagnostics.append(f"- **Modelo configurado:** `{settings.lmstudio_model}`")
            diagnostics.append(f"- **Habilitado:** {'✅ Sí' if settings.use_lmstudio else '❌ No'}")
            diagnostics.append(f"- **Estado:** {'✅ Conectado' if lmstudio_client.available else '❌ No disponible'}")
            
            if lmstudio_client.available:
                diagnostics.append(f"- **Modelo activo:** `{lmstudio_client.model}`")
                models = lmstudio_client.get_available_models()
                if models:
                    diagnostics.append(f"- **Modelos disponibles:** {len(models)}")
                    for i, model in enumerate(models[:5], 1):
                        diagnostics.append(f"  {i}. `{model}`")
                    if len(models) > 5:
                        diagnostics.append(f"  ... y {len(models) - 5} más")
            else:
                diagnostics.append("")
                diagnostics.append("### ⚠️ LM Studio no disponible")
                diagnostics.append("**Posibles causas:**")
                diagnostics.append("1. LM Studio no está instalado")
                diagnostics.append("2. LM Studio no está abierto")
                diagnostics.append("3. El servidor local no está iniciado")
                diagnostics.append("4. Puerto incorrecto o bloqueado")
                diagnostics.append("")
                diagnostics.append("**Solución:**")
                diagnostics.append("1. Descarga LM Studio desde https://lmstudio.ai")
                diagnostics.append("2. Abre LM Studio")
                diagnostics.append("3. Ve a la pestaña 'Local Server'")
                diagnostics.append("4. Carga un modelo y haz click en 'Start Server'")
        except Exception as e:
            diagnostics.append(f"- **Error:** {str(e)}")
        
        diagnostics.append("")
        
        # Logs
        diagnostics.append("## 📋 Logs")
        log_path = Path(__file__).parent.parent / "logs" / "jobfit.log"
        if log_path.exists():
            size_kb = log_path.stat().st_size / 1024
            diagnostics.append(f"- **Archivo:** `{log_path.name}`")
            diagnostics.append(f"- **Tamaño:** {size_kb:.2f} KB")
            diagnostics.append(f"- **Ruta completa:** `{log_path}`")
            diagnostics.append("")
            diagnostics.append("**💡 Para ver logs en tiempo real, ejecuta:**")
            diagnostics.append("```bash")
            diagnostics.append("view_logs.bat")
            diagnostics.append("```")
        else:
            diagnostics.append("- **Estado:** No hay logs todavía")
        
        return "\n".join(diagnostics)
    
    def get_recent_logs(self, num_lines: int = 100):
        """Obtiene las últimas líneas del log"""
        from pathlib import Path
        
        log_path = Path(__file__).parent.parent / "logs" / "jobfit.log"
        
        if not log_path.exists():
            return "📝 No hay logs disponibles todavía.\n\nLos logs aparecerán cuando uses la aplicación."
        
        try:
            # Intentar con UTF-8 primero, luego con otros encodings
            encodings = ['utf-8', 'cp1252', 'latin-1']
            lines = None
            
            for encoding in encodings:
                try:
                    with open(log_path, 'r', encoding=encoding, errors='ignore') as f:
                        lines = f.readlines()
                        break
                except:
                    continue
            
            if lines:
                recent_lines = lines[-num_lines:]
                return "".join(recent_lines)
            else:
                return "❌ No se pudieron leer los logs con ningún encoding compatible"
                
        except Exception as e:
            return f"❌ Error al leer logs: {e}"

    def _get_lmstudio_status(self):
        """Obtiene el estado de LM Studio para mostrar en la interfaz"""
        try:
            from src.llm.lmstudio_client import lmstudio_client
            from config.settings import settings
            
            if settings.use_lmstudio and lmstudio_client.available:
                models = lmstudio_client.get_available_models()
                current_model = lmstudio_client.model
                return f"""
> 🤖 **LM Studio activo** - Modelo: `{current_model}` 
> 📋 Modelos disponibles: {', '.join(models[:3])}{'...' if len(models) > 3 else ''}
"""
            elif settings.use_lmstudio:
                return """
> ⚠️ **LM Studio configurado pero no disponible** - Usando extracción basada en reglas
> 💡 Inicia LM Studio para mejorar la precisión del análisis
"""
            else:
                return """
> 📝 **Modo básico** - Usando extracción basada en reglas
"""
        except:
            return """
> 📝 **Modo básico** - Usando extracción basada en reglas
"""

    def audit_job_offer(self, url: str, manual_text: str) -> Tuple[str, str, str]:
        """Audita una oferta de trabajo"""
        try:
            # Obtener texto de la oferta
            if url.strip():
                job_text = self.scraper.scrape_job_offer(url)
                if not job_text:
                    return "❌ Error: No se pudo extraer texto de la URL", "", ""
            elif manual_text.strip():
                job_text = manual_text
            else:
                return "❌ Error: Proporciona una URL o pega el texto de la oferta", "", ""

            # Extraer datos estructurados (reutiliza caché si el texto no cambió)
            self.current_job_data = self._get_job_data(job_text)
            
            # Calcular score de realismo
            audit_result = self.scorer.calculate_realism_score(self.current_job_data)
            
            # Formatear resultados
            score = audit_result['realism_score']
            score_color = self._get_score_color(score)
            
            # Resumen del audit
            audit_summary = f"""
## 📊 Score de Realismo: {score_color} {score}/100

**{audit_result['reasoning']}**

### 🚨 Señales Detectadas:
"""
            
            for signal in audit_result['signals']:
                emoji = "⚠️" if signal['type'] == 'warning' else "❌" if signal['type'] == 'error' else "ℹ️"
                audit_summary += f"\n{emoji} {signal['description']}"
            
            if not audit_result['signals']:
                audit_summary += "\n✅ No se detectaron problemas significativos"
            
            # Categorías detalladas
            categories = audit_result.get('categories', {})
            category_detail = f"""
### 📈 Análisis por Categorías:
- **Años/Seniority**: {categories.get('years_seniority', 'N/A')}/100
- **Stack Tecnológico**: {categories.get('tech_stack', 'N/A')}/100
- **Salario**: {categories.get('salary', 'N/A') or 'No especificado'}/100
- **Consistencia**: {categories.get('consistency', 'N/A')}/100
"""
            
            # JSON estructurado
            job_json = json.dumps(self.current_job_data, indent=2, ensure_ascii=False)
            
            return audit_summary, category_detail, job_json
            
        except Exception as e:
            return f"❌ Error procesando la oferta: {str(e)}", "", ""
    
    def process_cv_and_match(self, cv_file, job_url: str, manual_job_text: str) -> Tuple[str, str, Optional[str], Optional[str]]:
        """Procesa CV, hace matching y genera AMBOS archivos"""
        try:
            self._clear_cache()

            if job_url.strip():
                job_text = self.scraper.scrape_job_offer(job_url)
                if not job_text:
                    return "❌ Error: No se pudo extraer texto de la URL", "", None, None
            elif manual_job_text.strip():
                job_text = manual_job_text
            else:
                return "❌ Error: Proporciona una URL o pega el texto de la oferta", "", None, None

            # Reutiliza job_data si el texto no cambió
            job_data = self._get_job_data(job_text)

            # Procesar CV
            if not cv_file:
                return "❌ Error: Sube un archivo de CV", "", None, None

            # En Gradio 4.4.0, cv_file es directamente la ruta del archivo temporal
            cv_file_path = cv_file if isinstance(cv_file, str) else cv_file.name

            # Parsear CV (reutiliza si es el mismo archivo)
            self.current_cv_data = self._get_cv_data(cv_file_path)
            # normalize_cv_data ya se aplica dentro de _get_cv_data

            # Realizar matching con información de tipos de requisitos
            # Normalización defensiva para evitar iteración sobre None
            must_have_reqs = job_data.get('must_have') or []
            if not isinstance(must_have_reqs, list):
                must_have_reqs = []
            
            nice_to_have_reqs = job_data.get('nice_to_have') or []
            if not isinstance(nice_to_have_reqs, list):
                nice_to_have_reqs = []
            
            # Crear lista de requisitos con tipos
            requirements_with_types = []
            for req in must_have_reqs:
                requirements_with_types.append({
                    'requirement': req, 
                    'type': 'must_have'
                })
            for req in nice_to_have_reqs:
                requirements_with_types.append({
                    'requirement': req, 
                    'type': 'nice_to_have'
                })
            
            # Para compatibilidad con el matcher actual
            requirements = must_have_reqs + nice_to_have_reqs
            
            # Debug: verificar que tenemos datos
            print(f"DEBUG - Requirements encontrados: {len(requirements)}")
            print(f"DEBUG - CV data keys: {list(self.current_cv_data.keys())}")
            
            cv_sections = {
                'experience': self._safe_join_cv_section(self.current_cv_data.get('experience', [])),
                # Para skills preferimos concatenar la lista 'technical' si existe
                'skills': self._safe_join_cv_section(self.current_cv_data.get('skills', {}).get('technical', [])),
                'projects': self._safe_join_cv_section(self.current_cv_data.get('projects', [])),
                'education': self._safe_join_cv_section(self.current_cv_data.get('education', []))
            }
            
            # Debug: verificar contenido de CV sections
            for section, content in cv_sections.items():
                print(f"DEBUG - {section}: {len(content)} caracteres")
            
            # Si no tenemos requirements, intentar extraer de texto plano
            if not requirements and job_data.get('raw_text'):
                # Extraer keywords básicos como requirements
                job_text_fallback = job_data.get('raw_text', '')
                requirements = self._extract_basic_requirements(job_text_fallback)
                print(f"DEBUG - Requirements extraídos de texto: {len(requirements)}")
            
            # Concatenar todas las secciones del CV en texto
            cv_text = ' '.join([
                cv_sections['experience'],
                cv_sections['skills'], 
                cv_sections['projects'],
                cv_sections['education']
            ])
            
            self.current_matching = self.matcher.match_requirements_to_cv(
                requirements, cv_text)
            
            # Enriquecer resultados con tipos de requisitos
            self._enrich_matching_with_types(
                self.current_matching, requirements_with_types)
            
            print(f"DEBUG - Matching results: {self.current_matching}")
            
            # Formatear resultados del matching
            matching_summary = self._format_matching_results(
                self.current_matching)
            
            # --- GENERACIÓN DUAL DE CVs ---

            # 1. Generar CV adaptado para humanos (DOCX)
            adapted_cv = self.adapter.adapt_cv(
                self.current_cv_data, 
                job_data, 
                self.current_matching
            )
            cv_preview = self._format_cv_preview(adapted_cv)
            
            # Crear directorio temporal si no existe
            temp_dir = Path(tempfile.gettempdir()) / "jobfit_exports"
            temp_dir.mkdir(exist_ok=True)

            # Exportar DOCX a archivo temporal
            temp_docx_path = temp_dir / f"cv_adaptado_{uuid.uuid4()}.docx"
            self.adapter.export_to_docx(adapted_cv, str(temp_docx_path))

            # 2. Generar CV optimizado para ATS (TXT)
            ats_optimized_text = self.optimizer.optimize_cv_for_ats(
                self.current_cv_data, self.current_matching
            )
            temp_txt_path = temp_dir / f"cv_optimizado_ats_{uuid.uuid4()}.txt"
            with open(temp_txt_path, 'w', encoding='utf-8') as f:
                f.write(ats_optimized_text)

            return matching_summary, cv_preview, str(temp_docx_path), str(temp_txt_path)
            
        except Exception as e:
            return f"❌ Error procesando CV: {str(e)}", "", None, None
    
    def _get_score_color(self, score: int) -> str:
        """Devuelve emoji de color según el score"""
        if score >= 85:
            return "🟢"
        elif score >= 70:
            return "🟡"
        elif score >= 50:
            return "🟠"
        else:
            return "🔴"
    
    def _format_matching_results(self, matching: Dict) -> str:
        """Formatea los resultados del matching"""
        matches = matching.get('matches', [])
        gaps = matching.get('missing_requirements', [])
        coverage = matching.get('coverage_percentage', 0) / 100
        
        # Validar que tenemos datos
        if coverage == 0 and not matches and not gaps:
            return """
## ⚠️ Sin Resultados de Matching

No se pudieron procesar los requisitos o el CV. Verifica que:
- La oferta de trabajo contenga requisitos claros
- El CV tenga información relevante

**Sugerencia**: Intenta con una oferta más detallada o un CV más completo.
"""
        
        result = f"""
## 🎯 Análisis de Encaje: {coverage*100:.1f}% de cobertura

### ✅ Requisitos Cubiertos ({len(matches)}):
"""
        
        if matches:
            for match in matches[:10]:  # Mostrar top 10
                # Emojis según similitud
                if match['similarity'] > 0.8:
                    confidence_emoji = "🔥"
                elif match['similarity'] > 0.6:
                    confidence_emoji = "✅"
                else:
                    confidence_emoji = "⚡"
                
                # Emoji según tipo de match
                match_type_emoji = ("🎯" if match.get('match_type') == 'exact'
                                    else "🔍")
                
                # Emoji según tipo de requisito
                req_type = match.get('requirement_type', 'unknown')
                if req_type == 'must_have':
                    type_emoji = "🔴"  # Rojo para obligatorios
                    type_text = "Obligatorio"
                elif req_type == 'nice_to_have':
                    type_emoji = "🟡"  # Amarillo para deseables
                    type_text = "Deseable"
                else:
                    type_emoji = "⚪"
                    type_text = "Otro"
                
                evidence = match.get('evidence',
                                    'Detectado por similitud semántica')
                section = match.get('section', 'N/A')
                similarity = match['similarity']
                
                result += f"""
{confidence_emoji} **{match['requirement']}** {type_emoji} *{type_text}*
   {match_type_emoji} *Evidencia*: {evidence}
   📍 *Sección*: {section} | 💪 *Similitud*: {similarity:.1%}
"""
        else:
            result += "\n*No se encontraron matches con suficiente confianza.*\n"
        
        if gaps:
            result += f"\n\n### ❌ Requisitos Faltantes ({len(gaps)}):\n"
            for gap in gaps[:8]:  # Mostrar top 8 gaps
                if isinstance(gap, dict):
                    req_text = gap.get('requirement', gap)
                    req_type = gap.get('requirement_type', 'unknown')
                    if req_type == 'must_have':
                        type_emoji = "🔴"
                        type_text = "Obligatorio"
                    elif req_type == 'nice_to_have':
                        type_emoji = "🟡"
                        type_text = "Deseable"
                    else:
                        type_emoji = "⚪"
                        type_text = "Otro"
                    result += f"• {req_text} {type_emoji} *{type_text}*\n"
                else:
                    result += f"• {gap}\n"
            
            if len(gaps) > 8:
                result += f"• ... y {len(gaps) - 8} requisitos más\n"
                
            result += ("\n**💡 Recomendación**: Considera fortalecer "
                      "estas áreas para mejorar tu perfil.\n")
        else:
            result += ("\n\n### 🎉 ¡Excelente!\n"
                      "Tu perfil cubre todos los requisitos identificados.\n")
        
        return result
    
    def _extract_basic_requirements(self, job_text: str) -> List[str]:
        """Extrae requisitos básicos del texto de la oferta"""
        import re
        
        # Buscar tecnologías comunes
        tech_patterns = [
            r'\b(python|java|javascript|react|angular|vue|node\.?js)\b',
            r'\b(html|css|sql|mysql|postgresql|mongodb)\b',
            r'\b(docker|kubernetes|aws|azure|git|github)\b',
            r'\b(spring|django|flask|express)\b'
        ]
        
        requirements = []
        job_lower = job_text.lower()
        
        for pattern in tech_patterns:
            matches = re.findall(pattern, job_lower, re.IGNORECASE)
            requirements.extend(matches)
        
        # Buscar frases de requisitos
        requirement_patterns = [
            r'experiencia (?:en|con) ([^.,\n]+)',
            r'conocimientos? (?:en|de) ([^.,\n]+)',
            r'dominio de ([^.,\n]+)',
            r'manejo de ([^.,\n]+)'
        ]
        
        for pattern in requirement_patterns:
            matches = re.findall(pattern, job_lower)
            # Filtrar solo strings para evitar error dict.strip()
            string_matches = [match.strip() for match in matches
                              if isinstance(match, str)]
            requirements.extend(string_matches)
        
        # Limpiar y limitar
        clean_requirements = []
        for req in requirements:
            if len(req) > 2 and len(req) < 50:
                clean_requirements.append(req)
        
        return list(set(clean_requirements))[:10]  # Max 10 requisitos únicos
    
    def _safe_join_cv_section(self, section_data) -> str:
        """Une de forma segura los datos de una sección del CV"""
        if not section_data:
            return ""
        
        texts = []
        for item in section_data:
            if isinstance(item, str):
                texts.append(item)
            elif isinstance(item, dict):
                # Si es un diccionario, extraer valores de texto
                for key, value in item.items():
                    if isinstance(value, str):
                        texts.append(value)
                    elif isinstance(value, list):
                        for subitem in value:
                            if isinstance(subitem, str):
                                texts.append(subitem)
            elif isinstance(item, list):
                # Si es una lista, procesar recursivamente
                for subitem in item:
                    if isinstance(subitem, str):
                        texts.append(subitem)
            else:
                # Para cualquier otro tipo, convertir a string
                texts.append(str(item))
        
        return ' '.join(texts)
    
    def _format_cv_preview(self, adapted_cv: Dict) -> str:
        """Formatea vista previa del CV adaptado"""
        preview = f"""
# 📄 Vista Previa del CV Adaptado

## 👤 {adapted_cv.get('personal_info', {}).get('name', 'Nombre')}

### 📝 Resumen Profesional
{adapted_cv.get('summary', 'No disponible')}

### 💼 Experiencia Profesional (Reordenada por Relevancia)
"""
        
        for i, exp in enumerate(adapted_cv.get('experience', [])[:3]):
            preview += f"""
**{i+1}. {exp.get('title', 'Título')} - {exp.get('company', 'Empresa')}**
*{exp.get('period', 'Periodo')}*
"""
            if exp.get('description'):
                for desc in exp['description'][:2]:
                    preview += f"• {desc}\n"
        
        # Skills reorganizadas
        skills = adapted_cv.get('skills', {})
        if skills.get('technical'):
            preview += f"\n### 🛠️ Habilidades Técnicas Destacadas\n{', '.join(skills['technical'][:8])}\n"
        
        # Notas de adaptación
        notes = adapted_cv.get('adaptation_notes', {})
        if notes:
            preview += f"""
### 📊 Notas de Adaptación
- **Cobertura**: {notes.get('coverage_percentage', 0)}%
- **Estrategia**: {notes.get('adaptation_strategy', 'N/A')}
- **Recomendaciones**: {'; '.join(notes.get('recommendations', [])[:2])}
"""
        
        return preview
    
    def _enrich_matching_with_types(self, matching_results: Dict,
                                    requirements_with_types: List[Dict]):
        """Enriquece los resultados del matching con información de tipos"""
        type_map = {}
        for req_info in requirements_with_types:
            type_map[req_info['requirement']] = req_info['type']
        
        # Agregar tipo a los matches
        for match in matching_results.get('matches', []):
            req_text = match['requirement']
            match['requirement_type'] = type_map.get(req_text, 'unknown')
        
        # Agregar tipo a los missing requirements
        enriched_missing = []
        for req in matching_results.get('missing_requirements', []):
            enriched_missing.append({
                'requirement': req,
                'requirement_type': type_map.get(req, 'unknown')
            })
        matching_results['missing_requirements'] = enriched_missing
    
    # ─────────────────────────────────────────────────────────────────
    #  Helpers para el rediseño Aurora
    # ─────────────────────────────────────────────────────────────────

    def _lmstudio_state(self) -> Tuple[bool, Optional[str]]:
        """Devuelve (disponible, modelo_activo) consultando el cliente global."""
        try:
            from src.llm.lmstudio_client import lmstudio_client
            return bool(lmstudio_client.available), lmstudio_client.model
        except Exception:  # noqa: BLE001
            return False, None

    def _build_results_html(
        self,
        results: Dict,
        rol_objetivo: str,
        idioma: str,
        longitud: str,
        pais: str,
        cv_text: str,
        has_files: bool,
    ) -> str:
        """Compone el bloque HTML completo del Paso 4 a partir del payload
        devuelto por CVFullAnalyzer.analyze. Tolerante a campos faltantes."""
        header = aurora.render_results_header(rol_objetivo, idioma, longitud, pais)
        row1 = (
            '<div class="aurora-grid-2">'
            + aurora.render_score_card(results.get("A_diagnosis", {}))
            + aurora.render_keywords_card(results.get("B_keywords", {}))
            + '</div>'
        )
        row2 = (
            '<div class="aurora-grid-3">'
            + aurora.render_plan_card(results.get("C_changes", {}))
            + aurora.render_cv_preview_card(cv_text, has_files)
            + aurora.render_checklist_card(results.get("F_checklist", {}))
            + '</div>'
        )
        variants = aurora.render_variants_card(results.get("E_variants", {}))
        return header + row1 + row2 + variants

    # ─────────────────────────────────────────────────────────────────
    #  UI principal (wizard Aurora)
    # ─────────────────────────────────────────────────────────────────

    def create_interface(self):
        """Crea la interfaz Gradio con el rediseño Aurora (wizard 4 pasos)."""

        lm_available, lm_model = self._lmstudio_state()

        # Tema base Gradio mínimo (el grueso del estilo vive en aurora.AURORA_CSS).
        # Solo neutralizamos colores y radios para que Gradio no choque con Aurora.
        theme = gr.themes.Base(
            primary_hue=gr.themes.colors.indigo,
            neutral_hue=gr.themes.colors.slate,
            font=[gr.themes.GoogleFont("Plus Jakarta Sans"), "system-ui", "sans-serif"],
        ).set(
            body_background_fill="transparent",
            body_background_fill_dark="transparent",
            block_background_fill="transparent",
            block_background_fill_dark="transparent",
            block_border_width="0px",
            block_radius="12px",
        )

        with gr.Blocks(
            title="JobFit Agent",
            theme=theme,
            css=aurora.AURORA_CSS,
            # El toggle de tema vive ahora en AURORA_HEAD (script en <head> con
            # event delegation). No usamos js= para no duplicar el listener.
            head=aurora.AURORA_HEAD,
            analytics_enabled=False,
        ) as app:

            # ── Barra global sticky con toggle de tema ────────────────
            gr.HTML(aurora.render_tbar("Análisis Pro ATS · IA local"))

            # ── Shell del wizard ──────────────────────────────────────
            with gr.Column(elem_classes=["aurora", "aurora-shell"]):

                # App top bar (marca + pill de estado LM Studio)
                topbar_html = gr.HTML(aurora.render_app_topbar(lm_available, lm_model))

                # Stepper (4 nodos, se actualiza con cada navegación)
                stepper_html = gr.HTML(aurora.render_stepper(1))

                # Estado del paso actual (1..4)
                state_step = gr.State(1)
                # Estado del último análisis para regenerar HTML en cambios de variante
                state_results = gr.State(None)

                # ── PASO 1: Subir CV ──────────────────────────────────
                with gr.Column(visible=True, elem_classes=["aurora-body"]) as g_step1:
                    gr.HTML(
                        '<div class="aurora-eyebrow">Paso 1 de 4</div>'
                        '<h2>Sube tu CV</h2>'
                        '<p>PDF, DOCX o TXT (máx. 10 MB). Tus datos no salen de tu máquina.</p>'
                    )
                    s1_cv_file = gr.File(
                        label="Arrastra tu CV o haz clic para seleccionar",
                        file_types=[".pdf", ".docx", ".txt"],
                    )
                    s1_alert = gr.HTML(visible=False)
                    with gr.Row():
                        s1_next = gr.Button("Siguiente →", variant="primary", size="lg")

                # ── PASO 2: Oferta ────────────────────────────────────
                # visible=True: render anticipado (igual que el Paso 3). El Paso 2
                # contiene el acordeón de auditoría; con render perezoso quedaba en
                # display:none al mostrarlo. El app.load lo colapsa al cargar.
                with gr.Column(visible=True, elem_classes=["aurora-body"]) as g_step2:
                    gr.HTML(
                        '<div class="aurora-eyebrow">Paso 2 de 4</div>'
                        '<h2>Pega la oferta</h2>'
                        '<p>Usa la URL del portal (LinkedIn, Indeed, InfoJobs, Tecnoempleo…) '
                        'o pega el texto completo de la descripción.</p>'
                    )
                    s2_job_url = gr.Textbox(
                        label="URL de la oferta",
                        placeholder="https://www.linkedin.com/jobs/view/...",
                        lines=1,
                    )
                    s2_job_text = gr.Textbox(
                        label="O pega aquí el texto de la oferta",
                        placeholder="Descripción completa de la oferta…",
                        lines=10,
                    )
                    # Auditoría de realismo opcional: reutiliza la MISMA oferta de
                    # arriba (no se vuelve a pedir la URL/texto en otro sitio).
                    with gr.Accordion("🔍 Auditar realismo de la oferta (opcional)", open=False):
                        gr.Markdown(
                            "Comprueba si la oferta es realista antes de adaptar tu CV. "
                            "Usa la URL o el texto introducidos arriba."
                        )
                        s2_audit_btn = gr.Button("Auditar realismo", variant="secondary")
                        s2_audit_summary = gr.Markdown()
                        s2_audit_cats = gr.Markdown()
                        s2_audit_json = gr.Code(label="Datos estructurados (JSON)", language="json")
                    s2_audit_btn.click(
                        fn=self.audit_job_offer,
                        inputs=[s2_job_url, s2_job_text],
                        outputs=[s2_audit_summary, s2_audit_cats, s2_audit_json],
                    )
                    s2_alert = gr.HTML(visible=False)
                    with gr.Row():
                        s2_prev = gr.Button("← Atrás", variant="secondary")
                        s2_next = gr.Button("Siguiente →", variant="primary", size="lg")

                # ── PASO 3: Preferencias ──────────────────────────────
                # visible=True a propósito: Gradio 6 renderiza las columnas ocultas
                # de forma perezosa, y al mostrar por primera vez una columna con
                # gr.Dropdown queda en display:none (bug). Forzando el render inicial,
                # el app.load de abajo la colapsa y luego navegar es solo un flip de
                # display sobre una columna ya renderizada (sí funciona).
                with gr.Column(visible=True, elem_classes=["aurora-body"]) as g_step3:
                    gr.HTML(
                        '<div class="aurora-eyebrow">Paso 3 de 4</div>'
                        '<h2>Ajusta tus preferencias</h2>'
                        '<p>Estos parámetros guían cómo el LLM reescribe tu CV.</p>'
                    )
                    with gr.Row():
                        s3_idioma = gr.Dropdown(
                            choices=["ES", "EN", "FR", "DE", "PT"],
                            value="ES",
                            label="Idioma del CV final",
                        )
                        s3_longitud = gr.Dropdown(
                            choices=["1 página", "2 páginas"],
                            value="2 páginas",
                            label="Longitud deseada",
                        )
                    with gr.Row():
                        s3_pais = gr.Textbox(
                            label="País / mercado (opcional)",
                            placeholder="Ej: España, Latinoamérica…",
                            lines=1,
                        )
                        s3_rol = gr.Textbox(
                            label="Rol objetivo (si difiere de la oferta)",
                            placeholder="Ej: Data Analyst Senior",
                            lines=1,
                        )
                    s3_nivel = gr.Dropdown(
                        choices=["", "Junior", "Mid", "Senior", "Lead / Principal"],
                        value="",
                        label="Nivel deseado",
                    )
                    s3_status = gr.HTML(visible=False)
                    with gr.Row():
                        s3_prev = gr.Button("← Atrás", variant="secondary")
                        s3_analyze = gr.Button("🚀 Analizar y generar informe", variant="primary", size="lg")

                # ── PASO 4: Resultados ────────────────────────────────
                # visible=True: render anticipado por consistencia (evita el bug de
                # render perezoso si más adelante se enriquece este paso). El
                # app.load lo colapsa al cargar.
                with gr.Column(visible=True, elem_classes=["aurora-body"]) as g_step4:
                    results_html = gr.HTML(
                        '<div class="aurora-eyebrow">Paso 4 de 4</div>'
                        '<h2>Resultados</h2>'
                        '<p>El análisis aparecerá aquí cuando pulses «Analizar».</p>'
                    )
                    with gr.Row():
                        s4_cv_textbox = gr.Textbox(
                            label="CV reescrito (texto plano)",
                            lines=12,
                            interactive=True,
                        )
                    with gr.Row():
                        s4_download_txt = gr.File(label="⬇ TXT", interactive=False)
                        s4_download_docx = gr.File(label="⬇ DOCX", interactive=False)
                    with gr.Row():
                        s4_prev = gr.Button("← Atrás", variant="secondary")
                        s4_new = gr.Button("✨ Nuevo análisis", variant="primary")

            # ── Sección secundaria: herramientas + diagnóstico ────────
            with gr.Accordion("🔧 Herramientas avanzadas y diagnóstico", open=False):
                with gr.Tabs():
                    # (La auditoría de oferta se integró en el Paso 2 del wizard,
                    #  reutilizando el mismo input de oferta — sin duplicarlo aquí.)

                    # Diagnóstico del sistema
                    with gr.TabItem("Diagnóstico"):
                        diag_md = gr.Markdown(value=self.get_diagnostics())
                        diag_refresh = gr.Button("Actualizar diagnóstico", variant="secondary")
                        diag_refresh.click(fn=self.get_diagnostics, inputs=[], outputs=[diag_md])

                        gr.Markdown("### Logs recientes")
                        log_lines = gr.Slider(50, 500, value=100, step=50, label="Líneas a mostrar")
                        log_box = gr.Textbox(
                            value=self.get_recent_logs(100),
                            label="Últimas líneas",
                            lines=18,
                        )
                        log_refresh = gr.Button("Actualizar logs", variant="secondary")
                        log_refresh.click(fn=self.get_recent_logs, inputs=[log_lines], outputs=[log_box])
                        clear_cache_btn = gr.Button("🗑 Limpiar caché de análisis", variant="secondary")
                        clear_cache_msg = gr.Markdown()
                        clear_cache_btn.click(
                            fn=lambda: (self.full_analyzer.clear_cache(), "✅ Caché limpiada.")[1],
                            inputs=[],
                            outputs=[clear_cache_msg],
                        )

                    # Sobre JobFit
                    with gr.TabItem("Información"):
                        gr.Markdown("""
### Sobre JobFit Agent

JobFit analiza una oferta y adapta tu CV **sin inventar nada**, con IA local (LM Studio).
Privacidad por defecto: nada de lo que subes sale de tu máquina.

**Principios de veracidad:**
- ✅ Reorganiza información real del CV.
- ✅ Destaca experiencias y skills existentes.
- ❌ Nunca inventa ni infiere datos.

**Algoritmos:**
- Embeddings semánticos (`all-MiniLM-L6-v2`) para matching CV ↔ requisitos.
- LM Studio (recomendado: Qwen2.5-14B-Instruct) para los 6 entregables ATS.

Más detalle en [`docs/STRUCTURE.md`](docs/STRUCTURE.md) y [`docs/SETUP.md`](docs/SETUP.md).
""")

            # ── Lógica de navegación del wizard ───────────────────────

            def _goto(step: int):
                """Devuelve los updates para mostrar el paso `step` y actualizar stepper/estado."""
                return (
                    gr.update(visible=step == 1),
                    gr.update(visible=step == 2),
                    gr.update(visible=step == 3),
                    gr.update(visible=step == 4),
                    aurora.render_stepper(step),
                    step,
                )

            def go_step1_next(cv_file):
                if not cv_file:
                    return (
                        gr.update(),  # step1 visible (no cambia)
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        aurora.render_stepper(1),
                        1,
                        gr.update(value=aurora.render_alert("Sube un CV (PDF, DOCX o TXT) para continuar."), visible=True),
                    )
                return (*_goto(2), gr.update(visible=False))

            def go_step2_next(url, text):
                if not (url or "").strip() and not (text or "").strip():
                    return (
                        gr.update(visible=False),
                        gr.update(),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        aurora.render_stepper(2),
                        2,
                        gr.update(value=aurora.render_alert("Pega la URL o el texto de la oferta."), visible=True),
                    )
                return (*_goto(3), gr.update(visible=False))

            def go_back(target: int):
                return _goto(target)

            def go_new_analysis():
                # Volver al paso 1 limpiando alertas
                return (*_goto(1), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False))

            # ── Análisis: paso 3 → paso 4 ─────────────────────────────

            def run_analysis(
                cv_file,
                job_url,
                job_text,
                idioma,
                longitud,
                pais,
                rol_objetivo,
                nivel,
                progress=gr.Progress(),
            ):
                # Delega en analyze_full_cv y mapea su salida tupla a HTML Aurora
                try:
                    result = self.analyze_full_cv(
                        cv_file, job_url, job_text,
                        idioma, longitud, pais, rol_objetivo, nivel,
                        progress=progress,
                    )
                except TypeError:
                    # Compat con versiones de analyze_full_cv sin el kwarg progress
                    result = self.analyze_full_cv(
                        cv_file, job_url, job_text,
                        idioma, longitud, pais, rol_objetivo, nivel,
                    )

                # Estructura de result: (tab_a, tab_b, tab_c, tab_d, tab_e, tab_f, txt_path, docx_path, status)
                if isinstance(result, tuple) and len(result) >= 9:
                    tab_a, tab_b, tab_c, tab_d, tab_e, tab_f, txt_path, docx_path, status = result
                else:
                    err_html = aurora.render_alert(
                        "Error procesando el análisis. Revisa logs/jobfit.log.", "bad"
                    )
                    return (
                        # no avanzamos de paso
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(),
                        gr.update(visible=False),
                        aurora.render_stepper(3),
                        3,
                        err_html,
                        gr.update(),
                        None,
                        None,
                        None,
                    )

                # Si tab_a empieza con ❌ es un error de validación (CV faltante, URL inválida…).
                if isinstance(tab_a, str) and tab_a.startswith("❌"):
                    return (
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(),
                        gr.update(visible=False),
                        aurora.render_stepper(3),
                        3,
                        gr.update(value=aurora.render_alert(tab_a, "bad"), visible=True),
                        gr.update(),
                        None,
                        None,
                        None,
                    )

                # Recuperamos el payload completo (cv_full_analyzer cachea por hash)
                # No exponemos las dataclasses ricas, las regeneramos desde tab_X.
                # Más simple: reusamos los datos ya cacheados del analyzer.
                cache = next(iter(self.full_analyzer._cache.values()), {})
                results_payload = cache if cache else {
                    "A_diagnosis": {},
                    "B_keywords": {},
                    "C_changes": {},
                    "F_checklist": {},
                    "E_variants": {},
                }

                cv_text_for_preview = tab_d if isinstance(tab_d, str) else ""
                html_block = self._build_results_html(
                    results_payload,
                    rol_objetivo or "",
                    idioma or "ES",
                    longitud or "2 páginas",
                    pais or "",
                    cv_text_for_preview,
                    has_files=bool(txt_path or docx_path),
                )

                return (
                    gr.update(visible=False),  # step1
                    gr.update(visible=False),  # step2
                    gr.update(visible=False),  # step3
                    gr.update(visible=True),   # step4
                    aurora.render_stepper(4),
                    4,
                    gr.update(visible=False),  # alert s3
                    html_block,                # results_html
                    cv_text_for_preview,       # s4_cv_textbox
                    txt_path,
                    docx_path,
                )

            # ── Wiring de eventos ─────────────────────────────────────

            common_nav_outputs = [g_step1, g_step2, g_step3, g_step4, stepper_html, state_step]

            s1_next.click(
                fn=go_step1_next,
                inputs=[s1_cv_file],
                outputs=common_nav_outputs + [s1_alert],
            )
            s2_prev.click(fn=lambda: _goto(1), inputs=[], outputs=common_nav_outputs)
            s2_next.click(
                fn=go_step2_next,
                inputs=[s2_job_url, s2_job_text],
                outputs=common_nav_outputs + [s2_alert],
            )
            s3_prev.click(fn=lambda: _goto(2), inputs=[], outputs=common_nav_outputs)

            s3_analyze.click(
                fn=run_analysis,
                inputs=[
                    s1_cv_file, s2_job_url, s2_job_text,
                    s3_idioma, s3_longitud, s3_pais, s3_rol, s3_nivel,
                ],
                outputs=common_nav_outputs + [
                    s3_status,           # alert paso 3
                    results_html,        # bloque HTML del paso 4
                    s4_cv_textbox,
                    s4_download_txt,
                    s4_download_docx,
                ],
            )
            s4_prev.click(fn=lambda: _goto(3), inputs=[], outputs=common_nav_outputs)
            s4_new.click(
                fn=go_new_analysis,
                inputs=[],
                outputs=common_nav_outputs + [s1_alert, s2_alert, s3_status],
            )

            # Al cargar, colapsar al Paso 1. El Paso 3 se crea visible=True para
            # forzar su render inicial (evita el bug de Gradio 6 con dropdowns en
            # columnas perezosas); este load lo oculta hasta que se navegue a él.
            app.load(fn=lambda: _goto(1), inputs=[], outputs=common_nav_outputs)

        return app


def launch_app():
    """Lanza la aplicación"""
    app = JobFitApp()
    interface = app.create_interface()
    
    # Try multiple ports to avoid conflicts
    ports_to_try = [7860, 7861, 7862, 7863, 7864]
    
    for port in ports_to_try:
        try:
            interface.launch(
                server_name="0.0.0.0",
                server_port=port,
                share=False,
                debug=True,
                theme=gr.themes.Soft()
            )
            break
        except Exception as e:
            if "Cannot find empty port" in str(e) and port != ports_to_try[-1]:
                print(f"Port {port} is busy, trying next port...")
                continue
            else:
                raise e


if __name__ == "__main__":
    launch_app()
