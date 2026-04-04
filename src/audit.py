"""
audit.py — NLP Compliance Auditor (RAG Query Engine)
=====================================================
Skrip ini menerima input teks klausa SOP / Syarat & Ketentuan,
lalu mencocokkannya dengan database regulasi BI/OJK di ChromaDB,
dan mengeluarkan penilaian kepatuhan (Compliant / Non-Compliant / Not Addressed).

Cara pakai:
    cd nlp-compliance-rag
    source venv/bin/activate
    python src/audit.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY or OPENAI_API_KEY.startswith("sk-proj-xxx"):
    print("❌ OPENAI_API_KEY belum diisi di file .env!")
    sys.exit(1)

from llama_index.core import VectorStoreIndex, Settings
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI
from llama_index.vector_stores.chroma import ChromaVectorStore
import chromadb

# ── Konfigurasi Path ───────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DB_DIR = BASE_DIR / "data" / "processed" / "chroma_db"

# ── Setup LlamaIndex Settings ─────────────────────────────────────
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-large",
    api_key=OPENAI_API_KEY,
)
Settings.llm = OpenAI(
    model="gpt-4o",
    api_key=OPENAI_API_KEY,
    temperature=0.1,
)

# ── Prompt Template untuk Audit Kepatuhan ──────────────────────────
COMPLIANCE_AUDIT_PROMPT = """
Kamu adalah seorang Auditor Kepatuhan Regulasi (Compliance Auditor) yang ahli dalam regulasi perbankan dan keuangan Indonesia (Bank Indonesia dan OJK).

Kamu diberikan:
1. Sebuah KLAUSA dari dokumen SOP / Syarat dan Ketentuan internal sebuah perusahaan E-Wallet.
2. Beberapa PASAL REGULASI yang relevan dari database PBI (Peraturan Bank Indonesia) dan POJK (Peraturan OJK).

TUGASMU:
Bandingkan klausa SOP tersebut dengan pasal-pasal regulasi yang diberikan.
Tentukan status kepatuhannya dan berikan analisis.

FORMAT JAWABAN (WAJIB diikuti):
---
**STATUS:** [COMPLIANT / NON-COMPLIANT / NOT ADDRESSED]
**REGULATOR:** [Bank Indonesia (BI) / OJK / Keduanya]
**TINGKAT RISIKO:** [RENDAH / SEDANG / TINGGI / KRITIS]
**PASAL TERKAIT:** [Sebutkan nomor pasal/ayat regulasi yang relevan]

**ANALISIS:**
[Jelaskan mengapa klausa SOP ini dianggap patuh/tidak patuh/belum diatur
berdasarkan pasal regulasi yang ditemukan. Gunakan bahasa Indonesia formal.]

**REKOMENDASI:**
[Jika Non-Compliant, berikan saran perbaikan spesifik agar klausa SOP
menjadi patuh terhadap regulasi. Jika Compliant, cukup tulis "Tidak ada
rekomendasi. Klausa sudah sesuai regulasi."]
---
"""


def load_index():
    """Muat index dari ChromaDB yang sudah di-ingest sebelumnya."""
    if not CHROMA_DB_DIR.exists():
        print("❌ Database ChromaDB belum ditemukan!")
        print("   Jalankan 'python src/ingest.py' terlebih dahulu.")
        sys.exit(1)

    db = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    chroma_collection = db.get_or_create_collection("regulations_bi_ojk_v1")

    doc_count = chroma_collection.count()
    if doc_count == 0:
        print("❌ ChromaDB kosong! Belum ada data regulasi yang di-ingest.")
        sys.exit(1)

    print(f"✅ ChromaDB dimuat: {doc_count} vektor regulasi tersedia.")

    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)
    index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
    return index


def audit_clause(index, clause_text: str) -> str:
    """
    Lakukan audit kepatuhan terhadap satu klausa SOP.
    Menggunakan RAG: retrieve pasal relevan, lalu classify via GPT-4o.
    """
    query_engine = index.as_query_engine(
        similarity_top_k=5,  # Ambil 5 pasal paling relevan
        system_prompt=COMPLIANCE_AUDIT_PROMPT,
    )

    query = f"""
Analisis klausa SOP/T&C berikut ini terhadap regulasi BI dan OJK yang tersedia:

KLAUSA SOP:
\"{clause_text}\"

Berikan penilaian kepatuhan sesuai format yang diminta.
"""
    response = query_engine.query(query)
    return str(response)


# ── Contoh Klausa Uji (dari SOP Dummy kita) ───────────────────────
SAMPLE_CLAUSES = [
    {
        "id": "KLAUSA-01",
        "sumber": "SOP Dummy NusantaraPay — Bab II (Seharusnya COMPLIANT)",
        "teks": "Perusahaan wajib memperoleh persetujuan tertulis atau persetujuan elektronik (explicit consent) dari Nasabah sebelum mengumpulkan dan memproses Data Pribadi.",
    },
    {
        "id": "KLAUSA-02",
        "sumber": "SOP Dummy NusantaraPay — Bab III (Seharusnya NON-COMPLIANT)",
        "teks": "Tim Customer Service memiliki waktu maksimal 60 hari kerja sejak keluhan diterima untuk menyelesaikan masalah nasabah dan memberikan kompensasi.",
    },
    {
        "id": "KLAUSA-03",
        "sumber": "SOP Dummy NusantaraPay — Bab IV (Seharusnya NON-COMPLIANT)",
        "teks": "Nasabah yang belum mengunggah KTP (Unregistered) dapat menyimpan saldo maksimal hingga Rp 10.000.000 (Sepuluh Juta Rupiah).",
    },
    {
        "id": "KLAUSA-04",
        "sumber": "SOP Dummy NusantaraPay — Bab IV (Seharusnya NON-COMPLIANT)",
        "teks": "Batas transaksi masuk bulanan (Monthly Incoming Limit) untuk semua pengguna tidak dibatasi untuk mendorong pertumbuhan Gross Transaction Value (GTV) perusahaan.",
    },
]


def main():
    print("=" * 60)
    print("🏛️  NLP Compliance Auditor — Audit Engine")
    print("=" * 60)

    index = load_index()

    print(f"\n📝 Menjalankan audit terhadap {len(SAMPLE_CLAUSES)} klausa uji...\n")

    results = []
    for clause in SAMPLE_CLAUSES:
        print("-" * 60)
        print(f"🔎 [{clause['id']}] {clause['sumber']}")
        print(f"   Klausa: \"{clause['teks'][:80]}...\"")
        print()

        result = audit_clause(index, clause["teks"])
        print(result)
        print()

        results.append({
            "id": clause["id"],
            "sumber": clause["sumber"],
            "klausa": clause["teks"],
            "hasil_audit": result,
        })

    # Simpan hasil ke file teks
    output_path = BASE_DIR / "data" / "processed" / "hasil_audit.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("HASIL AUDIT KEPATUHAN REGULASI\n")
        f.write("=" * 60 + "\n\n")
        for r in results:
            f.write(f"[{r['id']}] {r['sumber']}\n")
            f.write(f"Klausa: {r['klausa']}\n\n")
            f.write(f"{r['hasil_audit']}\n")
            f.write("-" * 60 + "\n\n")

    print("=" * 60)
    print(f"✅ Audit selesai! Hasil disimpan di: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
