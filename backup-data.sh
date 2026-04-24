#!/bin/bash
#
# backup-data.sh - Backup ChromaDB dan BM25 untuk transfer ke server
# Usage: ./backup-data.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_DIR="$SCRIPT_DIR/data"
BACKUP_DIR="$SCRIPT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="compliance-data-$TIMESTAMP"

echo "📦 Data Backup Script"
echo "====================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check data exists
if [ ! -d "$DATA_DIR/processed/chroma_db" ]; then
    echo -e "${RED}[ERROR]${NC} ChromaDB tidak ditemukan di $DATA_DIR/processed/chroma_db"
    echo "Jalankan ingest terlebih dahulu:"
    echo "  python src/ingest.py --force"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

print_status "Memeriksa data..."

# Check collections
CHROMA_COUNT=$(find "$DATA_DIR/processed/chroma_db" -type d -name "*_regulations" | wc -l)
print_status "ChromaDB collections: $CHROMA_COUNT"

# Check BM25
if [ -d "$DATA_DIR/processed/bm25_index" ]; then
    BM25_COUNT=$(find "$DATA_DIR/processed/bm25_index" -type d -name "*_regulations" | wc -l)
    print_status "BM25 indexes: $BM25_COUNT"
else
    print_warning "BM25 index belum ada"
fi

# Check cache
if [ -d "$DATA_DIR/cache" ]; then
    CACHE_COUNT=$(find "$DATA_DIR/cache" -type f | wc -l)
    print_status "Cache files: $CACHE_COUNT"
fi

echo ""
print_status "Membuat archive..."

# Create tar.gz archive
ARCHIVE_PATH="$BACKUP_DIR/$BACKUP_NAME.tar.gz"

tar -czf "$ARCHIVE_PATH" \
    -C "$DATA_DIR" \
    --exclude='*.tmp' \
    --exclude='*.log' \
    processed/chroma_db \
    processed/bm25_index \
    cache \
    raw/*.pdf 2>/dev/null || true

# Get size
ARCHIVE_SIZE=$(du -h "$ARCHIVE_PATH" | cut -f1)

echo ""
print_status "✅ Backup selesai!"
echo ""
echo "File: $ARCHIVE_PATH"
echo "Size: $ARCHIVE_SIZE"
echo ""
echo "Untuk transfer ke server:"
echo "  scp $ARCHIVE_PATH user@server:/opt/nlp-compliance-rag/backups/"
echo ""
echo "Atau langsung deploy dengan:"
echo "  ./deploy.sh user@server-ip"

# Create latest symlink
ln -sf "$BACKUP_NAME.tar.gz" "$BACKUP_DIR/latest-data.tar.gz"
print_status "Symlink 'latest-data.tar.gz' diperbarui"