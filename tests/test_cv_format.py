#!/usr/bin/env python3
"""
Test del nuevo formato profesional de CV
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from generator.cv_adapter import CVAdapter
import json

def test_professional_cv_format():
    """Prueba el nuevo formato profesional del CV"""
    
    # CV de ejemplo
    sample_cv = {
        'personal_info': {
            'name': 'Roberto de Gouveia',
            'email': 'roberto.gouveia@email.com',
            'phone': '+34 123 456 789',
            'location': 'Madrid, España'
        },
        'summary': 'Profesional con 1 años de experiencia en análisis de datos, especializado en Python, SQL, y herramientas de Business Intelligence como Power BI y Tableau.',
        'experience': [
            {
                'title': 'Data Scientist Senior',
                'company': 'Tech Solutions Company',
                'period': '2020 - Presente',
                'description': [
                    'Implementación de pipelines de datos con Python, pandas, numpy para procesamiento en gran escala',
                    'Gestión y consulta de bases de datos SQL, MySQL y SQL Server para extracción de insights',
                    'Control de versiones y colaboración en equipo usando Git, GitHub y metodologías ágiles',
                    'Capacidad de desenvolverte de forma autónoma en proyectos de ciencia de datos complejos'
                ]
            }
        ],
        'skills': {
            'technical': [
                'Python (avanzado)', 'SQL (avanzado)', 'MySQL', 'SQL Server', 'PostgreSQL', 'JavaScript',
                'Java (intermedio)', 'SQL Server', 'MySQL', 'PostgreSQL', 'procedimientos almacenados',
                'funciones SQL', 'pandas', 'numpy', 'matplotlib', 'seaborn', 'scikit-learn', 'TensorFlow',
                'Keras', 'Power BI', 'Tableau', 'Excel', 'Git', 'GitHub', 'AWS', 'Docker'
            ],
            'other': [
                'Trabajo autónomo', 'Metodologías ágiles', 'Análisis de datos', 'Visualización de datos'
            ]
        },
        'education': [
            {
                'degree': 'Máster en Ciencia de Datos',
                'institution': 'Universidad Técnica',
                'year': '2018'
            },
            {
                'degree': 'Ingeniería en Sistemas',
                'institution': 'Universidad Politécnica',
                'year': '2016'
            }
        ],
        'projects': [
            {
                'name': 'Modelo Predictivo Bancario (2023)',
                'description': [
                    'Desarrollo autónomo de modelo de Machine Learning con Python y TensorFlow',
                    'Alcanzó precisión del 86.95% usando técnicas avanzadas de feature engineering'
                ],
                'relevance_score': 0.9
            },
            {
                'name': 'Sistema de Análisis de Datos en Tiempo Real (2022)',
                'description': [
                    'Creación de solución end-to-end usando Python, SQL y APIs para procesamiento continuo',
                    'Implementación autónoma de arquitectura escalable con TensorFlow para ML en producción'
                ],
                'relevance_score': 0.8
            }
        ],
        'raw_text': '''Roberto de Gouveia 
        Profesional con 1 años de experiencia en análisis de datos, especializado en Python (avanzado), SQL (avanzado), y herramientas de Business Intelligence como Power BI y Tableau.
        Implementación de pipelines de datos con Python, pandas, numpy para procesamiento en gran escala
        Gestión y consulta de bases de datos SQL, MySQL y SQL Server para extracción de insights'''
    }
    
    # Resultados de matching simulados
    matching_results = {
        'matches': [
            {
                'requirement': 'python',
                'similarity': 0.85,
                'evidence': 'Python (avanzado)',
                'requirement_type': 'must_have'
            },
            {
                'requirement': 'sql',
                'similarity': 0.90,
                'evidence': 'SQL (avanzado)',
                'requirement_type': 'must_have'
            }
        ],
        'coverage_percentage': 75.0
    }
    
    # Oferta de trabajo simulada
    job_offer = {
        'title': 'Senior Data Scientist',
        'company': 'Tech Innovation Ltd'
    }
    
    # Crear adaptador y generar CV
    adapter = CVAdapter()
    adapted_cv = adapter.adapt_cv(sample_cv, job_offer, matching_results)
    
    # Generar archivo DOCX profesional
    filename = 'exports/cv_profesional_test.docx'
    result_file = adapter.export_to_docx(adapted_cv, filename)
    
    print(f"✅ CV profesional generado exitosamente: {result_file}")
    print("\n=== MEJORAS IMPLEMENTADAS ===")
    print("📐 Márgenes ajustados (0.8 pulgadas)")
    print("🎨 Colores profesionales (azul corporativo #1F4E79)")
    print("📝 Tipografía mejorada con tamaños variables")
    print("📊 Habilidades categorizadas por tipo")
    print("🔗 Separadores visuales entre secciones")
    print("✨ Formato centrado para encabezado")
    print("📋 Viñetas mejoradas para experiencia")
    print("🎯 Proyectos destacados limitados a top 3")
    print("📞 Iconos en información de contacto")
    
    return result_file

if __name__ == "__main__":
    test_professional_cv_format()