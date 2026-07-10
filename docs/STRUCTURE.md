# Estructura del repositorio

```
JobFit/
├── README.md, LICENSE, pyproject.toml, requirements.txt
├── .env.example, .gitignore, .dockerignore
├── main.py                       Punto de entrada (CLI/Gradio)
├── start.bat, install.bat, dev_tools.bat   Wrappers (delegan a scripts/)
├── docker-compose.yml            Lanzador GPU
├── docker-compose.cpu.yml        Lanzador CPU
│
├── src/                          Código fuente del agente
│   ├── scraper/                  · Extracción de ofertas (genérico + LinkedIn)
│   ├── extractor/                · Parsers de CV y oferta (PDF/DOCX/TXT)
│   ├── auditor/                  · Score de realismo de ofertas
│   ├── matcher/                  · Matching semántico (Sentence Transformers)
│   ├── generator/                · Adaptador de CV + analizador ATS completo
│   ├── llm/                      · Cliente LM Studio (OpenAI-compat)
│   └── utils/                    · Helpers (anti-SSRF, normalización…)
│
├── config/                       Settings (env) y prompts del LLM
├── interface/                    Aplicación Gradio
├── tests/                        Suite pytest
│
├── docker/                       Imagen Docker (GPU y CPU)
│   ├── Dockerfile                · Build con CUDA + OCR
│   ├── Dockerfile.cpu            · Build CPU-only
│   ├── requirements.txt          · Deps específicas de la imagen
│   └── env.example               · Plantilla de entorno para contenedor
│
├── scripts/                      Scripts auxiliares
│   ├── start.bat, install.bat, dev_tools.bat   · Launchers Windows
│   ├── check_env.py              · Verificación de entorno
│   ├── log_viewer.py             · Tail coloreado de logs
│   └── docker_smoke_test.sh      · Test rápido del contenedor
│
├── data/                         Plantillas, ejemplos, archivos temporales
├── exports/                      CVs y reportes generados
├── logs/                         Logs de runtime
├── notebooks/                    Demo en Jupyter
├── assets/                       Imágenes del README
└── docs/                         Documentación técnica
    ├── architecture.md
    ├── diagrama_flujo_completo.md
    ├── testing_guide.md
    ├── plan-cvAdaptationSpeed.md
    └── STRUCTURE.md              · Este documento
```

## Convenciones

- **Imports absolutos** desde la raíz: `from src.scraper.job_scraper import JobScraper`,
  `from config.settings import settings`, `from interface.gradio_app import JobFitApp`.
- **`main.py`** es el único punto de entrada para uso nativo: `python main.py`.
- **Cada subpaquete** tiene su `__init__.py` con un docstring de una línea para
  documentar su responsabilidad.
- **Tests** en `tests/` siguen el patrón `test_<modulo>.py` y usan pytest.
- **Outputs generados** (`exports/`, `logs/`, `data/temp/`) están en `.gitignore`
  excepto la carpeta vacía, que se conserva.
- **Docker** vive en `docker/` excepto `.dockerignore` y los `docker-compose.*.yml`,
  que deben estar en la raíz porque ahí espera Docker el build context.

## Puntos de entrada

| Cómo | Comando | Para qué |
|---|---|---|
| Doble clic | `start.bat` | Lanzar la app en Windows (UI Gradio en `:7860`) |
| Terminal | `python main.py` | Lanzar nativo, igual que el `.bat` |
| Terminal CLI | `python main.py --cli --job-url ... --cv-path ...` | Sin UI, modo batch |
| Docker GPU | `docker compose up -d --build` | Contenedor con CUDA |
| Docker CPU | `docker compose -f docker-compose.cpu.yml up -d --build` | Contenedor sin GPU |
| Tests | `pytest` | Suite completa |
| Dev tools | `dev_tools.bat` | Menú interactivo (tests, deps, reset venv…) |
