"""
ingest.py — Data Ingestion Pipeline untuk NLP Compliance Auditor
================================================================
Skrip ini membaca file PDF regulasi (PBI dan POJK), mengekstrak teksnya
menggunakan LlamaParse, melakukan chunking, mengubahnya menjadi embedding
vektor, lalu menyimpannya ke ChromaDB lokal.

Cara pakai:
    cd nlp-compliance-rag
    source venv/bin/activate
    python src/ingest.py
"""

import os
import sys
import glob
from pathlib import Path
from dotenv import load_dotenv

# ── 0. Load env & validasi ──────────────────────────────────────────
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-proj-xxx"):
    print("❌ OPENAI_API_KEY belum diisi di file .env!")
    sys.exit(1)
if not LLAMA_CLOUD_API_KEY or LLAMA_CLOUD_API_KEY.startswith("llx-xxx"):
    print("❌ LLAMA_CLOUD_API_KEY belum diisi di file .env!")
    sys.exit(1)

# ── 1. Import library ──────────────────────────────────────────────
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

# ── 2. Konfigurasi path ────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw"
CHROMA_DB_DIR = BASE_DIR / "data" / "processed" / "chroma_db"

# ── 3. Setup komponen global LlamaIndex ─────────────────────────────
print("🔧 Mengkonfigurasi LlamaIndex Settings...")

# Model Embedding: OpenAI text-embedding-3-large (terbaik untuk semantik hukum)
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-large",
    api_key=OPENAI_API_KEY,
)

# LLM: GPT-4o digunakan nanti untuk klasifikasi kepatuhan (audit.py)
Settings.llm = OpenAI(
    model="gpt-4o",
    api_key=OPENAI_API_KEY,
    temperature=0.1,  # Suhu rendah = jawaban konsisten & tidak kreatif
)

# Chunk size & overlap untuk node parser
Settings.chunk_size = 1024
Settings.chunk_overlap = 128

print("✅ Embedding: text-embedding-3-large")
print("✅ LLM: GPT-4o (temperature=0.1)")


def parse_pdfs() -> list[Document]:
    """
    Tahap 1: Ekstraksi PDF → Markdown menggunakan LlamaParse.
    LlamaParse unggul dalam membaca PDF format regulasi yang punya:
    - Tabel dua kolom
    - Daftar nomor/ayat bertingkat (Pasal 1 ayat (1) huruf a)
    - Header/footer halaman berulang
    """
    pdf_files = glob.glob(str(RAW_DATA_DIR / "*.pdf"))

    if not pdf_files:
        print(f"❌ Tidak ada file PDF ditemukan di {RAW_DATA_DIR}")
        sys.exit(1)

    print(f"\n📄 Ditemukan {len(pdf_files)} file PDF:")
    for f in pdf_files:
        print(f"   → {os.path.basename(f)}")

    # Konfigurasi LlamaParse
    parser = LlamaParse(
        api_key=LLAMA_CLOUD_API_KEY,
        result_type="markdown",  # Output sebagai Markdown agar struktur BAB/Pasal terbaca
        verbose=True,
        language="id",  # Bahasa Indonesia
    )

    all_documents = []
    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        print(f"\n🔍 Memproses: {filename}...")

        # Tentukan sumber regulasi dari nama file
        if "PBI" in filename.upper():
            source_regulator = "Bank Indonesia (BI)"
        elif "POJK" in filename.upper() or "OJK" in filename.upper():
            source_regulator = "Otoritas Jasa Keuangan (OJK)"
        else:
            source_regulator = "Unknown"

        docs = parser.load_data(pdf_path)

        # Tambahkan metadata ke setiap dokumen
        for doc in docs:
            doc.metadata["source_file"] = filename
            doc.metadata["regulator"] = source_regulator

        all_documents.extend(docs)
        print(f"   ✅ Berhasil mengekstrak {len(docs)} halaman dari {filename}")

    print(f"\n📊 Total dokumen diekstrak: {len(all_documents)} halaman")
    return all_documents


def chunk_documents(documents: list[Document]):
    """
    Tahap 2: Hierarchical Chunking berbasis Markdown.
    Karena LlamaParse mengeluarkan output berformat Markdown (dengan heading #, ##, ###),
    MarkdownNodeParser akan memotong teks berdasarkan heading level.
    Ini jauh lebih cerdas daripada memotong berdasarkan jumlah karakter,
    karena setiap 'node' (potongan) akan berisi satu pasal/ayat utuh.
    """
    print("\n✂️  Melakukan Hierarchical Chunking (berbasis heading Markdown)...")

    node_parser = MarkdownNodeParser()
    nodes = node_parser.get_nodes_from_documents(documents)

    print(f"   ✅ Dihasilkan {len(nodes)} chunks (potongan pasal/ayat)")

    # Tampilkan 3 contoh node pertama untuk verifikasi
    print("\n📋 Pratinjau 3 chunks pertama:")
    for i, node in enumerate(nodes[:3]):
        preview = node.get_content()[:200].replace("\n", " ")
        regulator = node.metadata.get("regulator", "N/A")
        print(f"   [{i+1}] ({regulator}) {preview}...")

    return nodes


def build_vector_index(nodes):
    """
    Tahap 3: Vektorisasi & Penyimpanan ke ChromaDB.
    Setiap chunk pasal diubah menjadi vektor numerik oleh text-embedding-3-large,
    lalu disimpan secara persisten ke folder data/processed/chroma_db/.
    """
    print(f"\n💾 Menyimpan vektor ke ChromaDB di: {CHROMA_DB_DIR}")

    # Inisialisasi ChromaDB lokal (persisten di disk M1 Pro)
    db = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    chroma_collection = db.get_or_create_collection("regulations_bi_ojk_v1")
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    # Bangun index dari nodes (embedding otomatis dilakukan di sini)
    print("⏳ Proses embedding sedang berjalan (membutuhkan beberapa menit)...")
    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        show_progress=True,
    )

    doc_count = chroma_collection.count()
    print(f"\n🎉 SUKSES! {doc_count} vektor pasal/ayat tersimpan di ChromaDB.")
    print(f"   Database tersimpan di: {CHROMA_DB_DIR}")
    return index


def main():
    print("=" * 60)
    print("🏛️  NLP Compliance Auditor — Data Ingestion Pipeline")
    print("=" * 60)

    # Tahap 1: Parse PDF
    documents = parse_pdfs()

    # Tahap 2: Chunk Documents
    nodes = chunk_documents(documents)

    # Tahap 3: Build Vector Index
    index = build_vector_index(nodes)

    print("\n" + "=" * 60)
    print("✅ Pipeline Ingestion Selesai!")
    print("   Langkah selanjutnya: Jalankan 'python src/audit.py'")
    print("=" * 60)


if __name__ == "__main__":
    main()
