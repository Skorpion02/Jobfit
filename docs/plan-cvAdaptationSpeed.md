# Plan: Acelerar el Pipeline de Adaptación de CV

**TL;DR:** La mayor ganancia está en el flujo "Análisis Pro ATS" que hace **8 llamadas LLM totalmente secuenciales**. Con 3 cambios principales (paralelización, eliminación de una llamada redundante, y caché de sesión) se puede pasar de ~90-180s a ~25-50s.

---

## Bottlenecks por impacto

| # | Problema | Tiempo ahorrado |
|---|----------|----------------|
| 1 | 8 llamadas LLM secuenciales en `analyze_full_cv` | 🔴 ~60% del tiempo total |
| 2 | `_extract_cv_insights` — llamada LLM extra innecesaria | 🟠 1 call completa ahorrada |
| 3 | Job/CV re-parseados desde cero en cada tab | 🟠 1 call LLM + I/O ahorrada |
| 4 | `max_tokens=3500` en Deliverable E — sobredimensionado | 🟡 Reduce tiempo de inferencia |
| 5 | Prompts A/B/C sin truncación de inputs | 🟡 Reduce input tokens |

---

## Step 1 — Paralelizar deliverables independientes

**Archivo:** `src/generator/cv_full_analyzer.py`

A/B/E/F son independientes entre sí. Solo C depende de A, y D depende de B.

```
Wave 1 (parallel): [A: diagnosis] [B: keywords] [E: variants] [F: checklist]
Wave 2 (parallel): [C: changes ← A]  [D: cv_rewrite ← B]
```

```python
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=4) as ex:
    fut_a = ex.submit(self._deliverable_a, cv_text, job_text)
    fut_b = ex.submit(self._deliverable_b, cv_text, job_text)
    fut_e = ex.submit(self._deliverable_e, cv_text, job_text)
    fut_f = ex.submit(self._deliverable_f, cv_text, job_text)
    diag, kw, var, chk = fut_a.result(), fut_b.result(), fut_e.result(), fut_f.result()

with ThreadPoolExecutor(max_workers=2) as ex:
    fut_c = ex.submit(self._deliverable_c, cv_text, job_text, diag)
    fut_d = ex.submit(self._deliverable_d, cv_text, job_text, kw)
    changes, rewrite = fut_c.result(), fut_d.result()
```

---

## Step 2 — Eliminar `_extract_cv_insights` como call separada

**Archivo:** `src/generator/cv_full_analyzer.py`

Esta call solo existe para inyectar logros/stack en el prompt D. Usar los datos ya parseados:

```python
# Antes: siempre dispara una LLM call
logros, stack = self._extract_cv_insights(cv_text)

# Después: usar datos ya parseados del CV
logros = cv_data.get("achievements") or ""
stack  = ", ".join(cv_data.get("skills", {}).get("technical", []))
```

---

## Step 3 — Caché de sesión por hash CV+Job

**Archivo:** `src/generator/cv_full_analyzer.py`

```python
import hashlib

cache_key = hashlib.md5((cv_text + job_text).encode()).hexdigest()
if cache_key in self._cache:
    return self._cache[cache_key]
result = self._run_analysis(cv_text, job_text)
self._cache[cache_key] = result
```

Agregar botón "Limpiar caché" en `interface/gradio_app.py`.

---

## Step 4 — Compartir datos parseados entre tabs

**Archivo:** `interface/gradio_app.py`

```python
# Antes: re-parsea siempre
self._clear_cache()
job_data = self.job_parser.extract_job_data(job_text)

# Después: reutilizar si el texto no cambió
job_hash = hashlib.md5(job_text.encode()).hexdigest()
if self._last_job_hash != job_hash:
    self.current_job_data = self.job_parser.extract_job_data(job_text)
    self._last_job_hash = job_hash
job_data = self.current_job_data
```

---

## Step 5 — Reducir `max_tokens` mal calibrados

**Archivos:** `config/prompts.py`, `src/generator/cv_full_analyzer.py`

| Deliverable | Actual | Recomendado | Justificación |
|-------------|--------|-------------|---------------|
| E — Variants | 3500 | 1500 | Salida real ~600-900 tokens |
| F — ATS Checklist | 1200 | 800 | 12-15 items ~400-600 tokens |
| B — Keywords | 2000 | 1200 | 20-40 filas ~500-800 tokens |

Aplicar truncación consistente en A/B/C (como ya hacen E/F):

```python
cv_text_short  = cv_text[:2000]
job_text_short = job_text[:1500]
```

---

## Step 6 — Eliminar normalización de CV duplicada

**Archivos:** `src/generator/cv_adapter.py`, `interface/gradio_app.py`

Extraer `normalize_cv_data(cv_data)` a `src/utils/cv_utils.py` y llamarla una sola vez post-parsing, en lugar de repetirla en ambos archivos.

---

## Expected Time Savings

| Optimización | Actual | Esperado | Ahorro |
|---|---|---|---|
| Paralelizar waves 1+2 | ~150s | ~55s | -63% |
| Eliminar `_extract_cv_insights` | +25s | 0s | -25s |
| Caché (segunda ejecución) | ~150s | <1s | -100% |
| Compartir job parsing entre tabs | +20s | 0s | -20s |
| Reducir `max_tokens` | variable | ~-15% inferencia | moderado |

**Primera ejecución:** ~150s → ~40-50s  
**Ejecución repetida:** ~150s → <1s

---

## Decisions

- **`ThreadPoolExecutor` sobre `asyncio`:** la API de LMStudio usa `requests` síncrono; threading es la opción correcta sin refactorizar el cliente HTTP.
- **Caché en memoria (no en disco):** simple, sin dependencias extra, se limpia al reiniciar la app.
- **No reducir calidad de prompts:** todas las optimizaciones de tokens solo eliminan contenido que ya se trunca o que supera la capacidad de salida real.
