#!/usr/bin/env bash
# run_ablation.sh — Ablation study: GPT-5.4-mini vs Claude Haiku 4.5
# Dijalankan dari HOST (bukan di dalam container).
#
# Usage:
#   ~/nlp-compliance-rag/scripts/run_ablation.sh

set -euo pipefail

COMPOSE_FILE="$(dirname "$0")/../docker/docker-compose.yml"
ENV_FILE="$(dirname "$0")/../docker/.env"

# Load .env dari host untuk ambil API keys
if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE tidak ditemukan."
  exit 1
fi

# Baca keys dari .env
OPENAI_API_KEY=$(grep  '^OPENAI_API_KEY='     "$ENV_FILE" | cut -d= -f2-)
ANTHROPIC_API_KEY=$(grep '^ANTHROPIC_API_KEY=' "$ENV_FILE" | cut -d= -f2-)

echo "================================================"
echo "  Compliance Audit — Ablation Study"
echo "  MLflow URI : http://mlflow:5000"
echo "================================================"
echo ""

# ── Run 1: GPT-5.4-mini ──────────────────────────────────────────────────────
echo ">>> Run 1: GPT-5.4-mini (OpenAI)"
docker-compose -f "$COMPOSE_FILE" exec \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e LLM_PROVIDER=openai \
  -e LLM_MODEL=gpt-5.4-mini \
  -e RETRIEVAL_MODE=hybrid \
  -e MLFLOW_TRACKING_URI=http://mlflow:5000 \
  backend python /app/src/evaluation_runner.py \
    --mlflow-uri http://mlflow:5000

echo ""

# ── Run 2: Claude Haiku 4.5 ──────────────────────────────────────────────────
echo ">>> Run 2: claude-haiku-4-5-20251001 (Anthropic)"
docker-compose -f "$COMPOSE_FILE" exec \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e LLM_PROVIDER=anthropic \
  -e LLM_MODEL=claude-haiku-4-5-20251001 \
  -e RETRIEVAL_MODE=hybrid \
  -e MLFLOW_TRACKING_URI=http://mlflow:5000 \
  backend python /app/src/evaluation_runner.py \
    --mlflow-uri http://mlflow:5000

echo ""
echo "================================================"
echo "  Ablation study selesai."
echo "  Lihat hasil di: http://<server-ip>:5001"
echo "  JSON hasil di : data/audit_results/"
echo "================================================"
