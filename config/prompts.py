# Prompts para diferentes componentes del sistema

AUDIT_REALISM_PROMPT = """
Analiza la siguiente oferta de trabajo y evalúa su realismo en una escala de 0-100.
Considera estos factores:
- Coherencia entre años de experiencia y seniority
- Realismo del stack tecnológico solicitado
- Coherencia del salario con el rol y ubicación
- Contradicciones en modalidad/jornada
- Requisitos excesivos o poco realistas

Oferta: {job_description}

Responde en formato JSON:
{{
    "realism_score": <0-100>,
    "signals": [
        {{"type": "warning/error", "description": "descripción del problema"}}
    ],
    "reasoning": "explicación detallada"
}}
"""

EXTRACT_JOB_PROMPT = """
Extrae la información estructurada de la siguiente oferta de trabajo.

Oferta: {job_description}

Responde en formato JSON con exactamente estos campos:
{{
    "title": "título del puesto",
    "seniority": "junior/mid/senior/lead",
    "location": "ubicación",
    "salary_range": "rango salarial si se menciona, null si no",
    "must_have": ["requisitos obligatorios"],
    "nice_to_have": ["requisitos deseables"],
    "years_experience": "años de experiencia requeridos",
    "education": "educación requerida",
    "description": "descripción completa del rol"
}}
"""

CV_ADAPTATION_PROMPT = """
Adapta el siguiente CV para la oferta de trabajo, siguiendo estas reglas estrictas:
1. NO inventes información que no esté en el CV original
2. Solo reordena y selecciona contenido existente
3. Enfatiza experiencias relevantes para la oferta
4. Crea un resumen alineado con los requisitos

CV Original: {original_cv}
Oferta: {job_offer}
Matching Results: {matching_results}

Genera un CV adaptado manteniendo toda la información veraz.
"""

MATCHING_PROMPT = """
Compara los requisitos de la oferta con las evidencias del CV.
Identifica coincidencias y gaps.

Requisitos: {requirements}
CV: {cv_content}

Responde en formato JSON:
{{
    "matches": [
        {{"requirement": "req", "evidence": "evidencia del CV", "confidence": 0.0-1.0}}
    ],
    "gaps": ["requisitos sin evidencia en el CV"]
}}
"""

# ─────────────────────────────────────────────
#  PROMPTS PARA ANÁLISIS COMPLETO ATS (A → F)
# ─────────────────────────────────────────────

# SYSTEM prompt – reclutador senior + ATS specialist
ATS_SYSTEM_PROMPT = """Actúa como reclutador/a senior, especialista en ATS y career coach.
Tu objetivo es adaptar un CV a una oferta de trabajo concreta para maximizar las posibilidades
de pasar filtros ATS y convencer a un/a reclutador/a humano/a, SIN inventar ni exagerar.

Reglas estrictas:
- No añadas tecnologías, años, certificaciones o logros que el candidato no pueda respaldar.
- Solo incorpora keywords si encajan con la experiencia real.
- Formato ATS: texto claro, sin tablas/columnas, sin iconos, sin gráficos.
- Longitud final del CV: máximo 2 páginas.
- Estilo: directo, profesional, orientado a impacto (métricas si existen).
- NUNCA añadas secciones de notas, comentarios, preguntas ni texto meta al final del CV.
- NUNCA incluyas texto como 'Este CV está optimizado...', 'Notas adicionales:', preguntas entre corchetes u observaciones al candidato.
- Genera SOLO el contenido del CV, nada más.
"""

# ── A) Diagnóstico de encaje ──────────────────
DIAGNOSIS_PROMPT = """Analiza el encaje entre el CV y la oferta de trabajo.

OFERTA:
{job_offer}

CV:
{cv_text}

Preferencias del candidato:
- Idioma del CV: {idioma}
- Longitud deseada: {longitud}
- Rol objetivo: {rol_objetivo}
- Nivel: {nivel}

Responde en formato JSON con exactamente esta estructura:
{{
    "resumen_oferta": "4-6 líneas explicando qué necesita realmente la empresa",
    "score": <número entero 0-100>,
    "razon_score": "explicación del score en 2-3 líneas",
    "fortalezas": [
        {{"fortaleza": "descripción", "cita_cv": "texto literal del CV que lo demuestra"}}
    ],
    "gaps": [
        {{"gap": "descripción del gap o riesgo", "impacto": "alto/medio/bajo"}}
    ]
}}

Incluye exactamente 5 fortalezas y 5 gaps. No inventes fortalezas que no estén en el CV.
"""

# ── B) Keywords ATS ───────────────────────────
KEYWORDS_PROMPT = """Extrae todas las keywords relevantes de la oferta de trabajo y clasifícalas.

OFERTA:
{job_offer}

CV (para verificar presencia):
{cv_text}

Responde en formato JSON con exactamente esta estructura:
{{
    "keywords": [
        {{
            "keyword": "nombre de la keyword",
            "categoria": "hard_skill | herramienta | metodologia | industria | soft_skill | certificacion | verbo_accion",
            "estado": "presente | debil | ausente",
            "ubicacion_cv": "dónde aparece en el CV (sección y forma), o null si no aparece",
            "sugerencia": "cómo reforzarla con redacción honesta, o 'No procede' si no encaja con la experiencia real"
        }}
    ]
}}

Para el campo 'estado':
- 'presente' = la keyword aparece claramente en el CV
- 'debil' = hay una referencia indirecta pero se puede reforzar
- 'ausente' = no aparece; solo sugiere incorporarla si encaja con la experiencia real del candidato

Extrae entre 20 y 40 keywords. Cubre todas las categorías mencionadas.
"""

# ── C) Plan de cambios ────────────────────────
CHANGES_PROMPT = """Propón un plan de cambios priorizado para mejorar el CV en relación a la oferta.

OFERTA:
{job_offer}

CV:
{cv_text}

DIAGNÓSTICO PREVIO (score y gaps):
{diagnosis_summary}

Responde en formato JSON con exactamente esta estructura:
{{
    "cambios": [
        {{
            "prioridad": "alto | medio | opcional",
            "seccion": "nombre de la sección del CV a modificar",
            "que_cambiar": "descripción clara de qué cambiar",
            "ejemplo": "ejemplo breve del cambio sugerido",
            "impacto": "cómo afecta al ATS y/o al reclutador"
        }}
    ]
}}

Propón entre 8 y 15 cambios. Los de prioridad 'alto' deben aparecer primero.
NUNCA sugieras añadir información que el candidato no pueda defender en una entrevista.
"""

# ── D) CV reescrito ───────────────────────────
CV_REWRITE_PROMPT = """Reescribe el CV adaptado a la oferta en texto plano, listo para enviar a una empresa.

OFERTA:
{job_offer}

CV ORIGINAL:
{cv_text}

Preferencias:
- Idioma: {idioma}
- Longitud: {longitud}
- Rol objetivo: {rol_objetivo}
- Nivel: {nivel}
- Logros medibles que el candidato puede defender: {logros}
- Stack/herramientas reales que usa: {stack}

Estructura del CV (en el idioma indicado). Usa los títulos de sección exactamente como se indican,
NO uses palabras genéricas como "Encabezado" ni "Header":
1. [Nombre completo — sin etiqueta de sección]
   [Ciudad/País · Tel · Email · LinkedIn · GitHub/Portfolio]
2. PERFIL PROFESIONAL  (o PROFESSIONAL SUMMARY si el idioma es inglés)
3. HABILIDADES  (o SKILLS)
4. EXPERIENCIA PROFESIONAL  (o PROFESSIONAL EXPERIENCE)
5. PROYECTOS  (solo si aportan valor al encaje; omitir si no hay)
6. EDUCACIÓN  (o EDUCATION)
7. IDIOMAS  (o LANGUAGES)

Reglas importantes:
- NO inventes métricas, herramientas ni logros que no estén en el CV original.
- Si falta algún dato (ej. email), simplemente omítelo; no pongas marcadores ni preguntas.
- Texto plano: sin emojis, tablas, iconos ni columnas.
- Verbos de acción al inicio de cada bullet de experiencia.
- Máximo {longitud}.
- GENERA ÚNICAMENTE EL CV. Sin notas finales, comentarios sobre el proceso, preguntas entre
  corchetes, secciones "Notas adicionales", ni ningún texto que no forme parte del CV.
"""

# ── E) Variantes Resumen + Skills ─────────────
VARIANTS_PROMPT = """Genera DOS variantes del bloque "Resumen profesional + Skills" del CV.

OFERTA:
{job_offer}

CV ORIGINAL:
{cv_text}

Preferencias:
- Idioma: {idioma}
- Rol objetivo: {rol_objetivo}
- Nivel: {nivel}

Responde en formato JSON con exactamente esta estructura:
{{
    "ats_first": {{
        "resumen": "Resumen profesional de 4-6 líneas orientado a keywords naturales, alta densidad de términos de la oferta sin que suene forzado",
        "skills": "Bloque de skills agrupado por categorías, con todas las keywords relevantes de la oferta que el candidato posee"
    }},
    "recruiter_first": {{
        "resumen": "Resumen narrativo/diferenciador de 4-6 líneas que cuenta una historia de valor, más humano y memorable",
        "skills": "Bloque de skills más selectivo, destacando las competencias más diferenciadoras del candidato"
    }}
}}

NO inventes skills ni experiencias. Solo usa lo que está en el CV original.
"""

# ── F) Checklist ATS ──────────────────────────
ATS_CHECKLIST_PROMPT = """Genera un checklist ATS final para este CV adaptado a la oferta.

OFERTA (resumen de requisitos):
{job_offer_summary}

CV ADAPTADO:
{cv_adapted}

Responde en formato JSON con exactamente esta estructura:
{{
    "checklist": [
        {{
            "punto": "descripción del punto a verificar",
            "estado": "ok | advertencia | fallo",
            "detalle": "explicación o acción recomendada"
        }}
    ]
}}

Incluye entre 12 y 15 puntos cubriendo:
- Formato y estructura (sin tablas, columnas, imágenes)
- Secciones estándar presentes
- Keywords de la oferta incorporadas
- Longitud correcta
- Datos de contacto completos
- Verbos de acción en la experiencia
- Métricas y resultados
- Sin información falsa o exagerada
- Idioma consistente
- Fechas en formato estándar
"""

# ── Extracción automática de logros y stack desde el CV ──
EXTRACT_CV_INSIGHTS_PROMPT = """Analiza el siguiente CV y extrae:
1. Los logros medibles más relevantes que el candidato puede defender en una entrevista.
   (Busca cifras, porcentajes, tiempos, equipos liderados, proyectos entregados, mejoras demostradas, etc.)
   Si no hay datos cuantitativos explícitos, describe los logros cualitativos más destacados.

2. El stack real de herramientas, tecnologías y lenguajes que el candidato usa actualmente.
   (Solo lo que aparece en el CV — no inferir ni inventar.)

CV:
{cv_text}

Responde en formato JSON con exactamente esta estructura:
{{
    "logros": [
        "logro 1 en una línea concisa",
        "logro 2 en una línea concisa"
    ],
    "stack": [
        "tecnología / herramienta 1",
        "tecnología / herramienta 2"
    ]
}}

Extrae entre 3 y 8 logros, y entre 5 y 20 elementos de stack.
Solo incluye información que esté claramente respaldada en el CV.
"""