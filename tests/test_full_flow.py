#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(__file__))

from src.extractor.job_parser import JobParser
from src.matcher.semantic_matcher import SemanticMatcher

# Test completo del flujo
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

cv_text = """
Juan Pérez
Desarrollador Python con 5 años de experiencia

Experiencia:
- Desarrollo web con Python y Django durante 3 años
- Bases de datos PostgreSQL y MySQL
- Control de versiones con Git y GitHub
- Deployment con Docker
- APIs REST
- Conocimientos en AWS

Educación:
- Ingeniería Informática
- Certificación AWS
"""

print("=== TEST COMPLETO DEL FLUJO ===")

# 1. Parsear job offer
print("1. Parseando job offer...")
parser = JobParser()
job_data = parser.extract_job_data(job_text)

requirements = job_data.get('requirements', {})
must_have = requirements.get('must_have', [])
nice_to_have = requirements.get('nice_to_have', [])

print(f"Requisitos extraídos: {len(must_have)} obligatorios, {len(nice_to_have)} deseables")
print(f"Must have: {must_have}")
print(f"Nice to have: {nice_to_have}")

# 2. Combinar todos los requisitos para el matching
all_requirements = must_have + nice_to_have
print(f"Total requisitos para matching: {len(all_requirements)}")

# 3. Hacer matching
print("\n2. Haciendo matching semántico...")
matcher = SemanticMatcher()
match_result = matcher.match_requirements_to_cv(all_requirements, cv_text)

print(f"Coverage: {match_result['coverage_percentage']:.1f}%")
print(f"Overall match: {match_result['overall_match']:.3f}")
print(f"Matches encontrados: {len(match_result['matches'])}")

print("\n=== MATCHES DETALLADOS ===")
for match in match_result['matches']:
    print(f"✓ {match['requirement']} - Similitud: {match['similarity']:.3f}")

print("\n=== REQUISITOS NO ENCONTRADOS ===")
for missing in match_result['missing_requirements']:
    print(f"✗ {missing}")