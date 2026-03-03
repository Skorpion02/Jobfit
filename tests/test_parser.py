#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.extractor.job_parser import JobParser

# Test básico de extracción
job_text = """
Desarrollador Python Senior
Empresa: TechCorp
Ubicación: Madrid

Requisitos imprescindibles:
• Python 3.8+
• Django o Flask
• Base de datos (PostgreSQL, MySQL)
• Git y GitHub

Requisitos deseables:
• Docker
• AWS o Azure
• React
• Experiencia con APIs REST
"""

print("=== TESTING JOB PARSER ===")
print(f"Texto de entrada: {len(job_text)} caracteres")

parser = JobParser()
result = parser.extract_job_data(job_text)

print('\n=== RESULTADO DEL PARSING ===')
print(f'Título: {result.get("title", "No encontrado")}')
print(f'Empresa: {result.get("company", "No encontrado")}')
print(f'Ubicación: {result.get("location", "No encontrado")}')

requirements = result.get('requirements', {})
must_have = requirements.get('must_have', [])
nice_to_have = requirements.get('nice_to_have', [])

print(f'\nRequisitos obligatorios ({len(must_have)}):')
for req in must_have:
    print(f'  - {req}')

print(f'\nRequisitos deseables ({len(nice_to_have)}):')
for req in nice_to_have:
    print(f'  - {req}')

print(f'\nTOTAL REQUISITOS: {len(must_have) + len(nice_to_have)}')