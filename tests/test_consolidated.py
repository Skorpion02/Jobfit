#!/usr/bin/env python3
"""
Test suite consolidado para JobFit Agent
"""

import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import pytest
from unittest.mock import Mock, patch

from src.extractor.cv_parser import CVParser
from src.extractor.job_parser import JobParser  
from src.matcher.semantic_matcher import SemanticMatcher
from src.generator.cv_adapter import CVAdapter
from src.auditor.realism_scorer import RealismScorer


class TestCVParser:
    def test_cv_parser_initialization(self):
        parser = CVParser()
        assert parser.sections is not None
        assert 'experience' in parser.sections
        assert 'skills' in parser.sections
    
    def test_cv_structure_has_required_fields(self):
        parser = CVParser()
        # Test con texto simple
        result = parser._structure_cv_content("Test CV Content")
        
        # Verificar que todos los campos existen y son del tipo correcto
        assert 'personal_info' in result
        assert 'experience' in result
        assert 'education' in result  
        assert 'skills' in result
        assert 'projects' in result
        assert 'raw_text' in result
        
        # Verificar tipos
        assert isinstance(result['experience'], list)
        assert isinstance(result['education'], list)
        assert isinstance(result['projects'], list)
        assert isinstance(result['skills'], dict)
        assert isinstance(result['raw_text'], str)


class TestSemanticMatcher:
    def test_matcher_initialization(self):
        matcher = SemanticMatcher()
        assert matcher.model is not None
        assert matcher.threshold > 0
    
    @patch('src.matcher.semantic_matcher.SemanticMatcher._calculate_similarities')
    def test_match_requirements_handles_empty_inputs(self, mock_calc):
        matcher = SemanticMatcher()
        mock_calc.return_value = []
        
        # Test casos edge
        result = matcher.match_requirements_to_cv([], "")
        assert result is not None
        
        result = matcher.match_requirements_to_cv(None, "test cv")
        assert result is not None


class TestCVAdapter:
    def test_cv_adapter_initialization(self):
        adapter = CVAdapter()
        assert adapter is not None
    
    def test_adapt_cv_handles_none_fields(self):
        adapter = CVAdapter()
        
        # CV con campos None
        cv_data = {
            'experience': None,
            'education': None,
            'skills': None,
            'projects': None,
            'raw_text': 'Test content'
        }
        
        job_requirements = ['Python', 'Data Analysis']
        
        # No debería fallar con campos None
        try:
            result = adapter.adapt_cv(cv_data, job_requirements, {})
            assert result is not None
        except TypeError as e:
            pytest.fail(f"adapt_cv failed with None fields: {e}")


class TestRealismScorer:
    def test_scorer_initialization(self):
        scorer = RealismScorer()
        assert scorer is not None
    
    def test_calculate_realism_score_basic(self):
        scorer = RealismScorer()
        
        job_data = {
            'title': 'Data Analyst',
            'must_have': ['Python', 'SQL'],
            'nice_to_have': ['Tableau'],
            'years_experience': '2-3',
            'description': 'Test job description'
        }
        
        result = scorer.calculate_realism_score(job_data)
        
        assert 'realism_score' in result
        assert isinstance(result['realism_score'], (int, float))
        assert 0 <= result['realism_score'] <= 100


if __name__ == '__main__':
    # Ejecutar tests
    pytest.main([__file__, '-v'])
