"""
audit_md.py — Full Markdown NLP Compliance Auditor
=====================================================
Skrip ini membaca dokumen berformat Markdown (.md) secara penuh,
mengubahnya menjadi potongan klausa (chunks), 
dan mengevaluasi setiap chunk ke database ChromaDB (Regulasi).
Sangat efisien karena tidak memerlukan ekstraksi OCR dari LlamaParse.
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
from llama_index.core import Document
from llama_index.core.node_parser import MarkdownNodeParser
from audit import load_index, audit_clause

BASE_DIR = Path(__file__).resolve().parent.parent

def parse_and_chunk_md(md_path: str):
    print(f"\n📄 Membaca dokumen Markdown: {os.path.basename(md_path)}...")
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    doc = Document(text=content)
    
    print("\n✂️  Melakukan Chunking (Memecah menjadi klausa)...")
    node_parser = MarkdownNodeParser()
    nodes = node_parser.get_nodes_from_documents([doc])
    
    print(f"   ✅ Dihasilkan {len(nodes)} klausul yang akan diaudit.")
    return nodes

def analyze_full_md(md_path: str):
    print("=" * 60)
    print("🤖  NLP Compliance Auditor — FULL MARKDOWN SCAN")
    print("=" * 60)
    
    # 1. Pastikan file ada
    if not os.path.exists(md_path):
        print(f"❌ File tidak ditemukan: {md_path}")
        sys.exit(1)
        
    # 2. Muat basis pengetahuan (BI & OJK)
    try:
        index = load_index()
    except Exception as e:
        print(f"Gagal memuat index: {e}")
        sys.exit(1)
        
    # 3. Ekstrak SOP Target
    nodes = parse_and_chunk_md(md_path)
    
    print(f"\n🔍 Mengaudit SELURUH ({len(nodes)}) klausa dari dokumen Dummy...\n")

    # 4. Audit per klausa
    results = []
    output_path = BASE_DIR / "data" / "processed" / "report_audit_dummy_full.txt"
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"LAPORAN AUDIT DOKUMEN: {os.path.basename(md_path)}\n")
        f.write("=" * 60 + "\n\n")
        
        for i, node in enumerate(nodes):
            clause_text = node.get_content().strip()
            
            # Skip jika terlalu pendek (seperti judul tunggal)
            if len(clause_text) < 30:
                continue
                
            print("-" * 60)
            print(f"Mengaudit Klausa [{i+1}/{len(nodes)}]...")
            print(f"   Cuplikan: \"{clause_text[:100].replace(chr(10), ' ')}...\"")
            
            result = audit_clause(index, clause_text)
            print("   ✅ Selesai dinilai.")
            
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
        print("Penggunaan: python src/audit_md.py \"/path/ke/file.md\"")
        sys.exit(1)
        
    target_md = sys.argv[1]
    analyze_full_md(target_md)
