"""
ingest.py — Data Ingestion Pipeline untuk Multi-Agent NLP Compliance Auditor
===================================================================================
Skrip ini membaca file PDF regulasi (PBI dan POJK), mengekstrak teksnya
menggunakan LlamaParse, melakukan chunking, dan menyimpannya keChromaDB
dengan SEPARATE COLLECTIONS per regulator (BI & OJK).

Struktur Collections:
- bi_regulations: Khusus regulasi Bank Indonesia
- ojk_regulations: Khusus regulasi Otoritas Jasa Keuangan
- pdp_regulations: Khusus UU Perlindungan Data Pribadi (opsional)

Cara pakai:
    cd nlp-compliance-rag
    source venv/bin/activate
    python src/ingest.py
"""

import os
import sys
import glob
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
    model="text-embedding-3-large",
    api_key=OPENAI_API_KEY,
)

Settings.llm = OpenAI(
    model="gpt-4o",
    api_key=OPENAI_API_KEY,
    temperature=0.1,
)

Settings.chunk_size = 1024
Settings.chunk_overlap = 128

print("Embedding: text-embedding-3-large")
print("LLM: GPT-4o (temperature=0.1)")


def detect_regulator(filename: str) -> str:
    filename_upper = filename.upper()
    for keyword, regulator in REGULATOR_MAPPING.items():
        if keyword in filename_upper:
            return regulator
    return "Unknown"


def parse_pdfs() -> Dict[str, List[Document]]:
    pdf_files = glob.glob(str(RAW_DATA_DIR / "*.pdf"))

    if not pdf_files:
        print(f"Tidak ada file PDF ditemukan di {RAW_DATA_DIR}")
        sys.exit(1)

    print(f"\nDitemukan {len(pdf_files)} file PDF:")
    for f in pdf_files:
        print(f"   -> {os.path.basename(f)}")

    parser = LlamaParse(
        api_key=LLAMA_CLOUD_API_KEY or "",
        result_type="markdown",
        verbose=True,
        language="id",
    )

    documents_by_regulator: Dict[str, List[Document]] = {}

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"\nMemproses: {filename}...")

        regulator = detect_regulator(filename)
        if regulator == "Unknown":
            print(f"   Lewati {filename} (regulator tidak terdeteksi)")
            continue

        docs = parser.load_data(pdf_path)

        for doc in docs:
            doc.metadata["source_file"] = filename
            doc.metadata["regulator"] = regulator

        if regulator not in documents_by_regulator:
            documents_by_regulator[regulator] = []
        documents_by_regulator[regulator].extend(docs)

        print(f"   [OK] {len(docs)} halaman dari {filename} ({regulator})")

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
    documents_by_regulator: Dict[str, List[Document]]
) -> Dict[str, VectorStoreIndex]:
    print(f"\nMenyimpan vektor ke ChromaDB (separate collections)...")

    db = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))

    indices = {}

    for regulator, documents in documents_by_regulator.items():
        collection_name = COLLECTION_NAMES.get(regulator)
        if not collection_name:
            print(f"   [Lewati] {regulator} (tidak ada collection mapping)")
            continue

        print(f"\n[{regulator}] -> Collection: {collection_name}")

        nodes = chunk_documents(documents)

        try:
            db.delete_collection(collection_name)
        except Exception:
            pass
        
        collection = db.get_or_create_collection(collection_name)

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
    print("=" * 60)
    print("NLP Compliance Auditor - Multi-Agent Data Ingestion")
    print("=" * 60)

    documents_by_regulator = parse_pdfs()

    if not documents_by_regulator:
        print("\nTidak ada dokumen yang berhasil diproses!")
        sys.exit(1)

    indices = build_separate_vector_stores(documents_by_regulator)

    print_summary(indices)

    print("\nPipeline Ingestion Selesai!")
    print("Langkah selanjutnya: Jalankan 'python src/agents/run_audit.py'")


if __name__ == "__main__":
    main()