# 🧪 Guía de Testing - JobFit Agent

Esta guía explica cómo ejecutar y crear tests para el sistema JobFit Agent.

## 🏃‍♂️ Ejecutar Tests

### Ejecución Rápida
```bash
# Usar el panel de desarrollador
dev_tools.bat
# Seleccionar opción [2] 🧪 Ejecutar tests
```

### Ejecución Manual
```bash
# Activar entorno virtual
venv\Scripts\activate

# Tests individuales
python tests\test_cv_format.py
python tests\test_parser.py

# Test completo del flujo
python tests\test_full_flow.py
```

## 📋 Descripción de Tests

### `test_cv_format.py`
- **Propósito**: Validar generación de CV profesional
- **Qué prueba**:
  - Formato corporativo DOCX
  - Estructura y estilos
  - Adaptación de contenido
- **Output**: CV de ejemplo en `exports/`

### `test_parser.py`
- **Propósito**: Tests unitarios del parser
- **Qué prueba**:
  - Extracción de campos específicos
  - Manejo de formatos diversos
  - Validación de datos

### `test_with_threshold.py`
- **Propósito**: Validar sistema de scoring
- **Qué prueba**:
  - Cálculo de scores de matching
  - Umbrales de compatibilidad
  - Métricas de calidad

### `test_full_flow.py`
- **Propósito**: Test de integración completa
- **Qué prueba**:
  - Flujo CV → Oferta → Adaptación
  - Interface Gradio
  - Exportación final

## 🔧 Crear Nuevos Tests

### Template Básico
```python
#!/usr/bin/env python3
"""
Test para [funcionalidad]
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_nueva_funcionalidad():
    """Descripción del test"""
    # Setup
    
    # Ejecución
    
    # Verificación
    assert resultado_esperado == resultado_real
    
    print("✅ Test pasado: Nueva funcionalidad")

if __name__ == "__main__":
    test_nueva_funcionalidad()
```

### Guidelines de Testing

#### ✅ Buenas Prácticas
- **Nomenclatura clara**: `test_[componente]_[funcionalidad].py`
- **Documentación**: Docstrings explicando qué se prueba
- **Aislamiento**: Cada test independiente
- **Cleanup**: Limpiar archivos temporales
- **Assertions claras**: Mensajes descriptivos

#### ❌ Evitar
- Tests que dependan de estado externo
- Hardcodear paths absolutos
- Tests que modifiquen configuración global
- Dependencias entre tests

## 📊 Interpretación de Resultados

### Outputs Esperados

#### Test Exitoso ✅
```
🧪 Ejecutando tests...
✅ LM Studio conectado
✅ Test completado correctamente
```

#### Test con Warning ⚠️
```
⚠️ LM Studio no disponible, usando fallback
✅ Extracción exitosa con reglas
✅ Test de fallback completado
```

#### Test Fallido ❌
```
❌ Error: No se pudo extraer información
Error: Connection refused
```

### Debugging de Fallos

1. **Verificar dependencias**:
   ```bash
   pip list | findstr "gradio torch"
   ```

2. **Check logs**:
   ```bash
   type logs\jobfit.log
   ```

## 🚀 Automatización CI/CD

### GitHub Actions (futuro)
```yaml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: windows-latest
    steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - run: pip install -r requirements.txt
    - run: python tests/test_cv_format.py
    - run: python tests/test_parser.py
```

## 📈 Coverage y Métricas

### Cobertura Objetivo
- **Core Logic**: >90%
- **Interface**: >70%
- **Utils**: >85%

### Comandos útiles
```bash
# Generar reporte de coverage (si pytest instalado)
pytest --cov=src tests/

# Benchmark de performance
python -m timeit -s "from src.extractor.job_parser import JobParser" "parser = JobParser()"
```

## 🔍 Debugging Avanzado

### Modo Verbose
```python
# En cualquier test, añadir:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Profiling
```python
import cProfile
cProfile.run('test_function()')
```

### Memory Usage
```python
import tracemalloc
tracemalloc.start()
# ... ejecutar test ...
current, peak = tracemalloc.get_traced_memory()
print(f"Memory: current={current/1024/1024:.1f}MB, peak={peak/1024/1024:.1f}MB")
```