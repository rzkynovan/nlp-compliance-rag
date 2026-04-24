#!/bin/bash
#
# deploy.sh - Deployment script untuk server 2CPU 2GB RAM
# Usage: ./deploy.sh <server-user@ip> [github-repo-url]
#

set -e

# Configuration
SERVER=${1:-"user@your-server-ip"}
GITHUB_REPO=${2:-"https://github.com/rzkynovan/nlp-compliance-rag.git"}
REMOTE_DIR="/opt/nlp-compliance-rag"
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

# Create archive dengan data yang perlu ditransfer
tar -czf "$ARCHIVE_PATH" \
    -C "$LOCAL_DATA_DIR" \
    processed/chroma_db \
    processed/bm25_index \
    cache \
    raw/*.pdf 2>/dev/null || true

ARCHIVE_SIZE=$(du -h "$ARCHIVE_PATH" | cut -f1)
print_status "Archive dibuat: $ARCHIVE_NAME ($ARCHIVE_SIZE)"

# Step 2: Setup server
echo ""
print_status "Step 2: Setup server dan clone repository..."

ssh -o StrictHostKeyChecking=no "$SERVER" << EOF
    set -e
    
    # Install Docker & Docker Compose jika belum ada
    if ! command -v docker &> /dev/null; then
        echo "Installing Docker..."
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker \$USER
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo "Installing Docker Compose..."
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
    
    # Create directory
    sudo mkdir -p $REMOTE_DIR
    sudo chown \$USER:\$USER $REMOTE_DIR
    
    # Clone repository (atau pull jika sudah ada)
    if [ -d "$REMOTE_DIR/.git" ]; then
        echo "Repository sudah ada, pulling latest changes..."
        cd $REMOTE_DIR
        git pull origin main
    else
        echo "Cloning repository..."
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
    docker exec docker-backend-1 python -c "
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
echo "Akses aplikasi:"
echo "  Frontend:  http://$SERVER:3000"
echo "  Backend:   http://$SERVER:8000"
echo "  API Docs:  http://$SERVER:8000/api/v1/docs"
echo ""
echo "Command berguna:"
echo "  ssh $SERVER"
echo "  cd $REMOTE_DIR/docker"
echo "  docker-compose -f docker-compose.prod.yml logs -f backend"
echo "  docker-compose -f docker-compose.prod.yml ps"
echo ""
echo "💡 Tips hemat biaya:"
echo "  - Data sudah ditransfer, tidak perlu re-ingest!"
echo "  - ChromaDB: $(ssh $SERVER "ls $REMOTE_DIR/data/processed/chroma_db" 2>/dev/null | wc -l) collections"
echo "  - BM25 index: $(ssh $SERVER "ls $REMOTE_DIR/data/processed/bm25_index" 2>/dev/null | wc -l) collections"
echo ""

# Check if .env needs editing
ssh "$SERVER" "grep -q 'OPENAI_API_KEY=sk-' $REMOTE_DIR/docker/.env" 2>/dev/null || {
    print_warning "Jangan lupa edit .env dan isi API keys!"
    echo "   ssh $SERVER"
    echo "   nano $REMOTE_DIR/docker/.env"
}

print_status "Deployment complete!"