#!/usr/bin/env python3
"""
Test para verificar la integración de LM Studio con el job parser
"""

import sys
import os
import pytest

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)


def test_job_parser_with_lmstudio():
    """Prueba el job parser usando LM Studio"""
    
    # Texto de ejemplo de oferta de trabajo
    job_text = """
    Data Scientist Senior - Madrid
    
    Buscamos un Data Scientist Senior con experiencia en:
    
    Requisitos obligatorios:
    • Python (pandas, numpy, scikit-learn)
    • SQL y bases de datos relacionales
    • Machine Learning y Deep Learning
    • Power BI y Tableau para visualización
    • Mínimo 3 años de experiencia
    
    Requisitos deseables:
    • TensorFlow o PyTorch
    • AWS o Azure
    • Docker y Kubernetes
    • Inglés nivel intermedio
    
    Ofrecemos:
    • Salario competitivo 45k-60k
    • Trabajo híbrido
    • Formación continua
    """
    
    # Importar y configurar el parser y comprobar disponibilidad de LM Studio
    from extractor.job_parser import JobParser
    from config.settings import settings

    # Intentar obtener el cliente de LM Studio para decidir si skipear la prueba
    try:
        from src.llm.lmstudio_client import lmstudio_client
    except Exception:
        lmstudio_client = None

    # Si LM Studio no está configurado/disponible, saltar la prueba
    lmstudio_ok = (
        getattr(settings, 'use_lmstudio', False)
        and lmstudio_client
        and getattr(lmstudio_client, 'available', False)
    )

    if not lmstudio_ok:
        pytest.skip("LM Studio no está disponible - salto de integración")

    print("🔧 Configurando para usar LM Studio...")
    settings.use_lmstudio = True

    # Crear parser
    parser = JobParser()

    print("� Extrayendo información con LM Studio...")
    result = parser.extract_job_data(job_text)

    print("\n✅ Resultado de la extracción:")
    print(f"🎯 Título: {result.get('title', 'N/A')}")
    print(f"📍 Ubicación: {result.get('location', 'N/A')}")
    print(f"💰 Salario: {result.get('salary_range', 'N/A')}")
    print(f"📊 Fuente: {result.get('source', 'N/A')}")

    must_have = result.get('must_have', [])
    nice_to_have = result.get('nice_to_have', [])

    print(f"\n🔴 Requisitos obligatorios ({len(must_have)}):")
    for req in must_have[:5]:  # Mostrar primeros 5
        print(f"  • {req}")

    print(f"\n🟡 Requisitos deseables ({len(nice_to_have)}):")
    for req in nice_to_have[:5]:  # Mostrar primeros 5
        print(f"  • {req}")

    # Afirmar que la fuente usada sea LM Studio
    assert result.get('source') == 'lmstudio', (
        f"Se usó {result.get('source')} en lugar de 'lmstudio'"
    )


if __name__ == "__main__":
    test_job_parser_with_lmstudio()
