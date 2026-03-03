import requests
from bs4 import BeautifulSoup
from typing import Optional
import re
import logging

# Importar scraper de LinkedIn
try:
    from .linkedin_job_scraper import scrape_linkedin_job, is_linkedin_job_url
    LINKEDIN_AVAILABLE = True
except ImportError:
    # Fallback si no está disponible
    LINKEDIN_AVAILABLE = False
    def scrape_linkedin_job(url: str) -> str:
        raise ValueError("LinkedIn scraper no disponible")
    
    def is_linkedin_job_url(url: str) -> bool:
        return False

logger = logging.getLogger(__name__)

class JobScraper:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def scrape_any_job_offer(self, url: str) -> Optional[str]:
        """Detecta el portal y extrae la descripción de la oferta usando selectores específicos."""
        try:
            # ✅ NUEVA FUNCIONALIDAD: Detectar y procesar URLs de LinkedIn
            if LINKEDIN_AVAILABLE and is_linkedin_job_url(url):
                logger.info("Detectada URL de LinkedIn, usando scraper específico")
                try:
                    return scrape_linkedin_job(url)
                except Exception as e:
                    logger.warning(f"Error en scraper de LinkedIn: {e}. Intentando scraping genérico.")
                    # Continuar con scraping genérico como fallback
            
            # Continuar con scraping genérico para otros portales
            domain = self._get_domain(url)
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            if 'indeed' in domain:
                selectors = [
                    '#jobDescriptionText',
                    '.jobsearch-jobDescriptionText',
                    '.jobsearch-JobComponent-description',
                ]
            elif 'infojobs' in domain:
                selectors = [
                    '.description',
                    '.job-description',
                    '.content',
                ]
            elif 'jobatus' in domain:
                selectors = [
                    '.job-offer-description',
                    '.oferta-descripcion',
                    '.description',
                ]
            elif 'tecnoempleo' in domain:
                selectors = [
                    '.description',
                    '.job-description',
                    '.oferta-desc',
                ]
            else:
                selectors = [
                    '.job-description',
                    '.description',
                    'main',
                    'article',
                    'body',
                ]

            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    return self._clean_text(element.get_text(strip=True))

            # Fallback: todo el body
            body = soup.find('body')
            if body:
                return self._clean_text(body.get_text(strip=True))

            return None
        except Exception as e:
            logger.error(f"Error en scrape_any_job_offer: {e}")
            return None

    def _get_domain(self, url: str) -> str:
        """Extrae el dominio de una URL"""
        match = re.search(r'https?://([^/]+)/', url)
        if match:
            return match.group(1).lower()
        return url.lower()

    def scrape_job_offer(self, url: str) -> Optional[str]:
        """Intenta scraping con múltiples estrategias"""
        try:
            # ✅ NUEVA FUNCIONALIDAD: Verificar LinkedIn primero
            if LINKEDIN_AVAILABLE and is_linkedin_job_url(url):
                logger.info("Procesando URL de LinkedIn")
                try:
                    return scrape_linkedin_job(url)
                except Exception as e:
                    logger.warning(f"Error en LinkedIn scraper: {e}. Usando método genérico.")
            
            # Estrategia 1: Requests básico
            text = self._scrape_with_requests(url)
            if text and len(text) > 100:
                return self._clean_text(text)
            
            return None
                
        except Exception as e:
            logger.error(f"Error en scraping: {e}")
            return None
    
    def _scrape_with_requests(self, url: str) -> Optional[str]:
        """Scraping básico con requests"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remover scripts y estilos
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # Buscar contenido principal
            main_content = self._extract_main_content(soup)
            return main_content
            
        except Exception as e:
            logger.error(f"Error con requests: {e}")
            return None
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extrae el contenido principal de la oferta"""
        # Selectores comunes para ofertas de trabajo
        selectors = [
            '.job-description',
            '.job-content',
            '[data-testid="job-description"]',
            '.description',
            'main',
            'article',
            '.content',
            # Selectores específicos para LinkedIn (fallback)
            '.jobs-description__content',
            '.job-details-jobs-unified-top-card__job-details',
            '.jobs-unified-description__content',
            '[data-job-description]',
            '.job-description-text'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        
        # Fallback: todo el body
        body = soup.find('body')
        if body:
            return body.get_text(strip=True)
        
        return soup.get_text(strip=True)
    
    def _clean_text(self, text: str) -> str:
        """Limpia el texto extraído"""
        # Remover espacios excesivos
        text = re.sub(r'\s+', ' ', text)
        
        # Remover caracteres especiales problemáticos
        text = re.sub(r'[^\w\s.,;:!?()-]', '', text)
        
        # Limitar longitud
        if len(text) > 10000:
            text = text[:10000] + "..."
        
        return text.strip()

    def scrape_linkedin_alternative(
        self, job_title: str, company: str = "", location: str = ""
    ) -> Optional[str]:
        """Busca ofertas similares en sitios gratuitos"""
        search_query = f"{job_title} {company}".strip()
        query_encoded = search_query.replace(' ', '+')
        loc_encoded = location.replace(' ', '+')
        base_url = "https://es.indeed.com/jobs"
        indeed_url = f"{base_url}?q={query_encoded}&l={loc_encoded}"

        logger.info(f"Buscando en Indeed: {indeed_url}")

        text = self._scrape_with_requests(indeed_url)
        if text and len(text) > 200:
            return self._clean_text(text)

        return None