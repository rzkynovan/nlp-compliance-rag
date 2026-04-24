# 🚀 Deployment Guide - Server 2CPU 2GB RAM

Panduan deployment aplikasi NLP Compliance RAG ke server dengan resource terbatas.

## 📋 Prerequisites

### Local Machine (Development)
- Docker & Docker Compose
- Python 3.11+ (untuk ingest data)
- SSH access ke server
- Git

### Server (Production)
- OS: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- Resource: **2CPU 2GB RAM minimum**
- Docker & Docker Compose (akan di-install otomatis)
- Port terbuka: 3000 (frontend), 8000 (backend)

## 🔧 File Deployment

```
deploy/
├── deploy.sh              # Script deployment utama
├── backup-data.sh         # Backup data untuk transfer
└── server-setup.sh        # Setup server (dijalankan via SSH)

docker/
├── docker-compose.prod.yml    # Konfigurasi production (lightweight)
└── ... (file lainnya)
```

## 📦 Data yang Perlu Ditransfer

**⚠️ PENTING:** Data ChromaDB dan BM25 TIDAK boleh di-push ke GitHub (terlalu besar & generated data).

Data yang harus ditransfer terpisah:

```
data/
├── processed/
│   ├── chroma_db/         # 2,621 vectors (~50-100MB)
│   │   ├── chroma.sqlite3
│   │   ├── bi_regulations/
│   │   └── ojk_regulations/
│   │
│   └── bm25_index/        # BM25 index (~10-20MB)
│       ├── bi_regulations/
│       └── ojk_regulations/
│
├── cache/                 # LlamaParse cache (~5-10MB)
│
└── raw/                   # Source PDFs (~3-5MB)
    ├── PBI_222320.pdf
    ├── PBI_230621.pdf
    └── POJK 22 Tahun 2023.pdf
```

**Total:** ~70-135MB (sekali transfer, hemat biaya LlamaParse!)

## 🚀 Quick Start Deployment

### Step 1: Pastikan Data Sudah Siap (Local)

```bash
# Di local machine - pastikan sudah ingest
python src/ingest.py --force

# Verifikasi data
ls data/processed/chroma_db/
# Output: bi_regulations/  ojk_regulations/  chroma.sqlite3
```

### Step 2: Jalankan Deployment Script

```bash
# Cara 1: Dengan script otomatis
./deploy.sh user@your-server-ip

# Cara 2: Dengan custom GitHub repo
./deploy.sh user@your-server-ip https://github.com/username/repo.git
```

Script akan:
1. ✅ Archive data (ChromaDB + BM25 + Cache)
2. ✅ Install Docker di server (jika belum ada)
3. ✅ Clone repository ke server
4. ✅ Transfer data archive ke server
5. ✅ Extract data di server
6. ✅ Build dan start containers
7. ✅ Verifikasi deployment

### Step 3: Edit Environment Variables (Server)

```bash
# SSH ke server
ssh user@your-server-ip

# Edit .env
nano /opt/nlp-compliance-rag/docker/.env

# Isi dengan API keys:
OPENAI_API_KEY=sk-xxxxxxxxxx
LLAMAPARSE_API_KEY=llx-xxxxxxxxxx
ALLOWED_ORIGINS=http://your-domain:3000,http://localhost:3000
```

### Step 4: Restart Services

```bash
cd /opt/nlp-compliance-rag/docker
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

## 📊 Resource Usage (2CPU 2GB)

| Service | CPU | RAM | Status |
|---------|-----|-----|--------|
| Backend (FastAPI) | 0.8 | 768MB | ✅ Running |
| Frontend (Next.js) | 0.4 | 384MB | ✅ Running |
| **TOTAL** | **1.2** | **~1.15GB** | ✅ OK |

**Sisa resource:** 0.8 CPU, ~850MB RAM untuk OS dan buffer.

## 🔍 Verifikasi Deployment

### Cek Container Status
```bash
ssh user@server
cd /opt/nlp-compliance-rag/docker
docker-compose -f docker-compose.prod.yml ps
```

### Cek ChromaDB
```bash
ssh user@server "docker exec compliance-backend python -c \"
import chromadb
client = chromadb.PersistentClient(path='/app/data/processed/chroma_db')
for c in client.list_collections():
    print(f'{c.name}: {c.count()} vectors')
\""
```

**Expected output:**
```
bi_regulations: 1590 vectors
ojk_regulations: 1031 vectors
```

### Test API
```bash
# Health check
curl http://your-server-ip:8000/api/v1/health

# Test audit
curl -X POST http://your-server-ip:8000/api/v1/audit/analyze \
  -H "Content-Type: application/json" \
  -d '{"clause": "Test", "regulator": "BI"}'
```

## 🔄 Update Deployment

### Update Kode (Pull Latest)
```bash
ssh user@server
cd /opt/nlp-compliance-rag
git pull origin main
cd docker
docker-compose -f docker-compose.prod.yml up -d --build
```

### Update Data (Re-ingest di Local, Transfer Ulang)
```bash
# Di local
python src/ingest.py --force

# Backup dan transfer
./backup-data.sh
scp backups/latest-data.tar.gz user@server:/opt/nlp-compliance-rag/backups/

# Di server
ssh user@server "cd /opt/nlp-compliance-rag && tar -xzf backups/latest-data.tar.gz -C data/"
```

## 💰 Biaya yang Dihindari

Dengan transfer data (bukan re-ingest):

| Resource | Tanpa Transfer | Dengan Transfer | Hemat |
|----------|---------------|-----------------|-------|
| LlamaParse | ~$5-10 | $0 | 100% |
| Embeddings | ~$0.50 | $0 | 100% |
| Waktu | 30 menit | 5 menit | 83% |
| **Total** | **~$6-11** | **$0** | **100%** |

## 🛠️ Troubleshooting

### Container tidak start
```bash
# Cek logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Cek resource
docker stats --no-stream
```

### ChromaDB tidak ditemukan
```bash
# Verifikasi data di server
ssh user@server "ls -la /opt/nlp-compliance-rag/data/processed/chroma_db/"

# Jika kosong, transfer ulang
./deploy.sh user@server
```

### Out of Memory
```bash
# Cek memory usage
free -h

# Restart dengan force
docker-compose -f docker-compose.prod.yml down
docker system prune -f
docker-compose -f docker-compose.prod.yml up -d
```

## 📁 Git Ignore Penting

Pastikan `.gitignore` sudah include:

```gitignore
# Data (jangan di-push ke GitHub)
data/processed/chroma_db/
data/processed/bm25_index/
data/cache/
data/raw/*.pdf
backups/*.tar.gz

# Environment
docker/.env
.env
```

## 📝 Catatan Penting

1. **Data terpisah dari kode**: ChromaDB dan BM25 ditransfer via SCP, bukan Git
2. **SQLite vs PostgreSQL**: Production menggunakan SQLite untuk hemat RAM
3. **No Redis**: Menggunakan in-memory cache untuk simplifikasi
4. **No MLflow**: Experiment tracking di-disable di production untuk hemat resource
5. **Read-only data**: Data di-mount read-only untuk mencegah accidental modification

## ✅ Checklist Pre-Deployment

- [ ] `python src/ingest.py --force` sudah dijalankan di local
- [ ] `ls data/processed/chroma_db/` menunjukkan collections
- [ ] API keys sudah disiapkan (OpenAI, LlamaParse)
- [ ] Server memiliki 2CPU 2GB RAM
- [ ] Port 3000 dan 8000 terbuka
- [ ] SSH access ke server tersedia

## 🎯 Next Steps

Setelah deployment berhasil:

1. Setup domain + SSL (opsional, bisa pakai Nginx + Certbot)
2. Setup monitoring (opsional, bisa pakai UptimeRobot)
3. Backup otomatis (cron job untuk backup data berkala)
4. Log rotation (prevent disk penuh)

Selamat mencoba! 🚀