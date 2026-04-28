#!/usr/bin/env bash
# prune_db.sh — Hapus semua data audit history dari PostgreSQL
# Usage:
#   ./scripts/prune_db.sh              # konfirmasi interaktif
#   ./scripts/prune_db.sh --yes        # langsung eksekusi tanpa konfirmasi

set -euo pipefail

COMPOSE_FILE="$(dirname "$0")/../docker/docker-compose.yml"

# ── Hitung jumlah record sebelum prune ──────────────────────────────
COUNT=$(docker-compose -f "$COMPOSE_FILE" exec -T db \
  psql -U compliance -d compliance_db -tAc \
  "SELECT COUNT(*) FROM audit_history;")

echo "========================================"
echo "  Compliance RAG — Database Prune Tool"
echo "========================================"
echo "  Jumlah record audit_history : $COUNT"
echo ""

if [[ "$COUNT" -eq 0 ]]; then
  echo "  Database sudah kosong. Tidak ada yang dihapus."
  exit 0
fi

# ── Konfirmasi ───────────────────────────────────────────────────────
if [[ "${1:-}" != "--yes" ]]; then
  read -r -p "  Hapus semua $COUNT record? [y/N] " CONFIRM
  case "$CONFIRM" in
    [yY][eE][sS]|[yY]) ;;
    *) echo "  Dibatalkan."; exit 0 ;;
  esac
fi

# ── Eksekusi TRUNCATE ────────────────────────────────────────────────
docker-compose -f "$COMPOSE_FILE" exec -T db \
  psql -U compliance -d compliance_db -c \
  "TRUNCATE TABLE audit_history RESTART IDENTITY;"

echo ""
echo "  ✓ $COUNT record berhasil dihapus."
echo "========================================"
