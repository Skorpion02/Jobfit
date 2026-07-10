<p align="center">
  <img src="assets/Banner.png" alt="JobFit Agent banner" width="100%" />
</p>

> **Adapta tu CV a cualquier oferta de trabajo con IA local. 100 % privado, 100 % tuyo.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Gradio](https://img.shields.io/badge/UI-Gradio-orange?logo=gradio)](https://gradio.app)
[![LM Studio](https://img.shields.io/badge/IA-LM%20Studio-purple)](https://lmstudio.ai)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)](docker/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## ¿Qué hace?

JobFit Agent analiza una oferta de trabajo y tu CV y, en una sola pasada, entrega **6 documentos** listos para revisar y enviar:

| Entregable | Descripción |
|---|---|
| **A · Diagnóstico de encaje** | Score 0-100 + top 5 fortalezas y top 5 gaps frente a la oferta |
| **B · Keywords ATS** | Tabla de 20-40 keywords clasificadas como `presente` / `débil` / `ausente` |
| **C · Plan de cambios** | 8-15 acciones priorizadas: 🔴 alto · 🟡 medio · 🟢 opcional |
| **D · CV reescrito** | CV adaptado, sin invenciones, descargable en `.txt` y `.docx` |
| **E · Variantes Resumen + Skills** | Versión *ATS-first* (keyword-density) y versión *Recruiter-first* (narrativa) |
| **F · Checklist ATS final** | 12-15 puntos de validación antes de enviar |

> 🔒 Todo el procesamiento ocurre en tu máquina. Ningún dato sale al exterior.

---

## Inicio rápido

### Opción A — Nativo (Windows / macOS / Linux)

```bash
# 1. Clonar e instalar
git clone https://github.com/Skorpion02/JobFit.git
cd JobFit
python -m venv venv
# Windows:  venv\Scripts\activate
# macOS/Linux:  source venv/bin/activate
pip install -r requirements.txt

# 2. Arrancar LM Studio (ver guía de configuración) y luego:
python main.py
#  → http://localhost:7860
```

En Windows: doble clic en **`start.bat`** y listo (crea venv si no existe, instala deps y arranca).

### Opción B — Docker (GPU NVIDIA)

```bash
docker compose up -d --build
#  → http://localhost:7860
```

Variante CPU-only: `docker compose -f docker-compose.cpu.yml up -d --build`.

> 📘 **Setup detallado + troubleshooting**: [`docs/SETUP.md`](docs/SETUP.md)

---

## Configuración de LM Studio

Sin LM Studio, JobFit funciona en **modo reglas** (resultados aproximados). Con LM Studio activo se generan los 6 entregables con calidad profesional.

1. Descarga LM Studio desde [lmstudio.ai](https://lmstudio.ai) (versión ≥ 0.3.10 recomendada).
2. Descarga un modelo. Recomendaciones según VRAM:

   | VRAM disponible | Modelo recomendado | Velocidad aprox. |
   |---|---|---|
   | 16 GB+ | `Qwen2.5-14B-Instruct Q4_K_M` (~9 GB) | 35-45 tok/s |
   | 8-12 GB | `Llama-3.1-8B-Instruct Q6_K` (~6.6 GB) | 70-90 tok/s |
   | < 8 GB | `Qwen2.5-7B-Instruct Q4_K_M` (~5 GB) | 50-70 tok/s |

3. Pestaña **Local Server** → carga el modelo → **Start Server** (puerto `1234`).
4. JobFit detecta la conexión automáticamente. Ajusta `LMSTUDIO_MODEL` en `.env` si tu modelo tiene otro identificador.

---

## Estructura del proyecto

```
JobFit/
├── main.py                    Punto de entrada (CLI + Gradio)
├── pyproject.toml             Metadatos, dependencias, tooling
├── requirements.txt           Mirror para `pip install -r`
├── start.bat / install.bat / dev_tools.bat   Wrappers de scripts/
│
├── src/
│   ├── scraper/               Extracción de ofertas (genérico + LinkedIn)
│   ├── extractor/             Parsers CV y oferta (PDF/DOCX/TXT)
│   ├── auditor/               Scoring de realismo de ofertas
│   ├── matcher/               Matching semántico (Sentence Transformers)
│   ├── generator/             Adaptador CV + analizador ATS completo
│   ├── llm/                   Cliente LM Studio (OpenAI-compat)
│   └── utils/                 Helpers (anti-SSRF, normalización)
│
├── config/                    Settings (.env) y prompts del LLM
├── interface/                 Aplicación Gradio
├── tests/                     Suite pytest
│
├── docker/                    Imagen Docker (GPU y CPU)
├── docker-compose*.yml        Lanzadores GPU / CPU
│
├── scripts/                   Launchers .bat reales + utilidades
├── docs/                      Documentación técnica
├── data/ exports/ logs/       Plantillas, outputs, logs (gitignored)
├── notebooks/                 Demo en Jupyter
└── assets/                    Imágenes del README
```

> 📐 Detalle de la arquitectura en [`docs/STRUCTURE.md`](docs/STRUCTURE.md).

---

## Cómo se usa

### 1 · Análisis ATS completo (pestaña principal)

1. Abre `http://localhost:7860`.
2. Sube tu CV (PDF, DOCX o TXT).
3. Pega la URL de la oferta o su texto completo.
4. Ajusta idioma, longitud, rol y nivel si quieres.
5. Pulsa **Analizar** → ves los 6 entregables con barra de progreso por fases.
6. Descarga el CV reescrito en `.txt` o `.docx`.

El CV generado:
- ✅ Respeta el 100 % de tu experiencia real (sin inventar nada).
- ✅ Usa secciones ATS-friendly (sin tablas, sin columnas, sin iconos).
- ✅ Sin meta-comentarios del modelo, sin placeholders tipo `[Tu LinkedIn]`.

### 2 · Auditoría de ofertas

Pega solo la oferta y obtén un score de realismo 0-100 con detección de:
- Contradicciones seniority ↔ salario.
- Requisitos excesivos o indefinidos.
- Stack tecnológico incoherente.

### 3 · Matching CV ↔ oferta

Comparación semántica entre tu perfil y los requisitos. Detecta similitudes reales, no solo palabras exactas; identifica qué cubres y cuáles son tus gaps.

---

## Variables de entorno

Copia `.env.example` a `.env` y ajusta:

```env
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=qwen/qwen2.5-14b-instruct
USE_LMSTUDIO=true

EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
MAX_CV_SIZE_MB=10
SCRAPING_TIMEOUT=30
```

> 📘 Listado completo y explicación de cada variable: [`docs/SETUP.md#variables-de-entorno`](docs/SETUP.md).

---

## Herramientas de desarrollo

```bash
dev_tools.bat                 # Menú: tests, deps, estado, reset venv
python -m pytest              # Suite completa
pip install -e ".[dev]"       # Instala dev deps (pytest-cov, ruff)
ruff check .                  # Linter
python scripts/log_viewer.py  # Tail coloreado de logs
python scripts/check_env.py   # Verifica entorno e imports
```

---

## Privacidad y seguridad

- 🔒 **Sin APIs externas**: toda la IA corre localmente con LM Studio.
- 🛡️ **Anti-SSRF en el scraper**: solo dominios de portales de empleo en la allowlist (`linkedin.com`, `indeed.com`, `infojobs.net`, `tecnoempleo.com`, …) y bloqueo de IPs privadas.
- 📁 **Sin almacenamiento permanente**: CVs procesados en memoria y temporales.
- 📋 **Logs locales**: solo información técnica, nunca contenido de CVs.

---

## Licencia

Este proyecto está bajo la licencia [MIT](LICENSE).

---

## Contribuciones

¡Issues y pull requests son bienvenidos! Antes de abrir un PR:

1. `pip install -e ".[dev]"`
2. `ruff check . && pytest`

---

## Contacto

Abre un issue o contacta a través de [Skorpion02](https://github.com/Skorpion02).

---

## Agradecimientos

- [LM Studio](https://lmstudio.ai) — runtime de IA local
- [Hugging Face](https://huggingface.co) — modelos de embeddings y hub
- [Gradio](https://gradio.app) — interfaz web

---

<p align="center">
  ⭐️ <b>Si te ha sido útil, deja una estrella</b> ⭐️<br>
  <br>
  <sub>Hecho con ❤️ por <a href="https://github.com/Skorpion02">Skorpion02</a></sub>
</p>
