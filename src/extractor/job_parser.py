import re
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from config.settings import settings

# Importar cliente LM Studio
try:
    from src.llm.lmstudio_client import lmstudio_client
except ImportError:
    lmstudio_client = None


class JobOffer(BaseModel):
    """Modelo para una oferta de trabajo"""
    title: Optional[str] = Field(None, description="Título del puesto")
    seniority: Optional[str] = Field(None, description="Nivel de seniority")
    location: Optional[str] = Field(None, description="Ubicación del trabajo")
    salary_range: Optional[str] = Field(None, description="Rango salarial")
    must_have: List[str] = Field(default_factory=list, description="Requisitos obligatorios")
    nice_to_have: List[str] = Field(default_factory=list, description="Requisitos deseables")
    years_experience: Optional[str] = Field(None, description="Años de experiencia requeridos")
    education: Optional[str] = Field(None, description="Educación requerida")
    raw_text: str = Field(..., description="Texto original de la oferta")
    description: str = Field(..., description="Descripción de la oferta")


class JobParser:
    """Parser para extraer información estructurada de ofertas de trabajo"""
    
    def __init__(self):
        """Inicializar el parser"""
        import logging
        self.logger = logging.getLogger(__name__)
    
    def extract_job_data(self, job_text: str) -> Dict:
        """Extrae información estructurada de una oferta de trabajo"""
        # Validar entrada
        if not job_text or not isinstance(job_text, str):
            job_text = ""
            
        # Limpiar texto
        cleaned_text = self._clean_job_text(job_text)
        
        # 1. Intentar con LM Studio si está configurado y disponible
        if settings.use_lmstudio and lmstudio_client and lmstudio_client.available:
            try:
                self.logger.info("Usando LM Studio para extraer información...")
                result = lmstudio_client.extract_job_info(cleaned_text)
                if result:
                    result['raw_text'] = cleaned_text
                    result['source'] = 'lmstudio'
                    # Post-procesar para completar campos null
                    result = self._post_process_extraction(result, cleaned_text)
                    self.logger.info("Extracción exitosa con LM Studio")
                    return result
                else:
                    self.logger.warning("LM Studio no pudo extraer información, usando fallback")
            except Exception as e:
                self.logger.error(f"Error con LM Studio: {e}")
        
        # 2. Usar extracción basada en reglas como fallback
        self.logger.info("Usando extracción basada en reglas...")
        result = self._extract_with_rules(cleaned_text)
        result['source'] = 'rules'
        return result
    
    def _post_process_extraction(self, result: Dict, original_text: str) -> Dict:
        """Post-procesa la extracción para completar campos null con lógica"""
        
        # 1. Inferir seniority desde años de experiencia si está null
        if not result.get('seniority') and result.get('years_experience'):
            years_str = str(result['years_experience'])
            try:
                # Extraer el número de años (puede ser "2", "2-3", "2 años", etc.)
                import re
                years_match = re.search(r'(\d+)', years_str)
                if years_match:
                    years = int(years_match.group(1))
                    if years >= 7:
                        result['seniority'] = 'senior'
                        self.logger.info(f"Seniority inferido: senior (desde {years} años)")
                    elif years >= 3:
                        result['seniority'] = 'mid'
                        self.logger.info(f"Seniority inferido: mid (desde {years} años)")
                    elif years >= 0:
                        result['seniority'] = 'junior'
                        self.logger.info(f"Seniority inferido: junior (desde {years} años)")
            except Exception as e:
                self.logger.debug(f"No se pudo inferir seniority desde años: {e}")
        
        # 2. Si seniority aún es null, intentar detectarlo del texto original
        if not result.get('seniority'):
            seniority = self._extract_seniority(original_text.lower())
            if seniority:
                result['seniority'] = seniority
                self.logger.info(f"Seniority detectado del texto: {seniority}")
        
        # 3. Si education es null, intentar detectarla
        if not result.get('education'):
            education = self._extract_education(original_text.lower())
            if education:
                result['education'] = education
                self.logger.info(f"Educación detectada: {education}")
        
        return result
    
    def _extract_with_rules(self, job_text: str) -> Dict:
        """Extrae información usando reglas y expresiones regulares"""
        # Validar que job_text no sea None o vacío
        if not job_text or not isinstance(job_text, str):
            job_text = ""
            
        job_text_lower = job_text.lower()
        
        # Extraer información básica
        title = self._extract_title(job_text)
        seniority = self._extract_seniority(job_text_lower)
        location = self._extract_location(job_text)
        salary_range = self._extract_salary(job_text)
        years_experience = self._extract_years_experience(job_text_lower)
        education = self._extract_education(job_text_lower)
        
        # Extraer requisitos
        must_have, nice_to_have = self._extract_requirements(job_text)
        
        return {
            "title": title,
            "seniority": seniority,
            "location": location,
            "salary_range": salary_range,
            "must_have": must_have,
            "nice_to_have": nice_to_have,
            "years_experience": years_experience,
            "education": education,
            "raw_text": job_text,
            "description": job_text[:1000] + "..." if len(job_text) > 1000 else job_text
        }
    
    def _clean_job_text(self, text: str) -> str:
        """Limpia el texto de la oferta"""
        # Validar entrada
        if not text or not isinstance(text, str):
            return ""
            
        # Remover espacios excesivos
        text = re.sub(r'\s+', ' ', text)
        
        # Remover URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remover caracteres especiales problemáticos
        text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
        
        return text.strip()
    
    def _extract_title(self, text: str) -> Optional[str]:
        """Extrae el título del puesto"""
        if not text or not isinstance(text, str):
            return None
        
        # Patrones mejorados para títulos
        title_patterns = [
            r'(?:puesto|posición|vacante|oferta):\s*([^\n.]+)',
            r'buscamos\s+(?:un|una|un/a)?\s*([^,]+?)(?:\s+(?:con|que|para|se))',
            r'(?:título|title|job title):\s*([^\n.]+)',
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,4})(?:\s*[-–]|\s+en|\s+con|$)',
        ]
        
        job_keywords = [
            'analyst', 'analista', 'developer', 'desarrollador', 'engineer',
            'ingeniero', 'data', 'consultant', 'consultor', 'specialist',
            'especialista', 'técnico', 'technician', 'manager', 'director',
            'coordinator', 'coordinador', 'architect', 'arquitecto'
        ]
        
        for pattern in title_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                title = matches[0].strip()
                title = re.sub(r'\s+', ' ', title)
                title = re.sub(r'^(?:un|una|un/a|el|la)\s+', '', title, flags=re.IGNORECASE)
                
                if (5 <= len(title) <= 70 and
                    any(keyword in title.lower() for keyword in job_keywords)):
                    return title.title()
        
        # Buscar en primeras líneas
        lines = [l.strip() for l in text.split('\n')[:15] if l.strip()]
        for line in lines:
            if (8 <= len(line) <= 80 and
                not any(x in line.lower() for x in ['http', '@', 'www', 'ubicación', 'salario']) and
                any(keyword in line.lower() for keyword in job_keywords)):
                # Limpiar línea
                line = re.sub(r'[\[\]()]', '', line)
                line = re.sub(r'^\d+[\.)\s]+', '', line)
                return line.strip()
        
        return None
    
    def _extract_seniority(self, text: str) -> Optional[str]:
        """Extrae el nivel de seniority"""
        if not text or not isinstance(text, str):
            return None
        
        text_lower = text.lower()
        
        # Orden de prioridad (más específico primero)
        seniority_levels = [
            ('lead', ['tech lead', 'team lead', 'principal', 'architect', 'staff', 'director']),
            ('senior', ['senior', r'sr\.', ' sr ', 'sénior', 'experto', 'avanzado']),
            ('mid', ['mid level', 'middle', 'semi senior', 'intermediate', 'mid-level']),
            ('junior', ['junior', r'jr\.', ' jr ', 'trainee', 'entry level', 'graduate', 'inicial'])
        ]
        
        # Buscar en orden de especificidad
        for level, keywords in seniority_levels:
            for keyword in keywords:
                # Usar regex para word boundaries
                if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
                    return level
        
        # Inferir de años de experiencia si está disponible
        years_match = re.search(r'(\d+)\s*[-–]?\s*(\d+)?\s*años?\s*de\s*experiencia', text_lower)
        if years_match:
            min_years = int(years_match.group(1))
            if min_years >= 7:
                return 'senior'
            elif min_years >= 3:
                return 'mid'
            elif min_years >= 0:
                return 'junior'
        
        return None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extrae la ubicación del trabajo"""
        location_patterns = [
            r'(?:ubicación|location|lugar):\s*([^.\n,]+)',
            r'oficinas?\s+(?:de|en)\s+([^.\n,]+)',
            r'(?:trabajo|position|puesto)\s+en\s+([A-Z][a-zá-ú]+(?:\s+[A-Z][a-zá-ú]+)?)',
            r'(?:based|ubicado|situado)\s+en\s+([^.\n,]+)',
        ]
        
        for pattern in location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                location = matches[0].strip()
                # Limpiar y validar
                location = re.sub(r'\s+', ' ', location)
                if 3 <= len(location) <= 50:
                    return location.title()
        
        # Ciudades españolas principales
        cities = [
            'Madrid', 'Barcelona', 'Valencia', 'Sevilla', 'Bilbao',
            'Málaga', 'A Coruña', 'Coruña', 'Zaragoza', 'Murcia',
            'Palma', 'Las Palmas', 'Alicante', 'Córdoba', 'Valladolid'
        ]
        
        # Modalidades de trabajo
        modalities = ['Remoto', 'Remote', 'Híbrido', 'Hybrid', 'Teletrabajo']
        
        text_lower = text.lower()
        for city in cities:
            if city.lower() in text_lower:
                # Verificar si hay modalidad
                for modality in modalities:
                    if modality.lower() in text_lower:
                        return f"{city} ({modality})"
                return city
        
        # Solo modalidad
        for modality in modalities:
            if modality.lower() in text_lower:
                return modality
        
        return None
    
    def _extract_salary(self, text: str) -> Optional[str]:
        """Extrae el rango salarial"""
        salary_patterns = [
            # Rangos: 18.000-24.000€ o 18k-24k
            r'(\d{2,3})[\.,]?(\d{3})?\s*[-–]\s*(\d{2,3})[\.,]?(\d{3})?\s*[€k]',
            # Salario único: 30.000€ o 30k
            r'(?:salario|salary|sueldo)[^\d]*(\d{2,3})[\.,]?(\d{3})?\s*[€k]',
            # Formato k: 30-40k o 30k
            r'(\d{2,3})\s*[-–]\s*(\d{2,3})\s*k',
            r'(\d{2,3})\s*k[€\s]',
        ]
        
        for pattern in salary_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                match = matches[0]
                if isinstance(match, tuple):
                    # Filtrar elementos vacíos
                    parts = [p for p in match if p]
                    if len(parts) >= 2:
                        # Rango
                        val1 = int(parts[0])
                        val2 = int(parts[1]) if len(parts) > 1 else None
                        # Validar que sean valores razonables (15k-200k)
                        if val2 and 15 <= val1 <= 200 and 15 <= val2 <= 200:
                            return f"{val1}k-{val2}k€"
                        elif 15 <= val1 <= 200:
                            return f"{val1}k€"
                    elif len(parts) == 1:
                        val = int(parts[0])
                        if 15 <= val <= 200:
                            return f"{val}k€"
                else:
                    val = int(match)
                    if 15 <= val <= 200:
                        return f"{val}k€"
        
        return None
    
    def _extract_years_experience(self, text: str) -> Optional[str]:
        """Extrae años de experiencia"""
        years_patterns = [
            # Rangos: "3-5 años", "3 a 5 años"
            r'(\d+)\s*[-–a]\s*(\d+)\s*años',
            # Con +: "5+ años", "5 + años"
            r'(\d+)\s*\+\s*años',
            # Estándar: "5 años de experiencia"
            r'(\d+)\s*años?\s*de\s*experiencia',
            # Contexto: "experiencia de 5 años"
            r'experiencia.*?(\d+)\s*años?',
            # Mínimo: "mínimo 5 años"
            r'mínimo\s*(\d+)\s*años?',
            # Al menos: "al menos 3 años"
            r'al\s+menos\s+(\d+)\s*años?',
        ]
        
        for pattern in years_patterns:
            matches = re.findall(pattern, text)
            if matches:
                # Extraer el número y validarlo
                years_value = matches[0]
                # Si es una tupla (rango), tomar el segundo valor (máximo)
                if isinstance(years_value, tuple):
                    years_value = years_value[1] if years_value[1] else years_value[0]
                
                # Convertir a entero y validar que sea razonable (1-20 años)
                try:
                    years_int = int(years_value)
                    if 1 <= years_int <= 20:  # Rango razonable para experiencia
                        return str(years_int)
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def _extract_education(self, text: str) -> Optional[str]:
        """Extrae requisitos de educación"""
        education_patterns = [
            r'(?:educación|education|formación|titulación):\s*([^\n.]+)',
            r'(?:grado|licenciatura|título)(?:\s+en|\s+de)?\s+([^\n.,]{10,60})',
            r'(?:máster|master|msc|mba)(?:\s+en)?\s+([^\n.,]{10,60})',
            r'(?:ingeniería|engineering)(?:\s+en)?\s+([^\n.,]{10,60})',
        ]
        
        for pattern in education_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                education = matches[0].strip()
                education = re.sub(r'\s+', ' ', education)
                if 5 <= len(education) <= 80:
                    return education.capitalize()
        
        # Buscar keywords generales
        keywords = ['grado', 'licenciatura', 'ingeniería', 'máster', 'master', 
                   'doctorado', 'fp', 'formación profesional', 'universitario']
        
        for keyword in keywords:
            if keyword in text.lower():
                # Extraer contexto
                pattern = rf'.{{0,40}}{keyword}.{{0,60}}'
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    context = matches[0].strip()
                    context = re.sub(r'\s+', ' ', context)
                    if 10 <= len(context) <= 100:
                        return context.capitalize()
        
        return None
    
    def _extract_requirements(self, text: str) -> tuple[List[str], List[str]]:
        """Extrae requisitos must-have y nice-to-have"""
        must_have = []
        nice_to_have = []
        
        # Lista expandida de tecnologías y herramientas específicas
        technologies = [
            # Lenguajes de programación
            'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
            'node.js', 'php', 'ruby', 'go', 'rust', 'kotlin', 'swift', 'c++', 'c#',
            
            # Bases de datos y Big Data
            'sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'elasticsearch',
            'bigquery', 'snowflake', 'oracle', 'sqlserver', 'cassandra',
            
            # Analytics y BI
            'google analytics', 'ga4', 'power bi', 'tableau', 'looker', 'qlik',
            'adobe analytics', 'segment', 'mixpanel', 'amplitude',
            'herramientas de bi', 'business intelligence',
            
            # Cloud y DevOps
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
            'jenkins', 'gitlab', 'github', 'circleci', 'azure purview',
            'microsoft data quality services',
            
            # Data Science y ML
            'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch',
            'spark', 'hadoop', 'airflow', 'apache beam', 'dataflow',
            'matplotlib', 'seaborn', 'plotly',
            
            # Herramientas de desarrollo y datos
            'git', 'jira', 'confluence', 'slack', 'teams', 'figma',
            'postman', 'swagger', 'api rest', 'excel', 'excel avanzado',
            'etl', 'procesos etl', 'almacenamiento',
            
            # Metodologías y conceptos
            'agile', 'scrum', 'kanban', 'devops', 'ci/cd', 'tdd',
            'data governance', 'gobierno del dato', 'calidad del dato',
            'catálogo de datos', 'glosario de negocio', 'data steward',
            'modelos de datos', 'gdpr', 'lopd'
        ]
        
        # Frases específicas de requisitos (para capturar soft skills y conceptos)
        requirement_phrases = [
            'experiencia en análisis de datos',
            'áreas relacionadas a datos',
            'gestión de información',
            'herramientas de análisis',
            'nivel de inglés',
            'inglés intermedio',
            'inglés avanzado',
            'capacidad de organización',
            'mentalidad analítica',
            'orientado al detalle',
            'actitud colaborativa',
            'identificar mejoras',
            'aportar soluciones',
            'ganas de aprender',
            'autonomía',
            'proactividad',
            'dashboards',
            'consultas sql',
            'informes ad hoc',
            'visualizaciones',
            'reporting',
            'control de calidad',
            'análisis exploratorio',
            'estadística descriptiva',
            'privacidad de datos',
            'seguridad de datos'
        ]
        
        # 1. Buscar tecnologías mencionadas (evitar duplicados)
        found_techs = set()
        for tech in technologies:
            if tech.lower() in text.lower() and tech not in found_techs:
                found_techs.add(tech)
                
                # Contextos que indican requisito obligatorio
                must_context = [
                    'imprescindible', 'obligatorio', 'requerido', 'necesario',
                    'must have', 'required', 'essential', 'mínimo', 'indispensable',
                    'requisitos técnicos', 'requirements', 'requisitos', 'experiencia',
                    'conocimiento', 'dominio', 'familiaridad'
                ]
                
                nice_context = [
                    'deseable', 'valorable', 'plus', 'nice to have', 'preferible',
                    'ideal', 'bonus', 'se valorará', 'appreciated', 'adicionales',
                    'extras', 'que ofrecemos', 'valorable (no necesario)', 'no necesario'
                ]
                
                # Buscar en un contexto más amplio alrededor de la tecnología
                tech_context = self._get_context_around_word(text.lower(), tech, 100)
                
                is_required = any(ctx in tech_context for ctx in must_context)
                is_nice = any(ctx in tech_context for ctx in nice_context)
                
                # Lógica mejorada para clasificar requisitos
                if 'valorable (no necesario)' in tech_context or 'no necesario' in tech_context:
                    nice_to_have.append(tech)
                elif is_nice or 'adicionales' in tech_context:
                    nice_to_have.append(tech)
                elif is_required or 'experiencia' in tech_context or 'conocimiento' in tech_context:
                    must_have.append(tech)
                else:
                    # Buscar en secciones específicas
                    if self._is_in_requirements_section(text, tech):
                        must_have.append(tech)
                    else:
                        nice_to_have.append(tech)
        
        # 1.5. Buscar frases específicas de requisitos
        text_lower = text.lower()
        for phrase in requirement_phrases:
            if phrase.lower() in text_lower:
                # Buscar contexto para determinar si es obligatorio o deseable
                phrase_context = self._get_context_around_word(text_lower, phrase, 150)
                
                # Determinar si aparece en sección de conocimientos deseables
                if any(marker in phrase_context for marker in [
                    'conocimientos deseables', 'valorable', 'deseable', 
                    'plus', 'adicional', 'ideal'
                ]):
                    nice_to_have.append(phrase)
                else:
                    # Si aparece en sección de requisitos o sin marcadores específicos
                    must_have.append(phrase)
        
        # 2. Buscar requisitos en formato de lista
        bullet_requirements = self._extract_bullet_requirements(text)
        must_have.extend(bullet_requirements['must'])
        nice_to_have.extend(bullet_requirements['nice'])
        
        # 3. Buscar frases de requisitos
        requirement_phrases = self._extract_requirement_phrases(text)
        must_have.extend(requirement_phrases['must'])
        nice_to_have.extend(requirement_phrases['nice'])
        
        # Limpiar y deduplicar
        must_have = list(set([req.strip() for req in must_have 
                             if isinstance(req, str) and len(req.strip()) > 2]))
        nice_to_have = list(set([req.strip() for req in nice_to_have 
                                if isinstance(req, str) and len(req.strip()) > 2]))
        
        # Remover duplicados entre must y nice (priorizar must)
        nice_to_have = [req for req in nice_to_have if req not in must_have]
        
        # Limitar a un número razonable: max 10 must-have y 8 nice-to-have
        return must_have[:10], nice_to_have[:8]
    
    def _get_context_around_word(self, text: str, word: str, context_size: int = 50) -> str:
        """Obtiene el contexto alrededor de una palabra"""
        index = text.find(word.lower())
        if index == -1:
            return ""
        
        start = max(0, index - context_size)
        end = min(len(text), index + len(word) + context_size)
        
        return text[start:end]
    
    def _is_in_requirements_section(self, text: str, tech: str) -> bool:
        """Verifica si la tecnología está en una sección de requisitos"""
        # Dividir el texto en secciones
        sections = re.split(r'\n\s*(?:requisitos|requirements|funciones|responsibilities)', text, flags=re.IGNORECASE)
        
        if len(sections) > 1:
            requirements_section = sections[1]
            return tech.lower() in requirements_section.lower()
        
        return False
    
    def _extract_bullet_requirements(self, text: str) -> Dict[str, List[str]]:
        """Extrae requisitos en formato de lista con viñetas"""
        bullet_requirements = {'must': [], 'nice': []}
        
        # Buscar listas con viñetas
        bullet_patterns = [
            r'[•\-\*]\s*([^.\n]+)',
            r'\d+\.\s*([^.\n]+)',
            r'[▪▫]\s*([^.\n]+)'
        ]
        
        for pattern in bullet_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if isinstance(match, str):
                    match = match.strip()
                    if len(match) > 10 and len(match) < 100:
                        # Clasificar según contexto
                        if any(word in match.lower() for word in ['valorable', 'deseable', 'plus']):
                            bullet_requirements['nice'].append(match)
                        else:
                            bullet_requirements['must'].append(match)
        
        return bullet_requirements
    
    def _extract_requirement_phrases(self, text: str) -> Dict[str, List[str]]:
        """Extrae frases que describen requisitos"""
        requirement_phrases = {'must': [], 'nice': []}
        
        # Patrones para frases de requisitos
        requirement_patterns = [
            r'experiencia (?:en|con) ([^.,\n]+)',
            r'conocimientos? (?:en|de) ([^.,\n]+)',
            r'dominio de ([^.,\n]+)',
            r'manejo de ([^.,\n]+)',
            r'capacidad (?:para|de) ([^.,\n]+)'
        ]
        
        for pattern in requirement_patterns:
            matches = re.findall(pattern, text.lower())
            # Filtrar solo strings para evitar error dict.strip()
            string_matches = [match.strip() for match in matches
                              if isinstance(match, str)]
            requirement_phrases['must'].extend(string_matches)
        
        # Limpiar y limitar
        clean_requirements = []
        for req in requirement_phrases['must']:
            if len(req) > 2 and len(req) < 50:
                clean_requirements.append(req)
        
        requirement_phrases['must'] = list(set(clean_requirements))[:10]  # Max 10 requisitos únicos
        
        return requirement_phrases