# src/utils/cv_utils.py
"""
Utilidades compartidas para normalización y manipulación de datos de CV.
"""


def normalize_cv_data(cv_data: dict) -> dict:
    """
    Normaliza un dict de CV parseado asegurando tipos consistentes en todos
    los campos clave. Previene errores 'NoneType is not iterable' en el
    pipeline de adaptación y análisis.

    - experience, education, projects → list
    - skills → dict con claves 'technical' (list) y 'other' (list)
    - raw_text → str

    Modifica el dict en-lugar y lo devuelve para facilitar encadenamiento.
    """
    if cv_data is None:
        cv_data = {}

    # Secciones que deben ser listas
    for field in ("experience", "education", "projects", "languages", "certifications"):
        if not isinstance(cv_data.get(field), list):
            cv_data[field] = cv_data.get(field) or []

    # Skills normalizado a dict {'technical': [...], 'other': [...]}
    skills_field = cv_data.get("skills")
    if isinstance(skills_field, list):
        cv_data["skills"] = {"technical": skills_field, "other": []}
    elif isinstance(skills_field, dict):
        tech = skills_field.get("technical") or []
        other = skills_field.get("other") or []
        if isinstance(tech, str):
            tech = [s.strip() for s in tech.split(",") if s.strip()]
        if isinstance(other, str):
            other = [s.strip() for s in other.split(",") if s.strip()]
        cv_data["skills"] = {"technical": list(tech), "other": list(other)}
    else:
        cv_data["skills"] = {"technical": [], "other": []}

    # raw_text debe ser str
    if not isinstance(cv_data.get("raw_text"), str):
        cv_data["raw_text"] = ""

    return cv_data
