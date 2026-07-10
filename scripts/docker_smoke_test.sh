#!/usr/bin/env bash
# Smoke test end-to-end de la imagen Docker de JobFit.
# Encadena: build -> GPU -> OCR/PDF -> pytest -> arranque + healthcheck HTTP.
# Devuelve codigo != 0 si cualquier paso falla (apto para CI).
#
# Uso:
#   bash scripts/docker_smoke_test.sh
#
# Variables opcionales:
#   SKIP_GPU=1   -> omite la verificacion de GPU (util en hosts sin NVIDIA)
#
# Variante CPU-only (sin GPU) reutilizando este mismo script via COMPOSE_FILE:
#   COMPOSE_FILE=docker-compose.cpu.yml SKIP_GPU=1 bash scripts/docker_smoke_test.sh
set -euo pipefail

COMPOSE="docker compose"
SVC="jobfit"
PORT="${PORT:-7860}"

step() { printf '\n=== %s ===\n' "$1"; }

cleanup() {
  step "Limpieza"
  $COMPOSE down --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

step "1/5 Build de la imagen"
$COMPOSE build

if [ "${SKIP_GPU:-0}" != "1" ]; then
  step "2/5 GPU disponible dentro del contenedor"
  $COMPOSE run --rm "$SVC" python -c \
    "import torch; assert torch.cuda.is_available(), 'CUDA no disponible'; print('GPU:', torch.cuda.get_device_name(0))"
else
  step "2/5 GPU (omitido por SKIP_GPU=1)"
fi

step "3/5 Dependencias OCR/PDF importables + binario poppler"
$COMPOSE run --rm "$SVC" python -c \
  "import easyocr, fitz, pdfplumber, PyPDF2, pdf2image; print('imports OCR/PDF ok')"
$COMPOSE run --rm "$SVC" pdftoppm -h >/dev/null && echo "poppler (pdftoppm) ok"

step "4/5 Tests unitarios (excluye integracion LLM)"
# 'python -m pytest' (no 'pytest') para que /app entre en sys.path y 'src' sea importable.
$COMPOSE run --rm "$SVC" python -m pytest tests -q -k "not lmstudio_integration"

step "5/5 Arranque + healthcheck HTTP"
$COMPOSE up -d
# Esperar a que el contenedor reporte healthy (hasta ~120s)
for i in $(seq 1 24); do
  status="$($COMPOSE ps --format '{{.Health}}' "$SVC" 2>/dev/null || echo '')"
  if [ "$status" = "healthy" ]; then
    echo "contenedor healthy"
    break
  fi
  if [ "$i" = "24" ]; then
    echo "ERROR: el contenedor no llego a healthy"
    $COMPOSE logs "$SVC" || true
    exit 1
  fi
  sleep 5
done

# Verificacion directa del endpoint HTTP de Gradio
if curl -fsS "http://localhost:${PORT}/" >/dev/null; then
  echo "HTTP 200 en http://localhost:${PORT}/ ok"
else
  echo "ERROR: el endpoint HTTP no respondio"
  exit 1
fi

step "SMOKE TEST OK"
