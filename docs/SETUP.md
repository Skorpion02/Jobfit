# Guía de instalación de JobFit

Esta guía cubre desde cero hasta la primera ejecución, en nativo y en Docker. Si solo quieres el TL;DR, mira el [README](../README.md#inicio-rápido).

---

## Tabla de contenido

1. [Pre-requisitos](#1-pre-requisitos)
2. [Instalación nativa](#2-instalación-nativa)
3. [Instalación con Docker](#3-instalación-con-docker)
4. [Configurar LM Studio](#4-configurar-lm-studio)
5. [Variables de entorno](#5-variables-de-entorno)
6. [Verificar que todo funciona](#6-verificar-que-todo-funciona)
7. [Actualizar](#7-actualizar)
8. [Troubleshooting](#8-troubleshooting)

---

## 1. Pre-requisitos

| Componente | Mínimo | Recomendado |
|---|---|---|
| **Sistema operativo** | Windows 10, macOS 12, Linux x86_64 | Windows 11 / Ubuntu 22.04 |
| **Python** | 3.10 | 3.12 |
| **RAM** | 8 GB | 16 GB+ |
| **Disco** | 5 GB libres | 20 GB libres |
| **GPU (opcional)** | Cualquier NVIDIA con CUDA | RTX 30/40/50 con ≥ 8 GB VRAM |
| **LM Studio** | versión 0.3.10+ | última estable |

> Sin GPU el sistema funciona pero los 6 entregables tardarán varios minutos en lugar de segundos.
> Sin LM Studio JobFit funciona en **modo reglas**, sin la calidad del LLM.

Comprueba Python:

```bash
python --version          # debe ser >= 3.10
```

---

## 2. Instalación nativa

### Windows (recomendado: doble clic)

```bat
git clone https://github.com/Skorpion02/JobFit.git
cd JobFit
install.bat
```

`install.bat` crea el `venv`, actualiza `pip` y resuelve dependencias en bloques (con avisos si algo opcional falla). Después, doble clic en `start.bat` arranca la app.

### Windows / macOS / Linux (manual)

```bash
git clone https://github.com/Skorpion02/JobFit.git
cd JobFit

# 1. Entorno virtual
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 2. Dependencias core
pip install --upgrade pip
pip install -r requirements.txt

# 3. (Opcional) Instalar como paquete editable + dev tools
pip install -e ".[dev]"

# 4. (Opcional) OCR para PDFs escaneados (~1.5 GB con modelos)
pip install -e ".[ocr]"

# 5. Copiar plantilla de entorno
# Windows:
copy .env.example .env
# macOS / Linux:
cp .env.example .env
```

> **Nota sobre `torch`**: el `requirements.txt` instala la build CPU. Si tienes GPU NVIDIA y quieres acelerar el embedding y el OCR:
>
> ```bash
> pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
> ```
>
> (`cu128` para Blackwell/RTX 50; `cu124` para Ada/RTX 40; `cu121` para Ampere/RTX 30.)

### Arrancar

```bash
python main.py             # http://localhost:7860
python main.py --debug     # con logs detallados
python main.py --host 0.0.0.0 --port 7860   # accesible en LAN (sin auth, usa solo en redes de confianza)
```

---

## 3. Instalación con Docker

### GPU (NVIDIA + nvidia-container-toolkit instalado)

```bash
git clone https://github.com/Skorpion02/JobFit.git
cd JobFit
docker compose up -d --build
#  → http://localhost:7860
```

La imagen GPU usa `cu128` (CUDA 12.8). Para Ampere/Ada (RTX 30/40) edita `docker/Dockerfile` y cambia `cu128` por `cu124`.

### CPU-only

```bash
docker compose -f docker-compose.cpu.yml up -d --build
```

Imagen más ligera, sin CUDA. Funciona en cualquier host con Docker.

### Conectar al LM Studio del host

Dentro del contenedor, `localhost` es el propio contenedor (no tu PC). Por eso `docker-compose.yml` apunta por defecto a `http://host.docker.internal:1234/v1`. Si LM Studio está en otra máquina, exporta:

```bash
# Linux / macOS
export JOBFIT_LMSTUDIO_URL=http://192.168.1.50:1234/v1
docker compose up -d

# Windows PowerShell
$env:JOBFIT_LMSTUDIO_URL = "http://192.168.1.50:1234/v1"
docker compose up -d
```

### Verificar el contenedor

```bash
docker compose ps
docker compose logs -f jobfit
curl http://localhost:7860/      # debe devolver HTML
```

### Limpieza

```bash
docker compose down              # parar y borrar el contenedor
docker compose down -v           # + borrar los volúmenes (data, logs, exports)
```

---

## 4. Configurar LM Studio

JobFit habla con LM Studio vía la API OpenAI-compatible que LM Studio expone en `:1234`.

### 4.1 · Instalar LM Studio

Descarga e instala desde [lmstudio.ai](https://lmstudio.ai). Versión recomendada: **0.3.10 o superior** (soporte estable para `response_format`, runtime CUDA actualizado para Blackwell/RTX 50).

### 4.2 · Elegir y descargar un modelo

En la pestaña 🔍 **Discover** de LM Studio, busca el modelo y descárgalo. Recomendaciones:

| VRAM disponible | Modelo recomendado | Tamaño | Velocidad aprox. en GPU |
|---|---|---|---|
| **16 GB+** | `Qwen2.5-14B-Instruct Q4_K_M` | ~9 GB | 35-45 tok/s |
| 8-12 GB | `Llama-3.1-8B-Instruct Q6_K` | ~6.6 GB | 70-90 tok/s |
| 6-8 GB | `Qwen2.5-7B-Instruct Q4_K_M` | ~5 GB | 50-70 tok/s |
| < 6 GB | `Phi-3.5-mini-instruct Q4_K_M` | ~2.5 GB | 80-100 tok/s |
| Sin GPU | `Qwen2.5-7B-Instruct Q4_K_M` (CPU) | ~5 GB | 3-6 tok/s ⚠ |

**Para JobFit la recomendación top es `Qwen2.5-14B-Instruct Q4_K_M`** por su precisión generando los JSON estructurados que cada entregable requiere.

### 4.3 · Cargar el modelo y arrancar el servidor

1. Pestaña 💻 **Local Server** (o **Developer** en versiones nuevas).
2. **Load Model** → selecciona el modelo descargado.
3. Ajustes recomendados:
   - **Context Length**: 8192 (suficiente para CV + oferta + prompt).
   - **GPU Offload**: máximo posible si tienes GPU.
   - **Flash Attention**: activado si el modelo lo soporta.
4. **Start Server** (botón verde, puerto `1234`).

### 4.4 · Conectar JobFit

Edita `.env`:

```env
LMSTUDIO_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=qwen/qwen2.5-14b-instruct
USE_LMSTUDIO=true
```

El valor exacto de `LMSTUDIO_MODEL` lo ves en la pestaña Local Server bajo "currently loaded model". Si no coincide, JobFit usa el primero que encuentre listado por la API.

> 💡 Si LM Studio < 0.3.10 rechaza `response_format=json_object`, JobFit detecta el 400 al primer intento y desactiva JSON mode para esa sesión. No tienes que hacer nada.

---

## 5. Variables de entorno

| Variable | Default | Descripción |
|---|---|---|
| `LMSTUDIO_BASE_URL` | `http://localhost:1234/v1` | URL del servidor OpenAI-compat |
| `LMSTUDIO_MODEL` | `qwen/qwen2.5-14b-instruct` | Identificador del modelo cargado |
| `USE_LMSTUDIO` | `true` | Activar el LLM (`false` → modo reglas) |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | Modelo de embeddings para matching |
| `LLM_MODEL` | `gpt-4o-mini` | Reservado para fallback futuro (no se usa) |
| `SCRAPING_TIMEOUT` | `30` | Timeout en segundos para el scraper |
| `MAX_RETRIES` | `3` | Reintentos del scraper |
| `USER_AGENT` | `Mozilla/5.0…` | UA para las peticiones HTTP |
| `MAX_CV_SIZE_MB` | `10` | Tamaño máximo del CV que se acepta |
| `MAX_JOB_DESCRIPTION_LENGTH` | `10000` | Caracteres máximos de la oferta |
| `SEMANTIC_SIMILARITY_THRESHOLD` | `0.7` | Umbral para *exact match* en el matcher |
| `EXACT_MATCH_THRESHOLD` | `0.9` | Umbral para coincidencia exacta |
| `EXPORT_FORMAT` | `docx` | Formato de exportación por defecto |
| `TEMPLATE_PATH` | `data/templates/` | Dónde buscar plantillas DOCX |
| `TEMP_PATH` | `data/temp/` | Dónde guardar archivos temporales |

**Variables específicas de Docker** (solo en `docker-compose.yml`):

| Variable | Default | Descripción |
|---|---|---|
| `JOBFIT_LMSTUDIO_URL` | `http://host.docker.internal:1234/v1` | URL del LM Studio desde el contenedor |
| `JOBFIT_LMSTUDIO_MODEL` | `qwen/qwen2.5-14b-instruct` | Modelo a usar |
| `JOBFIT_USE_LMSTUDIO` | `true` | Activar el LLM en el contenedor |

---

## 6. Verificar que todo funciona

### 6.1 · Smoke test del entorno

```bash
python scripts/check_env.py
# → "Componentes principales cargados correctamente"
```

### 6.2 · Smoke test del LM Studio

Con LM Studio corriendo:

```bash
curl http://localhost:1234/v1/models
# → JSON con la lista de modelos disponibles
```

### 6.3 · Arrancar JobFit y verificar la UI

```bash
python main.py --debug
```

Abre [http://localhost:7860](http://localhost:7860). En la pestaña **🔧 Diagnóstico** debes ver:

- ✅ LM Studio: **Conectado**
- ✅ Modelo activo: `qwen/qwen2.5-14b-instruct`

### 6.4 · Test end-to-end

1. Pestaña **🎯 Análisis Pro ATS**.
2. Sube un CV (PDF o DOCX).
3. Pega una URL de oferta (LinkedIn, Indeed, InfoJobs, Tecnoempleo, Jobatus, Glassdoor, Ticjob, Manfred) **o** el texto de la oferta.
4. Pulsa **Generar Análisis Completo**.
5. La barra de progreso debe pasar por: *A → B → D → E → C → F → Empaquetando → Completado*.
6. Al terminar, descarga el CV reescrito y revísalo.

---

## 7. Actualizar

```bash
cd JobFit
git pull
pip install -r requirements.txt --upgrade
# o, si usas pyproject:
pip install -e ".[dev]" --upgrade
```

Para Docker:

```bash
git pull
docker compose up -d --build
```

---

## 8. Troubleshooting

### LM Studio no conecta

- En la pestaña **🔧 Diagnóstico** de JobFit verás los modelos detectados.
- Comprueba que **Start Server** esté pulsado en LM Studio (icono verde).
- Verifica `LMSTUDIO_BASE_URL` en `.env`. Por defecto `http://localhost:1234/v1`.
- En Docker el `localhost` no funciona — usa `host.docker.internal` o IP del host.

### El servidor responde 400 con "response_format must be json_schema or text"

Versión vieja de LM Studio. JobFit lo detecta automáticamente y desactiva JSON mode para esa sesión. Si quieres aprovechar JSON mode, actualiza LM Studio a 0.3.10+.

### El CV reescrito invent ciudades / tecnologías

Síntoma del LLM cuando faltan datos en el parseo estructurado. Soluciones:

1. Asegúrate de que el CV original tenga el bloque de contacto bien formateado (una sola línea: `email · teléfono · ciudad · LinkedIn · GitHub`).
2. Si tu CV tiene tablas o columnas, conviértelo a DOCX/PDF sin formato complejo.
3. Cambia a un modelo mayor (14B → 24B) si tienes VRAM suficiente.

### La descarga del modelo de embeddings se queda colgada

Primer arranque descarga `all-MiniLM-L6-v2` (~90 MB) desde Hugging Face. Si tu red es lenta o el proxy bloquea:

```bash
export HF_HUB_DOWNLOAD_TIMEOUT=300
python main.py
```

### "Cannot find empty port in range: 7860-7864"

Otra app está usando esos puertos:

```bash
python main.py --port 8080
```

### El scraping de LinkedIn falla

LinkedIn frecuentemente devuelve la página de login a scrapers anónimos. **Workaround**: copia el texto de la oferta y pégalo en el campo "Texto de la oferta" en lugar de usar la URL.

### Tests fallan por imports

```bash
# Verifica que estás en el venv:
which python    # macOS/Linux
where python    # Windows
# Deben apuntar a venv/Scripts/python.exe o venv/bin/python
```

Si no:

```bash
# Recrea el entorno:
rm -rf venv
python -m venv venv
source venv/bin/activate   # o venv\Scripts\activate en Windows
pip install -e ".[dev]"
```

### Logs gigantes

`logs/jobfit.log` no rota. Para reducir tamaño:

```bash
# Vacía manteniendo el fichero:
> logs/jobfit.log         # macOS/Linux
echo. > logs/jobfit.log   # Windows
```

O configura rotación añadiendo en `main.py`:

```python
from logging.handlers import RotatingFileHandler
handler = RotatingFileHandler('logs/jobfit.log', maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
```

---

## ¿Sigue sin funcionar?

1. Verifica el estado del LM Studio en la pestaña **🔧 Diagnóstico**.
2. Lee los últimos 100 líneas de `logs/jobfit.log`.
3. Abre un [issue](https://github.com/Skorpion02/JobFit/issues) con:
   - Sistema operativo + versión de Python.
   - Versión de LM Studio y modelo cargado.
   - Output de `python scripts/check_env.py`.
   - Traceback completo si lo hay (sin datos personales del CV).
