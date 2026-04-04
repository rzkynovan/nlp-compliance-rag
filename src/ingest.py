"""
ingest.py — Data Ingestion Pipeline untuk Multi-Agent NLP Compliance Auditor
==================================================================================
Skrip ini membaca file PDF regulasi (PBI dan POJK), mengekstrak teksnya
menggunakan LlamaParse, melakukan chunking, dan menyimpannya ke ChromaDB
dengan SEPARATE COLLECTIONS per regulator (BI & OJK).

Struktur Collections:
- bi_regulations: Khusus regulasi Bank Indonesia
- ojk_regulations: Khusus regulasi Otoritas Jasa Keuangan
- pdp_regulations: Khusus UU Perlindungan Data Pribadi (opsional)

Cara pakai:
    cd nlp-compliance-rag
    source venv/bin/activate
    python src/ingest.py
    
Optimasi Biaya:
    --skip-cache  : Force re-parse semua PDF (bakal kena biaya LlamaParse)
    --clear-cache : Hapus cache lama sebelum parse
"""

import os
import sys
import glob
import argparse
from pathlib import Path
from typing import Dict, List
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-proj-xxx"):
    print("OPENAI_API_KEY belum diisi di file .env!")
    sys.exit(1)
if not LLAMA_CLOUD_API_KEY or LLAMA_CLOUD_API_KEY.startswith("llx-xxx"):
    print("LLAMA_CLOUD_API_KEY belum diisi di file .env!")
    sys.exit(1)

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Settings,
    Document,
)
from llama_index.core.node_parser import MarkdownNodeParser
from llama_parse import LlamaParse
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

# Import caching module
from llama_cache import get_cache, LlamaParseCache

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
CHROMA_DB_DIR = BASE_DIR / "data" / "processed" / "chroma_db"

REGULATOR_MAPPING = {
    "PBI": "Bank Indonesia (BI)",
    "POJK": "Otoritas Jasa Keuangan (OJK)",
    "OJK": "Otoritas Jasa Keuangan (OJK)",
    "SEBI": "Bank Indonesia (BI)",
    "UU": "Undang-Undang (UU)",
    "PDP": "Undang-Undang (UU)",
}

COLLECTION_NAMES = {
    "Bank Indonesia (BI)": "bi_regulations",
    "Otoritas Jasa Keuangan (OJK)": "ojk_regulations",
    "Undang-Undang (UU)": "pdp_regulations",
}

print("Mengkonfigurasi LlamaIndex Settings...")

Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",  # Changed from large for cost optimization
    api_key=OPENAI_API_KEY,
)

Settings.llm = OpenAI(
    model="gpt-4o-mini",  # Changed from gpt-4o for cost optimization
    api_key=OPENAI_API_KEY,
    temperature=0.1,
)

Settings.chunk_size = 1024
Settings.chunk_overlap = 128

print("Embedding: text-embedding-3-small (optimized)")
print("LLM: GPT-4o-mini (optimized)")


def detect_regulator(filename: str) -> str:
    filename_upper = filename.upper()
    for keyword, regulator in REGULATOR_MAPPING.items():
        if keyword in filename_upper:
            return regulator
    return "Unknown"


def parse_pdfs(
    use_cache: bool = True,
    clear_cache: bool = False
) -> Dict[str, List[Document]]:
    """
    Parse PDF files dengan caching untuk optimasi biaya LlamaParse.
    
    Args:
        use_cache: Gunakan cache jika ada (default True)
        clear_cache: Hapus cache lama sebelum parse (default False)
    
    Returns:
        Dict regulator -> List of Documents
    """
    pdf_files = glob.glob(str(RAW_DATA_DIR / "*.pdf"))

    if not pdf_files:
        print(f"Tidak ada file PDF ditemukan di {RAW_DATA_DIR}")
        sys.exit(1)

    print(f"\nDitemukan {len(pdf_files)} file PDF:")
    for f in pdf_files:
        print(f"   -> {os.path.basename(f)}")

    # Initialize cache
    cache = get_cache()
    
    if clear_cache:
        print("\n[MENGHAPUS CACHE LAMA]")
        cache.clear()
    
    # Check cache stats
    stats = cache.get_stats()
    print(f"\nCache stats: {stats['total_entries']} files, {stats['total_pages_cached']} pages")
    print(f"Estimated savings: ${stats['estimated_savings_usd']}")

    parser = LlamaParse(
        api_key=LLAMA_CLOUD_API_KEY or "",
        result_type="markdown",
        verbose=True,
        language="id",
        num_workers=4,  # Parallel parsing
    )

    documents_by_regulator: Dict[str, List[Document]] = {}
    cached_count = 0
    parsed_count = 0
    saved_cost = 0.0

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"\nMemproses: {filename}...")

        regulator = detect_regulator(filename)
        if regulator == "Unknown":
            print(f"   Lewati {filename} (regulator tidak terdeteksi)")
            continue

        # Check cache first
        if use_cache:
            cached_docs = cache.get(pdf_path)
            if cached_docs:
                print(f"   [CACHE HIT] {len(cached_docs)} halaman dari cache")
                cached_count += len(cached_docs)
                
                # Convert cached docs back to Document objects
                for doc_dict in cached_docs:
                    doc = Document(
                        text=doc_dict["text"],
                        metadata=doc_dict["metadata"]
                    )
                    if regulator not in documents_by_regulator:
                        documents_by_regulator[regulator] = []
                    documents_by_regulator[regulator].append(doc)
                continue

        # Parse PDF (costs money)
        print(f"   [PARSING] Menggunakan LlamaParse API...")
        docs = parser.load_data(pdf_path)
        parsed_count += len(docs)

        # Save to cache
        if use_cache:
            cache.set(pdf_path, docs, metadata={"regulator": regulator})
            saved_cost += len(docs) * 0.003  # Estimasi hemat

        for doc in docs:
            doc.metadata["source_file"] = filename
            doc.metadata["regulator"] = regulator

        if regulator not in documents_by_regulator:
            documents_by_regulator[regulator] = []
        documents_by_regulator[regulator].extend(docs)

        print(f"   [OK] {len(docs)} halaman dari {filename} ({regulator})")

    # Summary
    print(f"\n{'='*60}")
    print("RINGKASAN PARSING:")
    print(f"{'='*60}")
    print(f"   Dari cache: {cached_count} halaman")
    print(f"   Baru diparse: {parsed_count} halaman")
    print(f"   Estimasi hemat: ${saved_cost:.4f}")
    
    for regulator, docs in documents_by_regulator.items():
        print(f"\n[{regulator}] Total: {len(docs)} halaman")

    return documents_by_regulator


def chunk_documents(documents: List[Document]) -> List:
    print("\nMelakukan Hierarchical Chunking (berbasis heading Markdown)...")

    node_parser = MarkdownNodeParser()
    nodes = node_parser.get_nodes_from_documents(documents)

    print(f"   [OK] Dihasilkan {len(nodes)} chunks")

    if nodes:
        print("\nPratinjau 3 chunks pertama:")
        for i, node in enumerate(nodes[:3]):
            preview = node.get_content()[:150].replace("\n", " ")
            regulator = node.metadata.get("regulator", "N/A")
            print(f"   [{i+1}] ({regulator}) {preview}...")

    return nodes


def build_separate_vector_stores(
    documents_by_regulator: Dict[str, List[Document]],
    force_rebuild: bool = False
) -> Dict[str, VectorStoreIndex]:
    """
    Build or load existing vector stores.
    
    Args:
        documents_by_regulator: Documents grouped by regulator
        force_rebuild: If True, rebuild all collections. If False, skip existing.
    """
    print(f"\nMenyimpan vektor ke ChromaDB (separate collections)...")

    db = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    indices = {}

    for regulator, documents in documents_by_regulator.items():
        collection_name = COLLECTION_NAMES.get(regulator)
        if not collection_name:
            print(f"   [Lewati] {regulator} (tidak ada collection mapping)")
            continue

        print(f"\n[{regulator}] -> Collection: {collection_name}")

        # CHECK: Skip if collection already has data (HEMAT USAGE!)
        try:
            existing_collection = db.get_collection(collection_name)
            existing_count = existing_collection.count()
            
            if existing_count > 0 and not force_rebuild:
                print(f"   [SKIP] Collection sudah ada dengan {existing_count} vektor.")
                print(f"   Gunakan --force untuk rebuild, atau lanjut ke tahap audit.")
                
                vector_store = ChromaVectorStore(chroma_collection=existing_collection)
                index = VectorStoreIndex.from_vector_store(vector_store)
                indices[regulator] = index
                continue
        except Exception:
            pass  # Collection doesn't exist, proceed with ingestion

        nodes = chunk_documents(documents)

        collection = db.get_or_create_collection(collection_name)
        
        # Delete old data if force_rebuild
        if force_rebuild:
            try:
                db.delete_collection(collection_name)
                collection = db.get_or_create_collection(collection_name)
            except Exception:
                pass

        vector_store = ChromaVectorStore(chroma_collection=collection)
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        print(f"   Proses embedding {len(nodes)} nodes...")
        index = VectorStoreIndex(
            nodes=nodes,
            storage_context=storage_context,
            show_progress=True,
        )

        indices[regulator] = index
        doc_count = collection.count()
        print(f"   [OK] {doc_count} vektor tersimpan di {collection_name}")

    print(f"\nDatabase tersimpan di: {CHROMA_DB_DIR}")
    return indices


def print_summary(indices: Dict[str, VectorStoreIndex]):
    print("\n" + "=" * 60)
    print("RINGKASAN INGESTION")
    print("=" * 60)

    db = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    total_vectors = 0
    for regulator, collection_name in COLLECTION_NAMES.items():
        try:
            collection = db.get_collection(collection_name)
            count = collection.count()
            total_vectors += count
            print(f"   [{regulator}] {collection_name}: {count} vektor")
        except Exception:
            print(f"   [{regulator}] {collection_name}: (kosong)")

    print("-" * 60)
    print(f"   Total: {total_vectors} vektor regulasi")
    print("=" * 60)


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="NLP Compliance Auditor - Data Ingestion")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild all collections (menggunakan LlamaParse API)"
    )
    parser.add_argument(
        "--skip-cache",
        action="store_true",
        help="Skip LlamaParse cache, re-parse all PDFs"
    )
    parser.add_argument(
        "--clear-cache",
        action="store_true",
        help="Clear LlamaParse cache before parsing"
    )
    parser.add_argument(
        "--cache-stats",
        action="store_true",
        help="Show cache statistics and exit"
    )
    args = parser.parse_args()
    
    print("=" * 60)
    print("NLP Compliance Auditor - Multi-Agent Data Ingestion")
    print("=" * 60)
    
    # Show cache stats if requested
    if args.cache_stats:
        cache = get_cache()
        stats = cache.get_stats()
        print(f"\nCache Statistics:")
        print(f"   Directory: {stats['cache_dir']}")
        print(f"   Total entries: {stats['total_entries']}")
        print(f"   Total pages cached: {stats['total_pages_cached']}")
        print(f"   Estimated savings: ${stats['estimated_savings_usd']}")
        print(f"\nCached files:")
        for entry in stats['entries']:
            print(f"   - {entry['file']}: {entry['pages']} pages")
        return
    
    if args.force:
        print("\n[MODE: FORCE REBUILD]")
        print("Semua collection akan di-rebuild dari awal.")
        print("Ini akan menggunakan quota LlamaParse API Anda!")
        print("-" * 60)

    if args.skip_cache:
        print("\n[MODE: SKIP CACHE]")
        print("Cache akan di-skip, semua PDF akan di-parse ulang.")
        print("-" * 60)

    documents_by_regulator = parse_pdfs(
        use_cache=not args.skip_cache,
        clear_cache=args.clear_cache
    )

    if not documents_by_regulator:
        print("\nTidak ada dokumen yang berhasil diproses!")
        sys.exit(1)

    indices = build_separate_vector_stores(
        documents_by_regulator, 
        force_rebuild=args.force
    )

    print_summary(indices)

    print("\nPipeline Ingestion Selesai!")
    print("Langkah selanjutnya: Jalankan 'python src/agents/run_audit.py'")


if __name__ == "__main__":
    main()