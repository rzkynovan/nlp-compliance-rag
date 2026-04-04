"""
run_audit.py — Multi-Agent Compliance Auditor Runner
======================================================
Script utama untuk menjalankan sistem multi-agent audit.

Cara pakai:
    cd nlp-compliance-rag
    source venv/bin/activate
    python src/agents/run_audit.py

Atau untuk audit file:
    python src/agents/run_audit.py --file path/to/document.md
"""

import os
import sys
import argparse
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))

from agents.coordinator import CoordinatorAgent


SAMPLE_CLAUSES = [
    {
        "id": "KLAUSA-01",
        "text": "Perusahaan wajib memperoleh persetujuan tertulis atau persetujuan elektronik (explicit consent) dari Nasabah sebelum mengumpulkan dan memproses Data Pribadi.",
        "expected": "COMPLIANT"
    },
    {
        "id": "KLAUSA-02",
        "text": "Tim Customer Service memiliki waktu maksimal 60 hari kerja sejak keluhan diterima untuk menyelesaikan masalah nasabah dan memberikan kompensasi.",
        "expected": "NON-COMPLIANT"
    },
    {
        "id": "KLAUSA-03",
        "text": "Nasabah yang belum mengunggah KTP (Unregistered) dapat menyimpan saldo maksimal hingga Rp 10.000.000 (Sepuluh Juta Rupiah).",
        "expected": "NON-COMPLIANT"
    },
    {
        "id": "KLAUSA-04",
        "text": "Batas transaksi masuk bulanan (Monthly Incoming Limit) untuk semua pengguna tidak dibatasi untuk mendorong pertumbuhan Gross Transaction Value (GTV) perusahaan.",
        "expected": "NON-COMPLIANT"
    },
]


def main():
    parser = argparse.ArgumentParser(description="Multi-Agent NLP Compliance Auditor")
    parser.add_argument(
        "--file",
        type=str,
        help="Path to document file (Markdown or PDF)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path for results (JSON)"
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Run with sample clauses for demo"
    )
    
    args = parser.parse_args()
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key or openai_key.startswith("sk-proj-xxx"):
        print("Error: OPENAI_API_KEY belum diisi di file .env!")
        sys.exit(1)
    
    chroma_path = str(BASE_DIR / "data" / "processed" / "chroma_db")
    
    coordinator = CoordinatorAgent()
    coordinator.initialize(api_key=openai_key, chroma_path=chroma_path)
    
    if args.sample:
        print("\n" + "=" * 60)
        print("MULTI-AGENT COMPLIANCE AUDIT - DEMO MODE")
        print("=" * 60)
        print("Menjalankan audit dengan klausa contoh...")
        
        results = asyncio.run(coordinator.audit_document_async(
            clauses=SAMPLE_CLAUSES,
            output_path=args.output
        ))
        
        print("\n" + "=" * 60)
        print("HASIL AUDIT")
        print("=" * 60)
        
        for result in results:
            print(f"\n[{result.clause_id}]")
            print(f"Klausa: {result.clause_text[:80]}...")
            print(f"Status: {result.final_verdict.final_status}")
            print(f"Confidence: {result.final_verdict.overall_confidence:.2f}")
            print(f"Risk: {result.final_verdict.risk_score}")
            
            if result.final_verdict.recommendations:
                print("Rekomendasi:")
                for rec in result.final_verdict.recommendations[:3]:
                    print(f"  - {rec}")
        
        report = coordinator.generate_report(results)
        print("\n" + report)
        
        if args.output:
            report_path = Path(args.output).with_suffix(".txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"\nLaporan disimpan di: {report_path}")
    
    elif args.file:
        print(f"\nMenjalankan audit untuk file: {args.file}")
        
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File tidak ditemukan: {args.file}")
            sys.exit(1)
        
        if file_path.suffix == ".md":
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            clauses = []
            for i, line in enumerate(content.split("\n\n")):
                line = line.strip()
                if len(line) > 30:
                    clauses.append({
                        "id": f"KLAUSA-{i+1}",
                        "text": line
                    })
            
            print(f"Ditemukan {len(clauses)} klausa dalam file.")
            
            results = asyncio.run(coordinator.audit_document_async(
                clauses=clauses,
                output_path=args.output
            ))
            
            report = coordinator.generate_report(results)
            print(report)
        
        else:
            print(f"Error: Format file tidak didukung: {file_path.suffix}")
            sys.exit(1)
    
    else:
        print("\n" + "=" * 60)
        print("MULTI-AGENT COMPLIANCE AUDIT - INTERACTIVE MODE")
        print("=" * 60)
        print("Ketik klausa untuk diaudit, atau 'quit' untuk keluar.")
        
        while True:
            print("\n" + "-" * 60)
            clause = input("Masukkan klausa SOP/T&C: ").strip()
            
            if clause.lower() in ["quit", "exit", "q"]:
                break
            
            if len(clause) < 20:
                print("Klausa terlalu pendek. Minimal 20 karakter.")
                continue
            
            result = coordinator.audit_clause(clause)
            
            print(f"\n{'='*60}")
            print("HASIL AUDIT")
            print("="*60)
            print(f"Status: {result.final_verdict.final_status}")
            print(f"Confidence: {result.final_verdict.overall_confidence:.2f}")
            print(f"Risk Level: {result.final_verdict.risk_score}")
            print(f"\n[BI] {result.bi_verdict.get('verdict', 'N/A')} (confidence: {result.bi_verdict.get('confidence_score', 0):.2f})")
            print(f"[OJK] {result.ojk_verdict.get('verdict', 'N/A')} (confidence: {result.ojk_verdict.get('confidence_score', 0):.2f})")
            
            if result.final_verdict.recommendations:
                print("\nRekomendasi:")
                for rec in result.final_verdict.recommendations[:3]:
                    print(f"  - {rec}")
        
        print("\nTerima kasih telah menggunakan Multi-Agent Compliance Auditor!")


if __name__ == "__main__":
    main()