# src/generator/ats_optimizer.py
import re
import logging

logger = logging.getLogger(__name__)

# Mapeo de nombres de mes en español/inglés → número de mes
MONTH_MAP = {
    'enero': '01', 'january': '01', 'jan': '01',
    'febrero': '02', 'february': '02', 'feb': '02',
    'marzo': '03', 'march': '03', 'mar': '03',
    'abril': '04', 'april': '04', 'apr': '04',
    'mayo': '05', 'may': '05',
    'junio': '06', 'june': '06', 'jun': '06',
    'julio': '07', 'july': '07', 'jul': '07',
    'agosto': '08', 'august': '08', 'aug': '08',
    'septiembre': '09', 'september': '09', 'sep': '09', 'sept': '09',
    'octubre': '10', 'october': '10', 'oct': '10',
    'noviembre': '11', 'november': '11', 'nov': '11',
    'diciembre': '12', 'december': '12', 'dec': '12',
}

class ATS_Optimizer:
    """
    Genera una versión de texto plano del CV optimizada para pasar filtros ATS.
    Su objetivo es inyectar palabras clave de la oferta de manera estratégica.
    """

    def optimize_cv_for_ats(self, cv_data: dict, matching_results: dict) -> str:
        """
        Genera un CV en formato de texto plano estructurado y legible.
        Organiza la información de forma clara para sistemas ATS y lectura humana.

        Args:
            cv_data (dict): El diccionario con los datos del CV parseado.
            matching_results (dict): Los resultados del análisis del SemanticMatcher.

        Returns:
            str: CV estructurado en texto plano.
        """
        logger.info("Generando CV optimizado para ATS en texto plano...")

        cv_text = []
        
        # INFORMACIÓN PERSONAL
        personal = cv_data.get('personal_info', {})
        if personal.get('name'):
            cv_text.append("="*60)
            cv_text.append(personal['name'].upper())
            cv_text.append("="*60)
            cv_text.append("")
        
        if personal.get('email') or personal.get('phone') or personal.get('location'):
            cv_text.append("CONTACTO")
            cv_text.append("-"*60)
            if personal.get('email'):
                cv_text.append(f"Email: {personal['email']}")
            if personal.get('phone'):
                cv_text.append(f"Teléfono: {personal['phone']}")
            if personal.get('location'):
                cv_text.append(f"Ubicación: {personal['location']}")
            cv_text.append("")
        
        # EXPERIENCIA PROFESIONAL
        experience = cv_data.get('experience', [])
        if experience:
            cv_text.append("PROFESSIONAL EXPERIENCE")
            cv_text.append("="*60)
            for exp in experience:
                # Solo incluir si tiene al menos título o empresa
                if not exp.get('title') and not exp.get('company'):
                    continue
                
                cv_text.append("")
                # Título del puesto
                if exp.get('title'):
                    cv_text.append(f"{exp['title']}")
                
                # Información de empresa, ubicación y período
                info_parts = []
                if exp.get('company'):
                    info_parts.append(exp['company'])
                if exp.get('location'):
                    info_parts.append(exp['location'])
                if exp.get('period'):
                    info_parts.append(self._normalize_date_period(exp['period']))
                
                if info_parts:
                    cv_text.append(" | ".join(info_parts))
                elif exp.get('period'):
                    # Si no hay empresa pero sí período
                    cv_text.append(self._normalize_date_period(exp['period']))
                
                # Responsabilidades
                if exp.get('description') and len(exp['description']) > 0:
                    valid_descriptions = [d for d in exp['description'] if len(d.strip()) > 10]
                    if valid_descriptions:
                        for desc in valid_descriptions[:6]:
                            cv_text.append(f"  • {desc.strip()}")
            cv_text.append("")
        
        # EDUCACIÓN
        education = cv_data.get('education', [])
        if education:
            cv_text.append("EDUCATION")
            cv_text.append("="*60)
            for edu in education:
                if isinstance(edu, dict):
                    # Construir la línea de educación
                    edu_line = ""
                    if edu.get('institution'):
                        edu_line = edu['institution']
                    if edu.get('degree'):
                        if edu_line:
                            edu_line += " - " + edu['degree']
                        else:
                            edu_line = edu['degree']
                    
                    if edu_line:
                        cv_text.append(f"  • {edu_line}")
                elif isinstance(edu, str):
                    cv_text.append(f"  • {edu}")
            cv_text.append("")
        
        # HABILIDADES
        skills = cv_data.get('skills', {})
        if isinstance(skills, dict):
            tech_skills = skills.get('technical', [])
            other_skills = skills.get('other', [])
            
            if tech_skills or other_skills:
                cv_text.append("SKILLS")
                cv_text.append("="*60)
                if tech_skills:
                    cv_text.append("Técnicas:")
                    cv_text.append("  " + ", ".join(tech_skills[:15]))
                if other_skills:
                    cv_text.append("Otras:")
                    cv_text.append("  " + ", ".join(other_skills[:10]))
                cv_text.append("")
        
        result = "\n".join(cv_text)
        
        # Si está vacío, usar raw_text como fallback
        if len(result.strip()) < 100:
            logger.warning("CV estructurado está vacío, usando raw_text")
            result = cv_data.get('raw_text', '')
        
        logger.info("CV optimizado para ATS generado correctamente.")
        return result

    def _normalize_date_period(self, period: str) -> str:
        """
        Convierte períodos de fecha al formato ATS-estándar MM/YYYY.
        Ejemplos:
          "octubre 2021 - 2025"   → "10/2021 - 2025"
          "Junio 2020 - Marzo 2023" → "06/2020 - 03/2023"
          "2021 - actualidad"     → "2021 - Present"
          "2021 - actual"         → "2021 - Present"
        """
        if not period:
            return period

        # Normalizar palabras de "presente/actual" a inglés estándar
        normalized = re.sub(
            r'\b(actual|actualidad|presente|present|hoy|now)\b',
            'Present', period, flags=re.IGNORECASE
        )

        # Reemplazar nombre de mes + año → MM/YYYY (ej. "octubre 2021" → "10/2021")
        def replace_month_year(m):
            month_name = m.group(1).lower()
            year = m.group(2)
            month_num = MONTH_MAP.get(month_name)
            if month_num:
                return f"{month_num}/{year}"
            return m.group(0)  # sin cambio si no se reconoce

        normalized = re.sub(
            r'\b([A-Za-záéíóúñü]+)\s+(\d{4})\b',
            replace_month_year,
            normalized
        )

        return normalized

    def _create_keyword_section(self, keywords: list) -> str:
        """Crea un bloque de texto con las palabras clave."""
        section = "\n--- COMPETENCIAS CLAVE Y PALABRAS CLAVE PARA ATS ---\n"
        section += "Como profesional orientado a resultados, poseo las siguientes competencias directamente alineadas con los requisitos de la oferta:\n"
        for keyword in keywords:
            section += f"- {keyword}\n"
        section += "--- FIN DE LA SECCIÓN DE PALABRAS CLAVE ---\n"
        return section

    def _inject_section(self, original_text: str, section_to_inject: str) -> str:
        """Inyecta la sección de palabras clave después del perfil profesional."""
        # Buscamos el final del perfil profesional, que suele estar marcado por "---"
        injection_point = original_text.find("---")
        
        if injection_point != -1:
            # Encontramos el final de la primera sección de "---"
            next_marker = original_text.find("---", injection_point + 3)
            if next_marker != -1:
                # Inyectamos después de la primera sección (después del Perfil Profesional)
                final_text = original_text[:next_marker] + section_to_inject + original_text[next_marker:]
                return final_text

        # Si no encontramos los marcadores, lo añadimos al principio como fallback
        return section_to_inject + original_text
