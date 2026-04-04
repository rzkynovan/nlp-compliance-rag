"""
audit_pdf.py — Full Document NLP Compliance Auditor
=====================================================
Skrip ini membaca dokumen PDF penuh (SOP / T&C),
mengubahnya menjadi potongan klausa (chunks), 
dan mengevaluasi setiap chunk ke database ChromaDB (Regulasi).
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
LLAMA_CLOUD_API_KEY = os.getenv("LLAMA_CLOUD_API_KEY")

from llama_parse import LlamaParse
from llama_index.core.node_parser import MarkdownNodeParser
from audit import load_index, audit_clause

BASE_DIR = Path(__file__).resolve().parent.parent

def parse_and_chunk_sop(pdf_path: str):
    """Membaca PDF T&C dan memecahnya menjadi potongan-potongan bernilai."""
    print(f"\n📄 Mengekstrak PDF: {os.path.basename(pdf_path)}...")
    parser = LlamaParse(
        api_key=LLAMA_CLOUD_API_KEY,
        result_type="markdown",
        verbose=True,
        language="id"
    )
    docs = parser.load_data(pdf_path)
    
    print("\n✂️  Melakukan Chunking (Memecah menjadi klausa)...")
    node_parser = MarkdownNodeParser()
    nodes = node_parser.get_nodes_from_documents(docs)
    
    print(f"   ✅ Dihasilkan {len(nodes)} klausul yang akan diaudit.")
    return nodes

def analyze_full_sop(pdf_path: str):
    print("=" * 60)
    print("🤖  NLP Compliance Auditor — FULL DOCUMENT SCAN")
    print("=" * 60)
    
    # 1. Pastikan file ada
    if not os.path.exists(pdf_path):
        print(f"❌ File tidak ditemukan: {pdf_path}")
        sys.exit(1)
        
    # 2. Muat basis pengetahuan (BI & OJK)
    try:
        index = load_index()
    except Exception as e:
        print(f"Gagal memuat index: {e}")
        sys.exit(1)
        
    # 3. Ekstrak SOP Target
    nodes = parse_and_chunk_sop(pdf_path)
    
    # Karena dokumen T&C penuh bisa menghasilkan ratusan klausa,
    # kita batasi analisa pada 10 klausa acak saja untuk demonstrasi agar tidak menghabiskan waktu/uang API.
    # Untuk skripsi penuh, loop ini dijalankan untuk semua 'nodes'.
    import random
    num_samples = min(5, len(nodes)) 
    print(f"\n🔍 [Mode Demo] Memilih {num_samples} klausa acak untuk diaudit agar hemat token LLM...\n")
    sample_nodes = random.sample(nodes, num_samples)

    # 4. Audit per klausa
    results = []
    output_path = BASE_DIR / "data" / "processed" / "report_audit_gopay_full.txt"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"LAPORAN AUDIT DOKUMEN: {os.path.basename(pdf_path)}\n")
        f.write("=" * 60 + "\n\n")
        
        for i, node in enumerate(sample_nodes):
            clause_text = node.get_content().strip()
            
            # Skip jika terlalu pendek (bukan klausul hukum yang utuh)
            if len(clause_text) < 50:
                continue
                
            print("-" * 60)
            print(f"Mengaudit Klausa [{i+1}/{num_samples}]...")
            print(f"   Cuplikan: \"{clause_text[:100]}...\"")
            
            result = audit_clause(index, clause_text)
            print(result)
            print()
            
            f.write(f"KLAUSA [{i+1}]:\n")
            f.write(f"Teks: {clause_text}\n\n")
            f.write("HASIL ANALISIS:\n")
            f.write(f"{result}\n")
            f.write("-" * 60 + "\n\n")

    print("=" * 60)
    print(f"✅ Scanning Selesai! Laporan disimpan di:\n   {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Penggunaan: python src/audit_pdf.py \"/path/ke/file.pdf\"")
        sys.exit(1)
        
    target_pdf = sys.argv[1]
    analyze_full_sop(target_pdf)
