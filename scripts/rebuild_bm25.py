#!/usr/bin/env python3
"""
rebuild_bm25.py — Rebuild BM25 index dari data ChromaDB yang sudah ada.

Dijalankan TANPA re-parse PDF dan TANPA biaya LlamaParse.
Baca semua chunks dari ChromaDB, build BM25 index, simpan ke disk.

Usage (dari dalam container):
    python /app/scripts/rebuild_bm25.py

Usage (dari host via docker-compose exec):
    docker-compose -f docker/docker-compose.yml exec backend \
        python /app/scripts/rebuild_bm25.py
"""

import sys
from pathlib import Path

# Pastikan src/ ada di Python path
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import chromadb
from retrieval.bm25_retriever import BM25Retriever

CHROMA_PATH  = Path(__file__).resolve().parent.parent / "data" / "processed" / "chroma_db"
BM25_DIR     = Path(__file__).resolve().parent.parent / "data" / "processed" / "bm25_index"

COLLECTIONS = [
    "bi_regulations",
    "ojk_regulations",
]


def rebuild_bm25_for_collection(db: chromadb.PersistentClient, collection_name: str) -> int:
    """
    Baca semua dokumen dari ChromaDB collection, bangun BM25 index.
    Return jumlah chunk yang di-index.
    """
    try:
        col = db.get_collection(collection_name)
    except Exception as e:
        print(f"  [SKIP] Collection '{collection_name}' tidak ditemukan: {e}")
        return 0

    total = col.count()
    if total == 0:
        print(f"  [SKIP] Collection '{collection_name}' kosong.")
        return 0

    print(f"  Membaca {total} chunks dari ChromaDB collection '{collection_name}'...")

    # Baca semua data dari ChromaDB dalam batch
    batch_size = 500
    all_chunks = []
    offset = 0
    while offset < total:
        result = col.get(
            limit=batch_size,
            offset=offset,
            include=["documents", "metadatas"],
        )
        docs      = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        for doc, meta in zip(docs, metadatas):
            if doc:
                all_chunks.append({"text": doc, "metadata": meta or {}})
        offset += batch_size

    if not all_chunks:
        print(f"  [SKIP] Tidak ada dokumen yang berhasil dibaca dari '{collection_name}'.")
        return 0

    # Build BM25
    bm25_path = str(BM25_DIR / collection_name)
    bm25 = BM25Retriever(index_path=bm25_path)
    bm25.build_index(all_chunks)
    return len(all_chunks)


def main():
    print("=" * 60)
    print("  BM25 Index Rebuild — dari ChromaDB existing data")
    print(f"  ChromaDB : {CHROMA_PATH}")
    print(f"  BM25 dir : {BM25_DIR}")
    print("=" * 60)

    if not CHROMA_PATH.exists():
        print(f"ERROR: ChromaDB path tidak ditemukan: {CHROMA_PATH}")
        sys.exit(1)

    db = chromadb.PersistentClient(path=str(CHROMA_PATH))
    available = [c.name for c in db.list_collections()]
    print(f"\nCollections tersedia di ChromaDB: {available}\n")

    total_indexed = 0
    for col_name in COLLECTIONS:
        print(f"[{col_name}]")
        n = rebuild_bm25_for_collection(db, col_name)
        total_indexed += n
        print()

    print("=" * 60)
    print(f"  Selesai. Total chunk di-index: {total_indexed}")
    print(f"  BM25 index tersimpan di: {BM25_DIR}")
    print("=" * 60)
    print("\nVerifikasi: jalankan ulang ablation untuk melihat 'Hybrid retriever aktif'")


if __name__ == "__main__":
    main()
