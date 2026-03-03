from docx import Document
import PyPDF2
import pdfplumber
from typing import Dict, List, Optional
import re
import json

class CVParser:
    def __init__(self):
        self.sections = {
            'experience': ['experiencia', 'experience', 'trabajo', 'work', 'employment', 
                          'professional', 'laboral', 'trayectoria', 'historial'],
            'education': ['educación', 'formación', 'education', 'academic', 'degree', 
                         'university', 'estudios', 'titulación', 'cualificación'],
            'skills': ['habilidades', 'competencias', 'skills', 'competencies', 'conocimientos',
                      'technologies', 'tools', 'técnicas', 'idiomas', 'languages'],
            'projects': ['proyectos', 'projects', 'portfolio', 'achievements', 'logros']
        }
    
    def parse_cv(self, file_path: str, file_type: str) -> Dict:
        """Parsea CV según el tipo de archivo"""
        if file_type.lower() == 'pdf':
            text = self._extract_pdf_text(file_path)
        elif file_type.lower() in ['docx', 'doc']:
            text = self._extract_docx_text(file_path)
        elif file_type.lower() == 'txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
        else:
            raise ValueError(f"Tipo de archivo no soportado: {file_type}")
        
        return self._structure_cv_content(text)
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extrae texto de un PDF y limpia el formato"""
        text = ""
        try:
            # Intentar primero con pdfplumber (mejor para layouts complejos)
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    # Usar extract_text simple - funciona mejor para layouts complejos
                    page_text = page.extract_text(layout=False)
                    if page_text:
                        text += page_text + "\n"
            
            # Si pdfplumber no funciona, usar PyPDF2 como fallback
            if not text.strip():
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        page_text = page.extract_text()
                        text += page_text + "\n"
            
            # Limpiar y normalizar el texto
            text = self._clean_pdf_text(text)
        except Exception as e:
            print(f"Error extrayendo PDF con pdfplumber: {e}")
            # Fallback a PyPDF2
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                text = self._clean_pdf_text(text)
            except Exception as e2:
                print(f"Error con PyPDF2: {e2}")
        return text
    
    def _extract_text_with_columns(self, words: list, page_width: float) -> str:
        """Extrae texto respetando columnas del PDF"""
        if not words:
            return ""
        
        # Detectar puntos de división de columnas basado en x0
        # Usar 40% - 60% como zona de transición en lugar del punto medio exacto
        left_boundary = page_width * 0.4
        right_boundary = page_width * 0.6
        
        left_words = [w for w in words if w['x0'] < left_boundary]
        middle_words = [w for w in words if left_boundary <= w['x0'] < right_boundary]
        right_words = [w for w in words if w['x0'] >= right_boundary]
        
        # Combinar middle_words con la columna más cercana basándose en proximidad
        for word in middle_words:
            if abs(word['x0'] - left_boundary) < abs(word['x0'] - right_boundary):
                left_words.append(word)
            else:
                right_words.append(word)
        
        # Ordenar cada columna por posición vertical y horizontal
        left_words.sort(key=lambda w: (round(w['top'] / 2) * 2, w['x0']))
        right_words.sort(key=lambda w: (round(w['top'] / 2) * 2, w['x0']))
        
        # Convertir palabras a líneas de texto
        def words_to_lines(words_list):
            if not words_list:
                return []
            
            lines = []
            current_line = []
            current_top = round(words_list[0]['top'] / 2) * 2 if words_list else None
            
            for word in words_list:
                top_group = round(word['top'] / 2) * 2
                
                # Misma línea si están en el mismo grupo vertical (tolerancia 5 puntos)
                if current_top is not None and abs(top_group - current_top) < 5:
                    current_line.append(word['text'])
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word['text']]
                    current_top = top_group
            
            if current_line:
                lines.append(' '.join(current_line))
            
            return lines
        
        left_lines = words_to_lines(left_words)
        right_lines = words_to_lines(right_words)
        
        # Combinar: primero columna izquierda, luego derecha (con separador)
        all_lines = left_lines + [''] + right_lines
        
        return '\n'.join(all_lines)
    
    def _clean_pdf_text(self, text: str) -> str:
        """Limpia y normaliza texto extraído de PDF"""
        # Primero, separar secciones que están pegadas (problema común en PDFs con columnas)
        text = self._separate_sections(text)
        
        lines = text.split('\n')
        cleaned_lines = []
        skip_next = set()  # Índices a saltar
        
        for i, line in enumerate(lines):
            if i in skip_next:
                continue
                
            line = line.strip()
            if not line:
                cleaned_lines.append('')
                continue
            
            combined_line = line
            
            # Intentar unir con líneas siguientes si están cortadas
            j = i + 1
            while j < len(lines) and j < i + 3:  # Máximo 3 líneas siguientes
                next_line = lines[j].strip()
                
                if not next_line:
                    break
                
                # Unir si:
                # 1. La línea actual termina en minúscula o coma
                # 2. La siguiente empieza en minúscula
                # 3. Ambas son cortas (< 70 caracteres)
                should_merge = False
                
                if len(combined_line) < 70 and len(next_line) < 70:
                    # Si termina en minúscula o coma y sigue con minúscula
                    if (combined_line[-1].islower() or combined_line[-1] == ',') and next_line[0].islower():
                        should_merge = True
                    # Si la línea actual es muy corta (posible corte)
                    elif len(combined_line) < 40 and not next_line[0].isdigit():
                        # No es un título (no todo en mayúsculas)
                        if not combined_line.isupper():
                            should_merge = True
                
                if should_merge:
                    combined_line += ' ' + next_line
                    skip_next.add(j)
                    j += 1
                else:
                    break
            
            cleaned_lines.append(combined_line)
        
        # Filtrar líneas vacías duplicadas
        result_lines = []
        prev_empty = False
        for line in cleaned_lines:
            # Filtrar líneas basura
            if re.match(r'^De\s+DE\s+', line, re.IGNORECASE):
                continue
            if re.match(r'^[A-ZÁÉÍÓÚÑ]{2,}\s+[A-ZÁÉÍÓÚÑ]{2,}\s+[A-ZÁÉÍÓÚÑ]{2,}', line) and len(line.split()) > 5:
                # Múltiples palabras en mayúsculas seguidas = probablemente basura
                continue
            
            if not line:
                if not prev_empty:
                    result_lines.append(line)
                prev_empty = True
            else:
                result_lines.append(line)
                prev_empty = False
        
        return '\n'.join(result_lines)
    
    def _separate_sections(self, text: str) -> str:
        """Separa secciones que están pegadas en el texto"""
        # Palabras clave de secciones en mayúsculas
        section_keywords = [
            'EXPERIENCIA PROFESIONAL', 'EXPERIENCIA LABORAL', 'EXPERIENCIA',
            'FORMACIÓN Y EDUCACIÓN', 'FORMACIÓN ACADÉMICA', 'FORMACIÓN', 'EDUCACIÓN',
            'COMPETENCIAS PROFESIONALES', 'COMPETENCIAS TÉCNICAS', 'COMPETENCIAS', 'HABILIDADES',
            'CONTACTO', 'DATOS DE CONTACTO',
            'IDIOMAS', 'LANGUAGES',
            'SOBRE MÍ', 'PERFIL PROFESIONAL', 'PERFIL', 'PROFILE',
            'LOGROS', 'PROYECTOS', 'CERTIFICACIONES'
        ]
        
        # Ordenar por longitud (más largos primero) para evitar reemplazos parciales
        section_keywords.sort(key=len, reverse=True)
        
        # Separar secciones pegadas
        for keyword in section_keywords:
            # Si encuentra la keyword pegada con texto antes, separarla
            # Patrón 1: texto minúscula + KEYWORD
            text = re.sub(rf'([a-záéíóúñ.,;:])\s*{keyword}', rf'\1\n\n{keyword}', text)
            # Patrón 2: KEYWORD + otra KEYWORD
            text = re.sub(rf'{keyword}\s+([A-ZÁÉÍÓÚÑ]{{3,}})', rf'{keyword}\n\n\1', text)
        
        # Filtrar líneas basura comunes en PDFs mal extraídos
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Ignorar líneas que son claramente basura (mezcla de títulos)
            if re.match(r'^De\s+DE\s+', line, re.IGNORECASE):
                continue
            if re.match(r'^[A-ZÁÉÍÓÚÑ]{2,}\s+[A-ZÁÉÍÓÚÑ]{2,}\s+[A-ZÁÉÍÓÚÑ]{2,}', line) and len(line.split()) > 5:
                # Múltiples palabras en mayúsculas seguidas = probablemente basura
                continue
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _extract_docx_text(self, file_path: str) -> str:
        """Extrae texto de DOCX"""
        text = ""
        try:
            doc = Document(file_path)
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
        except Exception as e:
            print(f"Error extrayendo DOCX: {e}")
        return text
    
    def _structure_cv_content(self, text: str) -> Dict:
        """Estructura el contenido del CV en secciones"""
        lines = text.split('\n')
        structured_cv = {
            'personal_info': {},
            'experience': [],
            'education': [],
            'skills': {'technical': [], 'other': []},
            'projects': [],
            'raw_text': text
        }
        
        current_section = None
        current_content = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detectar sección
            section = self._detect_section(line)
            if section:
                # Guardar contenido de sección anterior
                if current_section and current_content:
                    self._add_content_to_section(
                        structured_cv, current_section, current_content
                    )
                
                current_section = section
                current_content = []
            else:
                current_content.append(line)
        
        # Procesar última sección
        if current_section and current_content:
            self._add_content_to_section(
                structured_cv, current_section, current_content
            )
        
        # Extraer información personal del inicio (más líneas para layout de 2 columnas)
        structured_cv['personal_info'] = self._extract_personal_info(lines[:50], text)
        
        return structured_cv
    
    def _detect_section(self, line: str) -> Optional[str]:
        """Detecta si una línea es un encabezado de sección"""
        line_lower = line.lower().strip()
        
        # Debe ser una línea corta y en mayúsculas o con formato de título
        if len(line) > 60:
            return None
        
        # Verificar que tenga palabras clave de sección
        for section, keywords in self.sections.items():
            for keyword in keywords:
                # La keyword debe ser una palabra completa, no parte de otra
                if keyword in line_lower:
                    # Verificar que no sea parte de una oración larga
                    words = line_lower.split()
                    if len(words) <= 5:  # Los títulos de sección son cortos
                        return section
        
        return None
    
    def _add_content_to_section(self, cv: Dict, section: str, content: List[str]):
        """Añade contenido a una sección del CV"""
        if section == 'experience':
            cv['experience'].extend(self._parse_experience(content))
        elif section == 'education':
            cv['education'].extend(self._parse_education(content))
        elif section == 'skills':
            parsed_skills = self._parse_skills(content)
            cv['skills']['technical'].extend(parsed_skills['technical'])
            cv['skills']['other'].extend(parsed_skills['other'])
        elif section == 'projects':
            cv['projects'].extend(self._parse_projects(content))
    
    def _parse_experience(self, content: List[str]) -> List[Dict]:
        """Parsea sección de experiencia"""
        experiences = []
        current_job = {}
        
        for i, line in enumerate(content):
            # Detectar fechas (múltiples formatos: YYYY-YYYY, MM/YYYY-MM/YYYY, actual, presente)
            date_patterns = [
                r'(\d{4}\s*[-–—/]\s*\d{4})',  # 2010-2015 o 2010/2015
                r'(\d{4}\s*[-–—]\s*(?:actual|actualidad|presente|present|now))',  # 2020-actual
                r'(\d{1,2}/\d{4}\s*[-–—]\s*\d{1,2}/\d{4})',  # 06/2020-12/2023
                r'(\d{1,2}/\d{4}\s*[-–—/]\s*(?:actual|actualidad|presente|present))',  # 06/2020-actual
                r'([A-Z][a-z]+\s+\d{4}\s*[-–—]\s+[A-Z][a-z]+\s+\d{4})',  # Junio 2020 - Marzo 2023
                r'([A-Z][a-z]+,\s*\d{4}\s*[-–—]\s*[A-Z][a-z]+\s*\d{4})',  # Enero, 2020 - Marzo, 2023
                r'([A-Z][a-z]+,?\s+[A-Z][a-z]+\s+\d{4}\s*[-–—]\s+[A-Z][a-z]+)',  # Octubre 2021 – Actualidad
                r'(\d{4}/\d{4})',  # 2024/2025
                r'(\d{4}\s*/\s*(?:actual|actualidad|presente|present))',  # 2022 / Actual
            ]
            
            date_match = None
            for pattern in date_patterns:
                date_match = re.search(pattern, line, re.IGNORECASE)
                if date_match:
                    break
            
            # Si encontramos una línea vacía o un guion, marca inicio de nuevo trabajo
            if not line.strip() or line.strip().startswith('---'):
                if current_job and (current_job.get('title') or current_job.get('company')):
                    experiences.append(current_job)
                    current_job = {}
                continue
            
            if date_match:
                # La línea actual puede tener ubicación antes de la fecha
                prefix = line[:date_match.start()].strip()
                date_text = date_match.group(1)
                
                location = ''
                job_title = ''
                
                # Determinar si el prefijo es ubicación o título
                if prefix and len(prefix) > 3:
                    if ',' in prefix:
                        location = prefix
                    else:
                        job_title = prefix
                
                # Si hay un trabajo previo con descripción o es claramente un nuevo trabajo
                # (la línea tiene un título antes de la fecha), guardar el anterior
                if current_job and (current_job.get('description') or job_title):
                    if current_job.get('title') or current_job.get('company'):
                        experiences.append(current_job)
                        current_job = {}
                
                # Si NO tenemos un trabajo actual O acabamos de crear uno nuevo
                if not current_job:
                    current_job = {
                        'period': date_text,
                        'title': job_title,
                        'company': '',
                        'description': [],
                        'location': location
                    }
                # Si ya tenemos título/empresa pero NO período, añadir el período
                elif not current_job.get('period'):
                    current_job['period'] = date_text
                    if location:
                        current_job['location'] = location
                    if job_title:
                        current_job['title'] = job_title
                else:
                    # Ya tenemos período, actualizar
                    if location:
                        current_job['location'] = location
                    if job_title:
                        current_job['title'] = job_title
                    
            elif not current_job.get('title') and len(line) > 5 and not line.startswith('-'):
                # Primera línea sin fecha suele ser el título/empresa
                current_job['title'] = line.strip()
                    
            elif not current_job.get('company') and len(line) > 5 and not line.startswith('-'):
                # Segunda línea suele ser la empresa o descripción
                # Si empieza con palabras descriptivas, es una descripción
                if line.lower().startswith(('realización', 'desarrollo', 'implementación', 'atención', 'orientación', 'venta', 'gestión')):
                    if 'description' not in current_job:
                        current_job['description'] = []
                    current_job['description'].append(line.strip())
                # Si empieza con minúscula y ya tenemos descripción, probablemente es continuación
                elif line[0].islower() and current_job.get('description'):
                    # Concatenar con la última descripción
                    current_job['description'][-1] += ' ' + line.strip()
                else:
                    current_job['company'] = line.strip()
                    
            elif line.strip().startswith('-'):
                # Es una responsabilidad
                if 'description' not in current_job:
                    current_job['description'] = []
                desc = line.strip().lstrip('-').strip()
                if desc:
                    current_job['description'].append(desc)
                    
            elif len(line.strip()) > 10:
                # Otro texto relevante
                # Si empieza con palabras descriptivas, es descripción
                if line.lower().startswith(('realización', 'desarrollo', 'implementación', 'atención', 'orientación', 'venta', 'gestión')):
                    if 'description' not in current_job:
                        current_job['description'] = []
                    current_job['description'].append(line.strip())
                # Si no tenemos company, esta línea podría ser company
                elif not current_job.get('company'):
                    current_job['company'] = line.strip()
                # Si ya tenemos company, es parte de descripción
                else:
                    if 'description' not in current_job:
                        current_job['description'] = []
                    current_job['description'].append(line.strip())
        
        # No olvidar el último trabajo
        if current_job and (current_job.get('title') or current_job.get('company')):
            experiences.append(current_job)
        
        return experiences
    
    def _parse_education(self, content: List[str]) -> List[Dict]:
        """Parsea sección de educación"""
        education = []
        current_degree = {}
        
        for line in content:
            line = line.strip()
            if len(line) < 5:
                continue
            
            # Detectar fechas de estudio
            date_patterns = [
                r'(\d{4}/\d{4})',
                r'(\d{4}\s*[-–]\s*\d{4})',
                r'(\d{4})',
            ]
            
            has_date = False
            for pattern in date_patterns:
                if re.search(pattern, line):
                    has_date = True
                    break
            
            # Si tiene fecha, es probablemente el período de estudios
            if has_date:
                # Guardar el grado anterior si existe
                if current_degree:
                    education.append(current_degree)
                
                current_degree = {
                    'degree': line,
                    'institution': '',
                    'period': ''
                }
            # Si no tiene fecha y tenemos un grado actual, es probablemente la institución o título
            elif current_degree:
                # Si no tenemos institución, añadir como institución
                if not current_degree.get('institution'):
                    current_degree['institution'] = line
                else:
                    # Si ya tenemos institución, añadir al título
                    if current_degree['degree']:
                        current_degree['degree'] += ' - ' + line
                    else:
                        current_degree['degree'] = line
            else:
                # Si no hay grado actual, crear uno nuevo
                current_degree = {
                    'degree': line,
                    'institution': '',
                    'period': ''
                }
        
        # No olvidar el último grado
        if current_degree:
            education.append(current_degree)
        
        return education
    
    def _parse_skills(self, content: List[str]) -> Dict:
        """Parsea sección de habilidades"""
        technical_skills = []
        other_skills = []
        
        for line in content:
            # Ignorar líneas que parecen ser de formación académica
            if any(word in line.lower() for word in ['universidad', 'centro oficial', 'formación profesional', 'grado', 'licenciada', 'técnico superior', 'postgrado']):
                continue
            
            # Ignorar líneas con fechas (probablemente de formación)
            if re.search(r'\d{4}[/-]\d{4}', line) or re.search(r'\d{4}\s*[-–]', line):
                continue
            
            # Dividir por comas o guiones
            line_skills = re.split(r'[,•\-]', line)
            for skill in line_skills:
                skill = skill.strip()
                if len(skill) > 2 and len(skill) < 50:  # Evitar textos muy largos
                    # Clasificar skills técnicas vs otras
                    if any(tech in skill.lower() for tech in ['python', 'sql', 'excel', 'tableau', 'power', 'data', 'analytics', 'bi', 'etl', 'api']):
                        technical_skills.append(skill)
                    else:
                        other_skills.append(skill)
        
        return {
            'technical': technical_skills,
            'other': other_skills
        }
    
    def _parse_projects(self, content: List[str]) -> List[Dict]:
        """Parsea sección de proyectos"""
        projects = []
        current_project = {}
        
        for line in content:
            if line.isupper() or (line and line[0].isupper() and len(line) < 100):
                if current_project:
                    projects.append(current_project)
                current_project = {
                    'name': line,
                    'description': []
                }
            else:
                if 'description' not in current_project:
                    current_project['description'] = []
                current_project['description'].append(line)
        
        if current_project:
            projects.append(current_project)
        
        return projects
    
    def _extract_personal_info(self, lines: List[str], full_raw_text: str = None) -> Dict:
        """Extrae información personal del inicio del CV"""
        info = {}
        header_text = '\n'.join(lines)
        # Usar el texto completo del CV para buscar teléfono/email por si están en columna derecha
        full_text = full_raw_text if full_raw_text else header_text
        
        # Buscar email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', full_text)
        if email_match:
            info['email'] = email_match.group()
        
        # Buscar teléfono: primero por etiqueta (más fiable), luego por patrón
        labeled_phone = re.search(
            r'(?:tel(?:é|e)fono|tel|phone|m(?:ó|o)vil|mobile|cel(?:ular)?)[:.\s]+([+]?[\d][\d\s.()\-]{7,20})',
            full_text, re.IGNORECASE
        )
        if labeled_phone:
            phone_raw = labeled_phone.group(1).strip()
            # Limpiar caracteres que no sean dígitos, +, espacios o guiones
            info['phone'] = re.sub(r'[^\d+\s()\-]', '', phone_raw).strip()[:20]
        else:
            # Fallback: buscar por patrones de número (incluye formatos españoles)
            phone_patterns = [
                r'\+34[\s.-]?[67]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}',  # Móvil español con +34
                r'\b[67]\d{2}[\s.-]?\d{3}[\s.-]?\d{3}\b',           # Móvil español sin prefijo
                r'\b9\d{2}[\s.-]?\d{3}[\s.-]?\d{3}\b',              # Fijo español
                r'(\+\d{1,3}[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{3,4}',  # Internacional
                r'\d{3}[\s]\d{3}[\s]\d{3}',
                r'\d{9}'
            ]
            for pattern in phone_patterns:
                phone_match = re.search(pattern, full_text)
                if phone_match:
                    info['phone'] = phone_match.group().strip()
                    break
        
        # Buscar nombre (líneas con mayúsculas y formato de nombre)
        for i, line in enumerate(lines[:25]):
            line = line.strip()
            # Nombre suele tener mayúsculas y 2-4 palabras
            if 'name' not in info and 5 < len(line) < 60:
                words = line.split()
                if len(words) >= 2 and any(w[0].isupper() for w in words if w):
                    # Verificar que no sea email, teléfono u otra cosa
                    if '@' not in line and not re.search(r'\d{3}', line):
                        # Si el nombre parece incompleto, buscar en la siguiente línea
                        if len(words) == 2 and i < len(lines) - 1:
                            next_line = lines[i + 1].strip()
                            next_words = next_line.split()
                            # Si la siguiente línea tiene 1-2 palabras con mayúsculas, probablemente es parte del nombre
                            if len(next_words) <= 2 and next_words and next_words[0][0].isupper():
                                if '@' not in next_line and not re.search(r'\d{3}', next_line):
                                    info['name'] = line + ' ' + next_line
                                    break
                        info['name'] = line
                        break
        
        # Buscar ubicación (soporta caracteres especiales del español: ñ, á, é, í, ó, ú)
        location_patterns = [
            r'C\.[^\n]+\d+',  # C. Nombre, número
            r'[A-ZÁ-ÚÀ-Ÿ][A-Za-záéíóúñüàèìòùÁÉÍÓÚÑÜÀÈÌÒÙ]+,\s*[A-ZÁ-ÚÀ-Ÿ][A-Za-záéíóúñüàèìòùÁÉÍÓÚÑÜÀÈÌÒÙ]+',  # Ciudad, País
            r'(?:Madrid|Barcelona|Valencia|Sevilla|España|Espa[ñn]a)[^\n]*'
        ]
        for pattern in location_patterns:
            location_match = re.search(pattern, full_text)
            if location_match:
                info['location'] = location_match.group().strip()
                break
        
        return info