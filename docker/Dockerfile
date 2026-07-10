# JobFit — imagen con torch CUDA (GPU) + OCR completo.
# Requiere en el host: driver NVIDIA + nvidia-container-toolkit, y ejecutar con --gpus all
# (docker-compose.yml ya reserva la GPU).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface \
    EASYOCR_MODULE_PATH=/app/.cache/easyocr

# Dependencias de sistema:
#   poppler-utils -> pdf2image (convert_from_path) en la ruta OCR
#   libgl1 / libglib2.0-0 -> opencv (dependencia de easyocr)
#   curl -> HEALTHCHECK
RUN apt-get update && apt-get install -y --no-install-recommends \
        poppler-utils libgl1 libglib2.0-0 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# torch + torchvision CUDA primero (capa pesada y cacheable). Ajustar cuXXX al driver del host.
# cu128 (CUDA 12.8) incluye kernels sm_120, necesarios para GPUs Blackwell (RTX 50, p. ej.
# RTX 5060 Ti). Con cu124 (hasta sm_90) torch detecta la GPU pero falla al computar.
# Se incluye torchvision para que easyocr no reinstale torch desde PyPI (que lo pisaria con
# una build CUDA distinta y duplicaria la descarga).
RUN pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

# Resto de dependencias (incluye OCR: easyocr + pdf2image).
# El Dockerfile vive en docker/, pero el build context se invoca desde la raíz del
# repo (ver docker-compose.yml), así que la ruta es docker/requirements.txt.
COPY docker/requirements.txt ./requirements.docker.txt
RUN pip install -r requirements.docker.txt

# Pre-descarga de modelos para que el primer arranque no necesite red:
#   - embeddings all-MiniLM-L6-v2 (sentence-transformers / HuggingFace)
#   - modelos de detección+reconocimiento de easyocr (es, en)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')" \
 && python -c "import easyocr; easyocr.Reader(['es', 'en'])"

# Código de la aplicación (.dockerignore excluye venv, .env, caches, etc.)
COPY . .

# Usuario no-root + directorios escribibles en runtime
RUN useradd -m appuser \
 && mkdir -p logs exports data/temp data/templates data/examples \
 && chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

# Gradio responde 200 en / cuando la interfaz está lista
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD curl -fsS http://localhost:7860/ || exit 1

# Forzar host 0.0.0.0 (el default 127.0.0.1 no es accesible desde fuera del contenedor)
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "7860"]
