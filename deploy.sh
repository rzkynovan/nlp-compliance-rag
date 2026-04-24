#!/bin/bash
#
# deploy.sh - Deployment script untuk server 2CPU 2GB RAM
# Usage: ./deploy.sh [server-user@ip]
#
# Server Anda:
#   IP: 144.126.136.57
#   User: root
#   Path: /root/nlp-compliance-rag
#

set -e

# Configuration - UPDATE SESUAI SERVER ANDA
SERVER=${1:-"root@144.126.136.57"}
GITHUB_REPO="https://github.com/rzkynovan/nlp-compliance-rag.git"
REMOTE_DIR="/root/nlp-compliance-rag"
LOCAL_DATA_DIR="$(cd "$(dirname "$0")" && pwd)/data"

echo "🚀 NLP Compliance RAG - Deployment Script"
echo "=========================================="
echo ""
echo "Server: $SERVER"
echo "GitHub: $GITHUB_REPO"
echo "Remote: $REMOTE_DIR"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check local data exists
if [ ! -d "$LOCAL_DATA_DIR/processed/chroma_db" ]; then
    print_error "Data ChromaDB tidak ditemukan di: $LOCAL_DATA_DIR/processed/chroma_db"
    echo "Pastikan kamu sudah menjalankan ingest di local:"
    echo "  python src/ingest.py --force"
    exit 1
fi

# Check if data is available
CHROMA_COUNT=$(ls -1 "$LOCAL_DATA_DIR/processed/chroma_db" 2>/dev/null | wc -l)
if [ "$CHROMA_COUNT" -eq 0 ]; then
    print_error "ChromaDB folder kosong!"
    exit 1
fi

print_status "ChromaDB ditemukan: $CHROMA_COUNT files/folders"

# Step 1: Prepare data archive
echo ""
print_status "Step 1: Mempersiapkan data archive..."
ARCHIVE_NAME="nlp-compliance-data-$(date +%Y%m%d-%H%M%S).tar.gz"
ARCHIVE_PATH="/tmp/$ARCHIVE_NAME"

# Build tar command dynamically based on what exists
TAR_ARGS=""

# ChromaDB (wajib ada)
if [ -d "$LOCAL_DATA_DIR/processed/chroma_db" ]; then
    TAR_ARGS="$TAR_ARGS processed/chroma_db"
    print_status "✓ ChromaDB ditemukan"
else
    print_error "ChromaDB tidak ditemukan!"
    exit 1
fi

# BM25 index (opsional - mungkin belum dibuat)
if [ -d "$LOCAL_DATA_DIR/processed/bm25_index" ]; then
    TAR_ARGS="$TAR_ARGS processed/bm25_index"
    print_status "✓ BM25 index ditemukan"
else
    print_warning "BM25 index tidak ditemukan (opsional, akan dibuat otomatis jika hybrid retrieval diaktifkan)"
fi

# Cache (opsional tapi recommended)
if [ -d "$LOCAL_DATA_DIR/cache" ]; then
    TAR_ARGS="$TAR_ARGS cache"
    CACHE_COUNT=$(find "$LOCAL_DATA_DIR/cache" -type f | wc -l)
    print_status "✓ Cache ditemukan ($CACHE_COUNT files)"
fi

# Raw PDFs (opsional)
if [ -d "$LOCAL_DATA_DIR/raw" ] && [ "$(ls -A $LOCAL_DATA_DIR/raw/*.pdf 2>/dev/null)" ]; then
    TAR_ARGS="$TAR_ARGS raw/*.pdf"
    print_status "✓ PDFs ditemukan"
fi

# Create archive
echo ""
print_status "Membuat archive..."
cd "$LOCAL_DATA_DIR"
tar -czf "$ARCHIVE_PATH" $TAR_ARGS

ARCHIVE_SIZE=$(du -h "$ARCHIVE_PATH" | cut -f1)
print_status "Archive dibuat: $ARCHIVE_NAME ($ARCHIVE_SIZE)"

# Step 2: Setup server
echo ""
print_status "Step 2: Setup server dan clone repository..."
print_status "Server: $SERVER (Docker sudah terinstall)"

ssh -o StrictHostKeyChecking=no "$SERVER" << EOF
    set -e
    
    # Check Docker sudah terinstall
    if ! command -v docker &> /dev/null; then
        echo "ERROR: Docker tidak ditemukan!"
        echo "Install Docker terlebih dahulu."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo "ERROR: Docker Compose tidak ditemukan!"
        echo "Install Docker Compose terlebih dahulu."
        exit 1
    fi
    
    echo "✓ Docker terdeteksi"
    echo "✓ Docker Compose terdeteksi"
    
    # Create directory (root already has permission)
    mkdir -p $REMOTE_DIR
    
    # Clone repository (atau pull jika sudah ada)
    if [ -d "$REMOTE_DIR/.git" ]; then
        echo "Repository sudah ada, pulling latest changes..."
        cd $REMOTE_DIR
        git pull origin main
    else
        echo "Cloning repository ke $REMOTE_DIR..."
        git clone "$GITHUB_REPO" $REMOTE_DIR
    fi
    
    # Create data directories
    mkdir -p $REMOTE_DIR/data/{processed,cache,raw}
    
    echo "Server ready!"
EOF

# Step 3: Transfer data archive
echo ""
print_status "Step 3: Transfer data (ChromaDB + BM25 + Cache)..."
print_warning "Ini akan menghemat biaya LlamaParse! Jangan skip!"

scp "$ARCHIVE_PATH" "$SERVER:/tmp/"

# Step 4: Extract data di server
echo ""
print_status "Step 4: Extract data di server..."

ssh "$SERVER" << EOF
    set -e
    cd $REMOTE_DIR
    
    # Extract archive
    echo "Extracting $ARCHIVE_NAME..."
    tar -xzf "/tmp/$ARCHIVE_NAME" -C "$REMOTE_DIR/data/"
    
    # Verifikasi data
    echo ""
    echo "Verifikasi data:"
    ls -lah $REMOTE_DIR/data/processed/
    
    # Cleanup archive
    rm "/tmp/$ARCHIVE_NAME"
    
    echo "Data extracted successfully!"
EOF

# Step 5: Setup environment
echo ""
print_status "Step 5: Setup environment variables..."

# Copy .env.example ke server jika .env belum ada
scp "$(dirname "$0")/.env.example" "$SERVER:$REMOTE_DIR/docker/.env.example"

ssh "$SERVER" << EOF
    set -e
    cd $REMOTE_DIR
    
    # Create .env dari .env.example jika belum ada
    if [ ! -f "$REMOTE_DIR/docker/.env" ]; then
        cp $REMOTE_DIR/docker/.env.example $REMOTE_DIR/docker/.env
        echo ""
        echo "⚠️  IMPORTANT: Edit file .env di server:"
        echo "   ssh $SERVER"
        echo "   nano $REMOTE_DIR/docker/.env"
        echo ""
        echo "Pastikan untuk mengisi:"
        echo "   - OPENAI_API_KEY"
        echo "   - LLAMAPARSE_API_KEY"
    else
        echo ".env sudah ada, melewati..."
    fi
EOF

# Step 6: Build dan run containers
echo ""
print_status "Step 6: Build dan start containers..."

ssh "$SERVER" << EOF
    set -e
    cd $REMOTE_DIR/docker
    
    # Stop containers lama jika ada
    docker-compose down 2>/dev/null || true
    
    # Build dan start dengan resource limits (2CPU 2GB)
    docker-compose -f docker-compose.prod.yml up -d --build
    
    # Wait for services
    echo ""
    echo "Waiting for services to start..."
    sleep 10
    
    # Check health
    echo ""
    echo "Health check:"
    curl -s http://localhost:8000/api/v1/health || echo "⚠️  Backend belum ready"
EOF

# Step 7: Verify deployment
echo ""
print_status "Step 7: Verifikasi deployment..."

ssh "$SERVER" << EOF
    set -e
    cd $REMOTE_DIR
    
    echo ""
    echo "Container status:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo "Verifikasi ChromaDB:"
    docker exec compliance-backend python -c "
import chromadb
client = chromadb.PersistentClient(path='/app/data/processed/chroma_db')
collections = client.list_collections()
print(f'Collections: {len(collections)}')
for c in collections:
    print(f'  - {c.name}: {c.count()} vectors')
" 2>/dev/null || echo "⚠️  ChromaDB check failed - mungkin container masih starting"
    
    echo ""
    echo "Resource usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
EOF

# Cleanup local archive
rm -f "$ARCHIVE_PATH"

# Summary
echo ""
echo "=========================================="
echo "🎉 DEPLOYMENT SELESAI!"
echo "=========================================="
echo ""
echo "Server: 144.126.136.57"
echo "Path: /root/nlp-compliance-rag"
echo ""
echo "Akses aplikasi:"
echo "  Frontend:  http://144.126.136.57:3000"
echo "  Backend:   http://144.126.136.57:8000"
echo "  API Docs:  http://144.126.136.57:8000/api/v1/docs"
echo ""
echo "Command berguna:"
echo "  ssh root@144.126.136.57"
echo "  cd /root/nlp-compliance-rag/docker"
echo "  docker-compose -f docker-compose.prod.yml logs -f backend"
echo "  docker-compose -f docker-compose.prod.yml ps"
echo ""

# Check if .env needs editing
ssh "$SERVER" "grep -q 'OPENAI_API_KEY=sk-' $REMOTE_DIR/docker/.env" 2>/dev/null || {
    print_warning "Jangan lupa edit .env dan isi API keys!"
    echo ""
    echo "   ssh root@144.126.136.57"
    echo "   nano /root/nlp-compliance-rag/docker/.env"
    echo ""
    echo "Isi dengan:"
    echo "   OPENAI_API_KEY=sk-xxxxxxxxxx"
    echo "   LLAMAPARSE_API_KEY=llx-xxxxxxxxxx"
}

print_status "Deployment complete!"