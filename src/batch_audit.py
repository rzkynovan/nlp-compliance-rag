"""
batch_audit.py — Batch Audit Runner untuk Multi-Agent Compliance Auditor
==========================================================================
Menjalankan audit batch untuk beberapa file SOP/T&C sekaligus
dan menghasilkan laporan evaluasi.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from agents.coordinator import CoordinatorAgent
from evaluation import ComplianceEvaluator, SOP_DUMMY_EXPECTED


BASE_DIR = Path(__file__).resolve().parent.parent
SOP_DIR = BASE_DIR.parent  # Parent folder (Tugas Akhir)
OUTPUT_DIR = BASE_DIR / "data" / "audit_results"


async def run_audit_on_file(
    coordinator: CoordinatorAgent,
    file_path: str,
    output_name: str
) -> Dict:
    """
    Run audit on a single file and save results.
    """
    print(f"\n{'='*60}")
    print(f"AUDIT FILE: {Path(file_path).name}")
    print(f"{'='*60}")
    
    file_path = Path(file_path)
    
    if file_path.suffix == ".md":
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse SOP structure - extract clauses from each BAB section
        clauses = []
        current_section = None
        clause_counter = 0
        
        lines = content.split('\n')
        current_clause_text = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Detect BAB sections
            if line_stripped.startswith('## BAB'):
                # Save previous clause if exists
                if current_clause_text and current_section:
                    clause_text = '\n'.join(current_clause_text).strip()
                    if len(clause_text) >= 30:
                        clause_counter += 1
                        clauses.append({
                            "id": f"KLAUSA-{clause_counter}",
                            "text": clause_text,
                            "section": current_section
                        })
                
                current_section = line_stripped.replace('##', '').strip()
                current_clause_text = []
            
            # Detect numbered clauses (1., 2., etc.)
            elif line_stripped and line_stripped[0].isdigit() and '. ' in line_stripped[:5]:
                # Save previous clause if exists
                if current_clause_text:
                    clause_text = '\n'.join(current_clause_text).strip()
                    if len(clause_text) >= 30:
                        clause_counter += 1
                        clauses.append({
                            "id": f"KLAUSA-{clause_counter}",
                            "text": clause_text,
                            "section": current_section or "PENDAHULUAN"
                        })
                
                current_clause_text = [line_stripped]
            
            # Continue adding to current clause
            elif line_stripped and not line_stripped.startswith('---') and not line_stripped.startswith('**('):
                current_clause_text.append(line_stripped)
        
        # Don't forget the last clause
        if current_clause_text and current_section:
            clause_text = '\n'.join(current_clause_text).strip()
            if len(clause_text) >= 30:
                clause_counter += 1
                clauses.append({
                    "id": f"KLAUSA-{clause_counter}",
                    "text": clause_text,
                    "section": current_section
                })
        
        # If no clauses found, fall back to line-by-line
        if not clauses:
            for i, line in enumerate(content.split('\n\n')):
                line = line.strip()
                if len(line) >= 30:
                    clauses.append({
                        "id": f"CLAUSE-{i+1}",
                        "text": line[:1000],
                        "section": None
                    })
    
    elif file_path.suffix == ".pdf":
        print("PDF files require LlamaParse API usage.")
        print("Skipping PDF for now - use audit_pdf.py separately.")
        return {"status": "skipped", "reason": "PDF requires separate processing"}
    
    else:
        print(f"Unsupported file format: {file_path.suffix}")
        return {"status": "error", "reason": "Unsupported format"}
    
    print(f"Found {len(clauses)} clauses to audit")
    
    # Run audit
    results = await coordinator.audit_document_async(clauses=clauses)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"{output_name}_{timestamp}.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        "source_file": str(file_path),
        "audit_timestamp": timestamp,
        "total_clauses": len(results),
        "results": [r.to_dict() for r in results]
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    
    return {
        "status": "success",
        "output_file": str(output_file),
        "total_clauses": len(results)
    }


def run_evaluation(results_file: str, expected_labels: Dict[str, str] = None):
    """
    Run evaluation on audit results.
    """
    print(f"\n{'='*60}")
    print("EVALUATION")
    print(f"{'='*60}")
    
    evaluator = ComplianceEvaluator()
    evaluator.load_results_from_file(results_file)
    
    # Apply expected labels
    if expected_labels:
        for result in evaluator.results:
            clause_id = result.get("clause_id", "")
            if clause_id in expected_labels:
                result["expected"] = expected_labels[clause_id]
    
    # Generate reports
    report_path = Path(results_file).with_suffix(".evaluation.md")
    metrics_path = Path(results_file).with_suffix(".metrics.json")
    
    evaluator.generate_report(str(report_path))
    evaluator.save_metrics_json(str(metrics_path))
    
    # Print summary
    metrics = evaluator.calculate_metrics()
    print(f"\nSUMMARY:")
    print(f"  Total Samples: {metrics['OVERALL']['Total_Samples']}")
    print(f"  Accuracy: {metrics['OVERALL']['Accuracy']*100:.2f}%")
    print(f"  Macro F1-Score: {metrics['MACRO_AVG']['F1-Score']:.4f}")
    
    return evaluator


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Batch Audit Runner")
    parser.add_argument("--sop-dummy", action="store_true", help="Audit SOP Dummy file")
    parser.add_argument("--gopay", action="store_true", help="Audit GoPay T&C file")
    parser.add_argument("--all", action="store_true", help="Audit all files")
    parser.add_argument("--evaluate", action="store_true", help="Run evaluation after audit")
    
    args = parser.parse_args()
    
    # Initialize coordinator
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key or openai_key.startswith("sk-proj-xxx"):
        print("Error: OPENAI_API_KEY belum diisi di file .env!")
        sys.exit(1)
    
    chroma_path = str(BASE_DIR / "data" / "processed" / "chroma_db")
    
    coordinator = CoordinatorAgent()
    coordinator.initialize(api_key=openai_key, chroma_path=chroma_path)
    
    # Files to audit
    files_to_audit = []
    
    if args.all or args.sop_dummy:
        sop_dummy = SOP_DIR / "SOP_Dummy_EWallet_Palsu.md"
        if sop_dummy.exists():
            files_to_audit.append((str(sop_dummy), "sop_dummy"))
        else:
            print(f"File not found: {sop_dummy}")
    
    if args.all or args.gopay:
        gopay = SOP_DIR / "Syarat dan Ketentuan GoPay.pdf"
        if gopay.exists():
            files_to_audit.append((str(gopay), "gopay_tc"))
        else:
            print(f"File not found: {gopay}")
    
    if not files_to_audit:
        print("No files to audit. Use --sop-dummy, --gopay, or --all")
        print("\nUsage:")
        print("  python batch_audit.py --sop-dummy      # Audit SOP Dummy")
        print("  python batch_audit.py --gopay           # Audit GoPay T&C (PDF)")
        print("  python batch_audit.py --all            # Audit all files")
        print("  python batch_audit.py --all --evaluate  # Audit and evaluate")
        sys.exit(0)
    
    # Run audits
    audit_results = []
    
    for file_path, output_name in files_to_audit:
        result = await run_audit_on_file(coordinator, file_path, output_name)
        audit_results.append((result, output_name))
    
    # Run evaluation if requested
    if args.evaluate:
        for result, output_name in audit_results:
            if result.get("status") == "success":
                run_evaluation(
                    result["output_file"],
                    expected_labels=SOP_DUMMY_EXPECTED if "sop" in output_name else None
                )
    
    print("\n" + "="*60)
    print("BATCH AUDIT COMPLETED")
    print("="*60)
    for result, output_name in audit_results:
        status = result.get("status", "unknown")
        print(f"  {output_name}: {status}")
        if status == "success":
            print(f"    Clauses: {result.get('total_clauses', 'N/A')}")
            print(f"    Output: {result.get('output_file', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())