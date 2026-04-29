#!/usr/bin/env bash
# run_ablation.sh — Jalankan ablation study: GPT-5.4-mini vs Claude Haiku 4.5
# Usage: ./scripts/run_ablation.sh
#
# Pastikan environment variables tersedia di shell atau di .env:
#   OPENAI_API_KEY, ANTHROPIC_API_KEY, MLFLOW_TRACKING_URI, CHROMADB_PERSIST_DIR

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$SCRIPT_DIR/.."
SRC="$ROOT/src"

# Load .env jika ada
if [ -f "$ROOT/docker/.env" ]; then
  set -a
  source "$ROOT/docker/.env"
  set +a
fi

# Override MLflow URI untuk akses dari luar container
MLFLOW_TRACKING_URI="${MLFLOW_TRACKING_URI_EXTERNAL:-http://localhost:5001}"
export MLFLOW_TRACKING_URI

echo "================================================"
echo "  Compliance Audit — Ablation Study"
echo "  MLflow URI: $MLFLOW_TRACKING_URI"
echo "================================================"
echo ""

# ── Run 1: GPT-5.4-mini + Hybrid Retrieval ──────────────────────────────────
echo ">>> Run 1: GPT-5.4-mini (OpenAI)"
LLM_PROVIDER=openai \
LLM_MODEL=gpt-5.4-mini \
RETRIEVAL_MODE=hybrid \
python "$SRC/evaluation_runner.py" \
  --mlflow-uri "$MLFLOW_TRACKING_URI"

echo ""

# ── Run 2: Claude Haiku 4.5 + Hybrid Retrieval ──────────────────────────────
echo ">>> Run 2: claude-haiku-4-5-20251001 (Anthropic)"
LLM_PROVIDER=anthropic \
LLM_MODEL=claude-haiku-4-5-20251001 \
RETRIEVAL_MODE=hybrid \
python "$SRC/evaluation_runner.py" \
  --mlflow-uri "$MLFLOW_TRACKING_URI"

echo ""
echo "================================================"
echo "  Ablation study selesai."
echo "  Lihat hasil di: $MLFLOW_TRACKING_URI"
echo "  JSON hasil di : $ROOT/data/audit_results/"
echo "================================================"
