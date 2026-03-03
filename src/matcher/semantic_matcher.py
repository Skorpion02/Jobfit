from sentence_transformers import SentenceTransformer
import numpy as np
import logging
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple
import re

logger = logging.getLogger(__name__)

class SemanticMatcher:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
        self.similarity_threshold = 0.10  # Más permisivo para detectar más matches
        # Backwards-compat alias expected by tests / callers
        self.threshold = float(self.similarity_threshold)
    
    def match_requirements_to_cv(self, requirements: List[str], cv_text: str) -> Dict:
        """
        Realiza matching semántico entre requisitos del trabajo y el CV
        """
        if not requirements:
            logger.warning("No hay requisitos para comparar")
            return {
                'overall_match': 0.0,
                'matches': [],
                'missing_requirements': [],
                'coverage_percentage': 0.0
            }
        
        if not cv_text or len(cv_text.strip()) < 50:
            logger.warning(f"CV text muy corto: {len(cv_text) if cv_text else 0} caracteres")
            return {
                'overall_match': 0.0,
                'matches': [],
                'missing_requirements': requirements,
                'coverage_percentage': 0.0
            }
        
        logger.info(f"Analizando {len(requirements)} requisitos contra CV de {len(cv_text)} caracteres")
        logger.info(f"Threshold configurado: {self.similarity_threshold}")
        
        # Log de los primeros requisitos
        logger.debug(f"Requisitos: {requirements[:5]}")
        logger.debug(f"CV preview: {cv_text[:200]}...")
        
        try:
            # Delegar cálculo de similitudes a un método separado para permitir
            # mocking/testing y reutilización.
            similarities = self._calculate_similarities(requirements, cv_text)
            # Asegurarnos de que tenemos un ndarray unidimensional
            import numpy as _np
            similarities = _np.asarray(similarities).flatten()
            logger.debug(f"Similarities shape: {similarities.shape}")
            logger.debug(f"Similarities: {similarities}")
            
            matches = []
            missing_requirements = []
            
            for i, (req, similarity) in enumerate(zip(requirements, similarities)):
                match_info = {
                    'requirement': req,
                    'similarity': float(similarity),
                    'match': similarity > self.similarity_threshold
                }
                
                if similarity > self.similarity_threshold:
                    matches.append(match_info)
                    logger.info(f"[+] Match encontrado: '{req}' - {similarity:.3f}")
                else:
                    missing_requirements.append(req)
                    logger.info(f"[-] No match: '{req}' - {similarity:.3f}")
            
            # Calcular métricas
            coverage = len(matches) / len(requirements) * 100 if requirements else 0
            overall_match = sum(similarities) / len(similarities) if similarities.size > 0 else 0
            
            result = {
                'overall_match': float(overall_match),
                'matches': matches,
                'missing_requirements': missing_requirements,
                'coverage_percentage': float(coverage),
                'total_requirements': len(requirements),
                'matched_requirements': len(matches)
            }
            
            logger.info(f"Resultado final: {coverage:.1f}% coverage, {len(matches)} matches de {len(requirements)} requisitos")
            
            return result
            
        except Exception as e:
            logger.error(f"Error en matching semántico: {str(e)}", exc_info=True)
            return {
                'overall_match': 0.0,
                'matches': [],
                'missing_requirements': requirements,
                'coverage_percentage': 0.0,
                'error': str(e)
            }

    def _calculate_similarities(self, requirements: List[str], cv_text: str):
        """
        Calcula las similitudes entre cada requirement y el CV. Se expone
        como método separado para facilitar tests (mock) y posible
        reimplementación.
        Retorna una lista o ndarray de floats.
        """
        # Caso sencillo: si no hay requisitos, devolver array vacío
        if not requirements:
            return []

        # Generar embeddings
        req_embeddings = self.model.encode(requirements)
        cv_embedding = self.model.encode([cv_text])

        # Normalizar shapes
        import numpy as _np
        if hasattr(req_embeddings, 'ndim') and req_embeddings.ndim == 1:
            req_embeddings = req_embeddings.reshape(1, -1)
        if hasattr(cv_embedding, 'ndim') and cv_embedding.ndim == 1:
            cv_embedding = cv_embedding.reshape(1, -1)

        # Calcular similitud coseno
        sims = cosine_similarity(req_embeddings, cv_embedding)
        return sims.flatten()
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """Divide texto en oraciones"""
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if len(s.strip()) > 10]
    
    def _find_exact_match(self, requirement: str, cv_parts: List[str]) -> Dict:
        """Busca coincidencias exactas usando keywords"""
        req_keywords = self._extract_keywords(requirement.lower())
        
        for i, cv_part in enumerate(cv_parts):
            cv_keywords = self._extract_keywords(cv_part.lower())
            
            # Calcular overlap de keywords
            overlap = len(req_keywords.intersection(cv_keywords))
            if overlap >= min(2, len(req_keywords) * 0.5):
                return {
                    "evidence": cv_part,
                    "section": f"section_{i}"  # Simplificado
                }
        
        return None
    
    def _extract_keywords(self, text: str) -> set:
        """Extrae keywords relevantes"""
        # Lista de tecnologías y skills comunes
        tech_keywords = {
            'python', 'java', 'javascript', 'react', 'angular', 'vue',
            'node', 'express', 'django', 'flask', 'spring', 'docker',
            'kubernetes', 'aws', 'azure', 'gcp', 'sql', 'mongodb',
            'postgresql', 'mysql', 'git', 'github', 'jenkins', 'ci/cd'
        }
        
        words = re.findall(r'\b\w+\b', text.lower())
        keywords = set()
        
        for word in words:
            if len(word) > 2 and (word in tech_keywords or len(word) > 4):
                keywords.add(word)
        
        return keywords