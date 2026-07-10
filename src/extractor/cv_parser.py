from docx import Document
import PyPDF2
import pdfplumber
from pathlib import Path
from typing import Dict, List, Optional
import os
import re
import json
import logging

from config.settings import settings

# Optional fast PDF engine (PyMuPDF) — gracefully disabled if not installed
try:
    import fitz as _fitz  # noqa: F401
    _PYMUPDF_AVAILABLE = True
except ImportError:
    _PYMUPDF_AVAILABLE = False

# PDF processing constants
_PDF_SCANNED_CHAR_THRESHOLD = 100   # avg non-whitespace chars/page; below this → scanned PDF
_PDF_OCR_DPI = 200                   # DPI for rasterising pages before OCR
_PDF_HEADER_FOOTER_MARGIN = 0.08     # fraction of page height stripped from top & bottom

logger = logging.getLogger(__name__)


class CVParser:
    def __init__(self):
        self._ocr_reader = None  # Lazy-loaded on first encounter of a scanned PDF
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
        # Guard de tamaño máximo: protege contra PDFs/DOCX gigantes que
        # podrían agotar RAM al ser parseados por PyMuPDF/pdfplumber/easyocr.
        self._enforce_size_limit(file_path)

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

    @staticmethod
    def _enforce_size_limit(file_path: str) -> None:
        """Rechaza el archivo si supera MAX_CV_SIZE_MB."""
        try:
            size_bytes = os.path.getsize(file_path)
        except OSError as exc:
            raise ValueError(f"No se pudo acceder al archivo: {exc}") from exc

        max_bytes = settings.max_cv_size_mb * 1024 * 1024
        if size_bytes > max_bytes:
            raise ValueError(
                f"CV demasiado grande: {size_bytes / (1024*1024):.1f} MB "
                f"(máximo {settings.max_cv_size_mb} MB). "
                f"Reduce el archivo o ajusta MAX_CV_SIZE_MB en .env."
            )
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Orchestrates PDF text extraction.

        Detects whether the PDF is scanned (image-based) or native (text-based)
        and routes to the appropriate pipeline. The result is cleaned and ready
        for _structure_cv_content().
        """
        if self._is_scanned_pdf(file_path):
            logger.info("[CVParser] PDF escaneado detectado — activando pipeline OCR")
            text = self._extract_ocr_text(file_path)
            if not text.strip():
                logger.warning("[CVParser] OCR sin resultado — usando extracción nativa como respaldo")
                text = self._extract_native_pdf_text(file_path)
        else:
            text = self._extract_native_pdf_text(file_path)
        return self._clean_pdf_text(text)

    # ------------------------------------------------------------------
    # Scanned PDF detection
    # ------------------------------------------------------------------

    def _is_scanned_pdf(self, file_path: str) -> bool:
        """Returns True if the PDF appears to be scanned (image-only pages).

        Samples the first three pages and computes the average number of
        non-whitespace characters.  A very low count (<100) indicates that
        the pages contain images rather than selectable text.
        """
        pages_to_check = 3
        total_chars = 0
        checked = 0
        try:
            if _PYMUPDF_AVAILABLE:
                import fitz
                doc = fitz.open(file_path)
                checked = min(pages_to_check, len(doc))
                for i in range(checked):
                    total_chars += len(re.sub(r'\s', '', doc[i].get_text()))
                doc.close()
            else:
                with pdfplumber.open(file_path) as pdf:
                    checked = min(pages_to_check, len(pdf.pages))
                    for page in pdf.pages[:checked]:
                        total_chars += len(re.sub(r'\s', '', page.extract_text() or ""))
        except Exception as e:
            logger.warning(f"[CVParser] No se pudo verificar si el PDF es escaneado: {e}")
            return False
        avg = total_chars / checked if checked else 0
        return avg < _PDF_SCANNED_CHAR_THRESHOLD

    # ------------------------------------------------------------------
    # Native (text-based) PDF extraction
    # ------------------------------------------------------------------

    def _extract_native_pdf_text(self, file_path: str) -> str:
        """Extracts text from a text-based PDF.

        Resolution order:
          1. PyMuPDF  — fastest, column-aware, strips header/footer by position.
          2. pdfplumber — better for pages that contain tables.
          3. PyPDF2   — last resort for simple single-column PDFs.
        """
        text = ""

        # --- 1. PyMuPDF ---
        if _PYMUPDF_AVAILABLE:
            try:
                import fitz
                doc = fitz.open(file_path)
                page_texts = []
                for page_num, page in enumerate(doc):
                    h = page.rect.height
                    # Page 1 header = candidate name/contact — never a running header,
                    # so don't crop it. On page 2+ crop the repeated-header zone.
                    header_y = h * _PDF_HEADER_FOOTER_MARGIN if page_num > 0 else 0
                    footer_y = h * (1 - _PDF_HEADER_FOOTER_MARGIN)
                    # block[6] == 0 → text block; filter blocks inside header/footer
                    text_blocks = [
                        (b[0], b[1], b[2], b[3], b[4])
                        for b in page.get_text("blocks")
                        if b[6] == 0 and b[1] > header_y and b[3] < footer_y
                    ]
                    page_texts.append(
                        self._blocks_to_ordered_text(text_blocks, page.rect.width)
                    )
                doc.close()
                text = "\n".join(page_texts)
            except Exception as e:
                logger.warning(f"[CVParser] pymupdf falló: {e}")
                text = ""

        # --- 2. pdfplumber — preferred for pages with tables ---
        if not text.strip():
            try:
                with pdfplumber.open(file_path) as pdf:
                    page_texts = []
                    for page in pdf.pages:
                        h = page.height
                        cropped = page.crop((
                            0,
                            h * _PDF_HEADER_FOOTER_MARGIN,
                            page.width,
                            h * (1 - _PDF_HEADER_FOOTER_MARGIN),
                        ))
                        if cropped.find_tables():
                            page_texts.append(self._extract_page_with_tables(cropped))
                        else:
                            page_texts.append(cropped.extract_text(layout=False) or "")
                    text = "\n".join(page_texts)
            except Exception as e:
                logger.warning(f"[CVParser] pdfplumber falló: {e}")

        # --- 3. PyPDF2 — last resort ---
        if not text.strip():
            try:
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    text = "\n".join(
                        (p.extract_text() or "") for p in reader.pages
                    )
            except Exception as e:
                logger.error(f"[CVParser] PyPDF2 falló: {e}")

        return text

    # Words that indicate a line is a job title/subtitle, not a person's name.
    _JOB_TITLE_WORDS = {
        'analyst', 'analista', 'developer', 'desarrollador', 'engineer', 'ingeniero',
        'programmer', 'programador', 'manager', 'director', 'coordinator', 'coordinador',
        'specialist', 'especialista', 'consultant', 'consultor', 'technician', 'técnico',
        'designer', 'diseñador', 'architect', 'arquitecto', 'scientist', 'científico',
    }

    def _blocks_to_ordered_text(self, blocks: list, page_width: float) -> str:
        """Orders pymupdf text blocks for correct reading order.

        Detects two-column layouts by checking whether there are substantial
        groups of blocks anchored on both the left and right halves of the
        page.  When two columns are found each is sorted top-to-bottom
        independently and the left column is emitted first.

        Special case: blocks that appear above the top-most left-column block
        are treated as a full-width header (where the candidate's name and
        job title usually live in Canva/designer templates) and emitted
        before either column so the name appears as the very first text.
        """
        if not blocks:
            return ""
        # Classify by x0 (left edge): blocks starting past 45 % are "right column"
        threshold = page_width * 0.45
        left_col = [b for b in blocks if b[0] < threshold and b[4].strip()]
        right_col = [b for b in blocks if b[0] >= threshold and b[4].strip()]

        if len(left_col) >= 3 and len(right_col) >= 2:
            # Two-column layout — but first extract any header blocks that live
            # above where the left column starts (e.g. name/title in a Canva CV).
            left_min_y = min(b[1] for b in left_col)
            header = [b for b in right_col if b[1] < left_min_y]
            body_r = [b for b in right_col if b[1] >= left_min_y]

            header_text = "\n".join(
                b[4].strip() for b in sorted(header, key=lambda b: b[1])
            )
            left_text = "\n".join(
                b[4].strip() for b in sorted(left_col, key=lambda b: b[1])
            )
            right_text = "\n".join(
                b[4].strip() for b in sorted(body_r, key=lambda b: b[1])
            )
            return "\n".join(p for p in [header_text, left_text, right_text] if p)
        # Single column: top-to-bottom, left-to-right
        return "\n".join(
            b[4].strip()
            for b in sorted(blocks, key=lambda b: (b[1], b[0]))
            if b[4].strip()
        )

    def _extract_page_with_tables(self, page) -> str:
        """Extracts text from a pdfplumber page that contains tables.

        Tables are rendered as pipe-delimited rows so the downstream LLM
        can interpret the structure.  The plain page text is emitted first
        to preserve any surrounding prose.
        """
        parts = [page.extract_text(layout=False) or ""]
        for table in page.find_tables():
            data = table.extract()
            if not data:
                continue
            rows = []
            for row in data:
                cells = [str(cell).strip() if cell is not None else "" for cell in row]
                rows.append(" | ".join(cells))
            parts.append("\n".join(rows))
        return "\n".join(p for p in parts if p.strip())

    # ------------------------------------------------------------------
    # OCR pipeline (scanned PDFs)
    # ------------------------------------------------------------------

    def _get_ocr_reader(self):
        """Lazy-loads EasyOCR reader (cached after first call).

        Returns None if easyocr is not installed so that callers can
        gracefully skip OCR rather than crashing.
        """
        if self._ocr_reader is None:
            try:
                import easyocr
                logger.info("[CVParser] Cargando EasyOCR (primera vez, puede tardar unos segundos)…")
                self._ocr_reader = easyocr.Reader(['es', 'en'], verbose=False)
            except ImportError:
                logger.warning(
                    "[CVParser] easyocr no instalado — OCR no disponible. "
                    "Instala con: pip install easyocr pdf2image"
                )
        return self._ocr_reader

    def _extract_ocr_text(self, file_path: str) -> str:
        """Extracts text from a scanned PDF using pdf2image + EasyOCR.

        Each page is rasterised at _PDF_OCR_DPI and passed to EasyOCR.
        Results are ordered by EasyOCR's paragraph grouping which already
        handles reading order.
        """
        text_parts: List[str] = []
        try:
            from pdf2image import convert_from_path
            import numpy as np

            reader = self._get_ocr_reader()
            if reader is None:
                return ""

            logger.info("[CVParser] Rasterizando páginas para OCR…")
            images = convert_from_path(file_path, dpi=_PDF_OCR_DPI)
            for idx, img in enumerate(images):
                results = reader.readtext(np.array(img), detail=0, paragraph=True)
                text_parts.append("\n".join(str(r) for r in results))
                logger.debug(f"[CVParser] OCR página {idx + 1}/{len(images)} completada")
        except ImportError as e:
            logger.warning(f"[CVParser] Dependencias OCR no instaladas ({e})")
        except Exception as e:
            logger.error(f"[CVParser] Error en OCR: {e}")
        return "\n".join(text_parts)

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
    
    @staticmethod
    def _extract_linkedin(text: str) -> Optional[str]:
        """Detecta URL completa o handle de LinkedIn en el texto."""
        # URL completa: https://(www.|es.|...)linkedin.com/in/<slug>
        url_match = re.search(
            r'(?:https?://)?(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|pub)/[A-Za-z0-9\-_%/.]+',
            text, re.IGNORECASE,
        )
        if url_match:
            url = url_match.group(0).rstrip('/.,;:)')
            if not url.lower().startswith('http'):
                url = 'https://' + url
            return url
        # Etiqueta "LinkedIn: <handle>" → handle libre (no URL)
        label_match = re.search(
            r'LinkedIn[:\s]+([A-Za-zÁ-Úá-ú0-9][\w\sÁ-Úá-úñÑ\-]{2,60})',
            text,
        )
        if label_match:
            handle = label_match.group(1).strip().rstrip('.,;:)')
            # Evitar capturar la siguiente sección si la línea no termina antes
            handle = re.split(r'\s{2,}|[\n\r]', handle)[0].strip()
            if handle and len(handle) >= 3:
                return handle
        return None

    @staticmethod
    def _extract_github(text: str) -> Optional[str]:
        """Detecta URL completa o handle de GitHub en el texto."""
        url_match = re.search(
            r'(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9\-_.]+',
            text, re.IGNORECASE,
        )
        if url_match:
            url = url_match.group(0).rstrip('/.,;:)')
            if not url.lower().startswith('http'):
                url = 'https://' + url
            return url
        label_match = re.search(
            r'GitHub[:\s]+([A-Za-z0-9\-_./]{2,60})',
            text,
        )
        if label_match:
            return label_match.group(1).strip().rstrip('.,;:)')
        return None

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

        # Buscar LinkedIn (URL completa o handle tras "LinkedIn:")
        linkedin = self._extract_linkedin(full_text)
        if linkedin:
            info['linkedin'] = linkedin

        # Buscar GitHub (URL completa o handle tras "GitHub:")
        github = self._extract_github(full_text)
        if github:
            info['github'] = github
        
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
        
        # Buscar nombre (líneas con mayúsculas y formato de nombre).
        # We search the first 40 lines to handle two-column PDFs where the
        # name block may be preceded by a header/subtitle extracted first.
        for i, line in enumerate(lines[:40]):
            line = line.strip()
            # Nombre suele tener mayúsculas y 2-4 palabras
            if 'name' not in info and 5 < len(line) < 60:
                words = line.split()
                if len(words) >= 2 and any(w[0].isupper() for w in words if w):
                    # Verificar que no sea email, teléfono u otra cosa
                    if '@' not in line and not re.search(r'\d{3}', line):
                        # Skip lines that look like job titles or section headers
                        lower_words = {w.lower() for w in words}
                        if lower_words & CVParser._JOB_TITLE_WORDS:
                            continue
                        # Skip common CV section headers (all-caps multi-word lines
                        # that contain typical section keywords)
                        section_kw = {
                            'perfil', 'profesional', 'experiencia', 'habilidades',
                            'educacion', 'educación', 'idiomas', 'contacto',
                            'skills', 'experience', 'education', 'profile',
                            'resumen', 'logros', 'proyectos', 'certificaciones',
                        }
                        if lower_words & section_kw:
                            continue
                        # Si el nombre parece incompleto, buscar en la siguiente línea
                        if len(words) == 2 and i < len(lines) - 1:
                            next_line = lines[i + 1].strip()
                            next_words = next_line.split()
                            # Si la siguiente línea tiene 1-2 palabras con mayúsculas,
                            # probablemente es parte del nombre
                            if (len(next_words) <= 2 and next_words
                                    and next_words[0][0].isupper()
                                    and '@' not in next_line
                                    and not re.search(r'\d{3}', next_line)
                                    and not {w.lower() for w in next_words} & section_kw):
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