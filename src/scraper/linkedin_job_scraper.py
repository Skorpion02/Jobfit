#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LinkedIn Job Scraper Mejorado
============================

Script mejorado para extraer información de ofertas de LinkedIn
con múltiples endpoints y mejor parsing.

ADVERTENCIA: Usar bajo tu propia responsabilidad. Revisa los términos de 
servicio de LinkedIn y las leyes locales antes de usar este script.

Autor: Generado para JobFit Agent
Fecha: 2025
Python: 3.8+
"""

import re
import time
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup, Tag

# Configurar logging
logger = logging.getLogger(__name__)

# Constantes de configuración
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
ACCEPT_LANGUAGE = "es-ES,es;q=0.9,en;q=0.8"
REQUEST_TIMEOUT = 30
RATE_LIMIT_DELAY = 3  # segundos entre peticiones

# Headers para simular navegador real
DEFAULT_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': ('text/html,application/xhtml+xml,application/xml;q=0.9,'
               'image/webp,*/*;q=0.8'),
    'Accept-Language': ACCEPT_LANGUAGE,
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Cache-Control': 'max-age=0'
}


def extract_job_id(url: str) -> Optional[str]:
    """
    Extrae el job ID de una URL de LinkedIn.
    
    Args:
        url: URL de LinkedIn o job ID directo
        
    Returns:
        Job ID extraído o None si no se encuentra
    """
    # Si parece ser solo un número, asumir que es el job ID
    if url.isdigit():
        return url
    
    # Buscar patrón /jobs/view/{jobId} en la URL
    job_id_match = re.search(r'/jobs/view/(\d+)', url)
    if job_id_match:
        return job_id_match.group(1)
    
    # Buscar en parámetros de query (?jobId=... o ?currentJobId=...)
    try:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        # Intentar diferentes parámetros
        for param in ['jobId', 'currentJobId', 'job_id']:
            if param in query_params:
                return query_params[param][0]
    except Exception:
        pass
    
    return None


def fetch_about_html(job_id: str) -> Optional[str]:
    """
    Obtiene el HTML de la oferta usando múltiples endpoints de LinkedIn.
    
    Args:
        job_id: ID numérico de la oferta de LinkedIn
        
    Returns:
        HTML de la página o None si hay error
    """
    # Intentar múltiples endpoints/enfoques
    endpoints = [
        # Endpoint público principal
        f"https://www.linkedin.com/jobs/view/{job_id}/",
        # Endpoint jobs-guest API
        f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}/",
        # Endpoint alternativo
        f"https://es.linkedin.com/jobs/view/{job_id}/"
    ]
    
    session = requests.Session()
    
    # Headers mejorados para simular mejor un navegador
    enhanced_headers = DEFAULT_HEADERS.copy()
    enhanced_headers.update({
        'Referer': 'https://www.google.com/',
        'Origin': 'https://www.linkedin.com',
        'DNT': '1',
        'Pragma': 'no-cache',
    })
    
    for i, endpoint_url in enumerate(endpoints):
        logger.info(f"Intentando endpoint {i+1}/3: {endpoint_url}")
        
        try:
            # Rate limiting más conservador
            time.sleep(RATE_LIMIT_DELAY + i)  # Aumentar delay en cada intento
            
            response = session.get(
                endpoint_url,
                headers=enhanced_headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True
            )
            
            # Verificar código de respuesta
            if response.status_code == 403:
                logger.warning(f"Error 403 en endpoint {i+1}: Acceso denegado")
                continue
            elif response.status_code == 429:
                logger.warning(f"Error 429 en endpoint {i+1}: Rate limiting")
                time.sleep(10)  # Esperar más tiempo antes del siguiente intento
                continue
            elif response.status_code == 404:
                logger.warning(f"Error 404 en endpoint {i+1}: "
                              f"Oferta no encontrada")
                continue
            elif response.status_code != 200:
                logger.warning(f"Error HTTP {response.status_code} "
                              f"en endpoint {i+1}")
                continue
            
            # Verificar que tenemos contenido HTML válido
            if not response.text or len(response.text.strip()) < 500:
                logger.warning(f"Respuesta muy corta en endpoint {i+1}: "
                              f"{len(response.text)} chars")
                continue
                
            # Verificar que no es una página de login/error
            text_lower = response.text.lower()
            if any(indicator in text_lower for indicator in [
                'sign in to linkedin', 'sign in with apple', 'cookie policy',
                'agree join linkedin', 'new to linkedin', 'privacy policy'
            ]):
                logger.warning(f"Endpoint {i+1} devolvió página "
                              f"de login/cookies")
                continue
            
            logger.info(f"HTML obtenido exitosamente: "
                       f"{len(response.text)} caracteres")
            return response.text
            
        except requests.RequestException as e:
            logger.warning(f"Error de conexión en endpoint {i+1}: {str(e)}")
            continue
    
    # Si llegamos aquí, ningún endpoint funcionó
    raise ValueError("No se pudo obtener el contenido de LinkedIn "
                     "desde ningún endpoint")


def _html_to_text_preserving_lists(element: Tag) -> str:
    """
    Convierte HTML a texto preservando la estructura de listas.
    
    Args:
        element: Elemento BeautifulSoup a convertir
        
    Returns:
        Texto formateado con viñetas para listas
    """
    result = []
    
    for child in element.children:
        if hasattr(child, 'name'):
            if child.name in ['ul', 'ol']:
                # Procesar listas
                for li in child.find_all('li'):
                    li_text = li.get_text(strip=True)
                    if li_text:
                        result.append(f"• {li_text}")
            elif child.name in ['p', 'div', 'section']:
                # Procesar párrafos y secciones
                text = child.get_text(strip=True)
                if text:
                    result.append(text)
            elif child.name in ['br']:
                result.append("")
            else:
                # Procesar otros elementos recursivamente
                text = _html_to_text_preserving_lists(child)
                if text:
                    result.append(text)
        else:
            # Texto directo
            text = str(child).strip()
            if text:
                result.append(text)
    
    return '\n'.join(result)


def parse_about_text(html: str) -> Dict[str, Any]:
    """
    Extrae la información de la oferta desde el HTML con múltiples selectores.
    
    Args:
        html: HTML de la página de LinkedIn
        
    Returns:
        Diccionario con información extraída
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    result = {
        'title': None,
        'company': None,
        'location': None,
        'about': None,
        'description': None,
        'criteria': {}
    }
    
    try:
        # === EXTRAER TÍTULO ===
        title_selectors = [
            'h1.top-card-layout__title',
            '.job-details-jobs-unified-top-card__job-title h1',
            'h1[data-test-id="job-title"]',
            '.jobs-unified-top-card__job-title h1',
            'h1.jobs-unified-top-card__job-title',
            '.job-details__job-title h1',
            'h1',  # Fallback genérico
        ]
        
        for selector in title_selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.get_text(strip=True):
                result['title'] = title_elem.get_text(strip=True)
                logger.info(f"Título encontrado: {result['title']}")
                break
        
        # === EXTRAER EMPRESA ===
        company_selectors = [
            '.job-details-jobs-unified-top-card__company-name a',
            '.jobs-unified-top-card__company-name a',
            'a[data-tracking-control-name="public_jobs_topcard-org-name"]',
            '.top-card-layout__card .top-card-layout__entity-info a',
            'a[href*="/company/"]'
        ]
        
        for selector in company_selectors:
            company_elem = soup.select_one(selector)
            if company_elem and company_elem.get_text(strip=True):
                result['company'] = company_elem.get_text(strip=True)
                logger.info(f"Empresa encontrada: {result['company']}")
                break
        
        # === EXTRAER UBICACIÓN ===
        location_selectors = [
            '.job-details-jobs-unified-top-card__primary-description-without-tagline',  # noqa
            '.jobs-unified-top-card__bullet',
            '.job-details-jobs-unified-top-card__primary-description',
            'span.jobs-unified-top-card__bullet',
            '.top-card-layout__second-subline',
        ]
        
        for selector in location_selectors:
            location_elem = soup.select_one(selector)
            if location_elem and location_elem.get_text(strip=True):
                location_text = location_elem.get_text(strip=True)
                # Filtrar texto que no sea ubicación
                if not any(word in location_text.lower() for word in 
                          ['remote', 'híbrido', 'presencial', 'días', 'hace']):
                    result['location'] = location_text
                    logger.info(f"Ubicación encontrada: {result['location']}")
                    break
        
        # === EXTRAER DESCRIPCIÓN/ABOUT ===
        description_selectors = [
            '.jobs-description-content__text',
            '.job-details-jobs-unified-top-card__job-description',
            '.jobs-unified-top-card__job-description',
            '.jobs-description__content',
            '.job-description',
            'div[data-test-id="job-description"]',
            '.description-module',
        ]
        
        for selector in description_selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                # Usar función para preservar formato de listas
                description = _html_to_text_preserving_lists(desc_elem)
                if description and len(description.strip()) > 50:
                    result['description'] = description.strip()
                    result['about'] = description.strip()
                    logger.info(f"Descripción encontrada: "
                               f"{len(description)} chars")
                    break
        
        # === EXTRAER CRITERIOS ADICIONALES ===
        # Buscar secciones de criterios como experiencia, educación, etc.
        criteria_selectors = [
            '.job-criteria__text',
            '.jobs-unified-top-card__job-criteria',
            '.job-details-preferences-and-skills'
        ]
        
        for selector in criteria_selectors:
            criteria_elems = soup.select(selector)
            for elem in criteria_elems:
                text = elem.get_text(strip=True)
                if 'years' in text.lower() or 'año' in text.lower():
                    result['criteria']['experience'] = text
                elif 'degree' in text.lower() or 'university' in text.lower():
                    result['criteria']['education'] = text
        
        # Si no encontramos descripción, intentar extraer todo el texto útil
        if not result['description']:
            # Eliminar elementos de navegación y cookie notices
            for element in soup.find_all(['nav', 'footer', 'header']):
                element.decompose()
            
            # Buscar el contenedor principal de contenido
            main_content = soup.find('main') or soup.find('body')
            if main_content:
                text_content = main_content.get_text(strip=True)
                # Filtrar contenido de login/cookies
                if len(text_content) > 200 and not any(
                    phrase in text_content.lower() for phrase in [
                        'sign in to linkedin', 'cookie policy', 
                        'privacy policy', 'user agreement'
                    ]
                ):
                    result['description'] = text_content
                    result['about'] = text_content
                    logger.info("Descripción extraída del contenido general")
        
        return result
        
    except Exception as e:
        logger.error(f"Error parseando HTML de LinkedIn: {e}")
        return result


def scrape_linkedin_job(url: str) -> str:
    """
    Función principal para scraping de LinkedIn integrada con JobFit.
    
    Args:
        url: URL de LinkedIn a scrapear
        
    Returns:
        Texto extraído de la oferta
        
    Raises:
        ValueError: Si no se puede extraer información válida
    """
    try:
        # Extraer Job ID
        job_id = extract_job_id(url)
        if not job_id:
            raise ValueError(f"No se pudo extraer Job ID de la URL: {url}")
        
        logger.info(f"Job ID identificado: {job_id}")
        
        # Obtener HTML
        html = fetch_about_html(job_id)
        if not html:
            raise ValueError("No se pudo obtener HTML de LinkedIn")
        
        # Parsear información
        parsed_data = parse_about_text(html)
        
        # Construir texto de salida
        output_parts = []
        
        if parsed_data.get('title'):
            output_parts.append(f"Título: {parsed_data['title']}")
        
        if parsed_data.get('company'):
            output_parts.append(f"Empresa: {parsed_data['company']}")
        
        if parsed_data.get('location'):
            output_parts.append(f"Ubicación: {parsed_data['location']}")
        
        if parsed_data.get('description'):
            output_parts.append(f"Descripción:\n{parsed_data['description']}")
        elif parsed_data.get('about'):
            output_parts.append(f"Descripción:\n{parsed_data['about']}")
        
        # Agregar criterios si los hay
        if parsed_data.get('criteria'):
            for key, value in parsed_data['criteria'].items():
                output_parts.append(f"{key.title()}: {value}")
        
        result = "\n\n".join(output_parts)
        
        if not result or len(result.strip()) < 50:
            raise ValueError("No se pudo extraer información válida de LinkedIn")
        
        logger.info(f"Scraping exitoso: {len(result)} caracteres extraídos")
        return result
        
    except Exception as e:
        error_msg = f"Error en LinkedIn scraper: {str(e)}"
        logger.error(error_msg)
        raise ValueError(error_msg)


def is_linkedin_job_url(url: str) -> bool:
    """
    Detecta si una URL es de LinkedIn jobs.
    
    Args:
        url: URL a verificar
        
    Returns:
        True si es una URL de LinkedIn jobs, False en caso contrario
    """
    if not url:
        return False
    
    # Patrones de URLs de LinkedIn jobs
    linkedin_patterns = [
        r'linkedin\.com/jobs/view/\d+',
        r'linkedin\.com/jobs-guest/jobs/api/jobPosting/\d+',
        r'[a-z]{2}\.linkedin\.com/jobs/view/\d+',
        r'linkedin\.com/jobs/collections/.*currentJobId=\d+',  # Nuevo formato
        r'linkedin\.com.*[?&]currentJobId=\d+',  # Cualquier URL con currentJobId
        r'linkedin\.com.*[?&]jobId=\d+',  # Cualquier URL con jobId
    ]
    
    return any(re.search(pattern, url, re.IGNORECASE) 
               for pattern in linkedin_patterns)


# Función de test para debugging
def test_scraper(job_url: str):
    """
    Función de test para debugging del scraper.
    
    Args:
        job_url: URL de LinkedIn para probar
    """
    print(f"Testing LinkedIn scraper with URL: {job_url}")
    
    try:
        result = scrape_linkedin_job(job_url)
        print(f"Success! Extracted {len(result)} characters:")
        print("-" * 50)
        print(result[:500] + "..." if len(result) > 500 else result)
        print("-" * 50)
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Test con URL de ejemplo
    test_url = "https://es.linkedin.com/jobs/view/4007853046"
    test_scraper(test_url)