"""
storage_paths.py — Resolusi lokasi ChromaDB yang aman untuk dijalankan di host
maupun di container.

CHROMADB_PERSIST_DIR bisa berisi path container (mis. /app/data/processed/chroma_db
dari docker/.env) yang terbawa ke .env lokal. Di host (macOS/Linux) path itu tidak
bisa ditulis, sehingga ChromaDB gagal dengan "Read-only file system". Fungsi ini
memakai nilai env hanya bila direktorinya bisa dibuat/dipakai; jika tidak, kembali
ke lokasi default repo dengan peringatan.
"""

import os
from pathlib import Path


def resolve_chroma_dir(default: Path) -> Path:
    raw = os.getenv("CHROMADB_PERSIST_DIR")
    if not raw:
        return default
    path = Path(raw).expanduser()
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not os.access(path, os.W_OK):
            raise PermissionError(f"tidak bisa menulis ke {path}")
        return path
    except OSError as e:
        print(
            f"⚠ CHROMADB_PERSIST_DIR={raw} tidak dapat dipakai di mesin ini ({e}). "
            f"Memakai {default}. (Path /app/... hanya berlaku di dalam container Docker.)"
        )
        return default
