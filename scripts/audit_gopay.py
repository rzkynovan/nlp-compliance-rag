"""
audit_gopay.py — Studi kasus R7: audit dokumen T&C GoPay tanpa UI (reprodusibel).

Alur identik dengan endpoint POST /audit/upload + /audit/analyze:
  1. Ekstraksi PDF dengan PyMuPDF (_extract_pdf_text_pymupdf)
  2. Segmentasi klausul (_split_into_clauses)
  3. Audit tiap klausul lewat RAGAuditService.analyze_with_rag
     (Gate Classifier + pre-filter + multi-agent RAG), cache dimatikan.

Run ditandai "invalid" bila ada klausul yang error atau jatuh ke mode llm_only
(fallback saat multi-agent gagal) — hasil semacam itu bukan evaluasi sistem RAG.

Contoh:
    python scripts/audit_gopay.py "../Syarat dan Ketentuan GoPay.pdf" \\
        --accessed 2026-03-23 --dry-run          # segmentasi saja, tanpa API
    python scripts/audit_gopay.py "../Syarat dan Ketentuan GoPay.pdf" --accessed 2026-03-23
"""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("CHROMADB_PERSIST_DIR", str(_ROOT / "data" / "processed" / "chroma_db"))
os.environ.setdefault("USE_TF", "0")
for p in (_ROOT / "backend", _ROOT / "src"):
    sys.path.insert(0, str(p))

from app.api.v1.audit import _extract_pdf_text_pymupdf, _split_into_clauses  # noqa: E402


def _agent(verdict):
    """Status, pasal yang dilanggar (+ grounded), dan sub-elemen hilang dari satu agen."""
    if not isinstance(verdict, dict):
        return None
    return {
        "status": verdict.get("verdict") or verdict.get("status"),
        "confidence": verdict.get("confidence_score"),
        "violated_articles": [
            {"regulation": a.get("regulation"), "article": a.get("article"),
             "grounded": a.get("grounded"), "detail": (a.get("violation_detail") or "")[:300]}
            for a in verdict.get("violated_articles") or [] if isinstance(a, dict)
        ],
        "checklist_topic": verdict.get("checklist_topic"),
        "missing_elements": verdict.get("missing_elements") or [],
    }


async def audit_all(clauses, regulator, top_k):
    from app.services.rag_service import RAGAuditService

    svc = RAGAuditService()
    rows = []
    for i, clause in enumerate(clauses, 1):
        cid = f"GOPAY-{i:03d}"
        t0 = time.time()
        gate = svc._run_gate(clause)  # dicatat terpisah: gate yang gagal diam-diam meloloskan klausul
        try:
            r = await svc.analyze_with_rag(clause=clause, regulator=regulator, top_k=top_k,
                                           clause_id=cid, use_cache=False)
            row = {
                "clause_id": cid, "text": clause,
                "final_status": r.get("final_status"),
                "analysis_mode": r.get("analysis_mode"),
                "gate_decision": r.get("gate_decision"),
                "gate": gate,
                "overall_confidence": r.get("overall_confidence"),
                "risk_score": r.get("risk_score"),
                "bi": _agent(r.get("bi_verdict")),
                "ojk": _agent(r.get("ojk_verdict")),
                "conflicts": r.get("violations") or [],
                "evidence_trail": r.get("evidence_trail") or [],
                "latency_ms": r.get("latency_ms", round((time.time() - t0) * 1000)),
            }
        except Exception as e:  # noqa: BLE001
            row = {"clause_id": cid, "text": clause, "gate": gate, "error": str(e),
                   "latency_ms": round((time.time() - t0) * 1000)}
        rows.append(row)
        print(f"[{i:03d}/{len(clauses)}] {row.get('analysis_mode', 'ERROR'):16s} "
              f"{row.get('final_status', row.get('error', ''))[:60]} ({row['latency_ms']} ms)")
        if row.get("error") and "credit" in row["error"].lower():
            print("  ✗ Saldo API habis — audit dihentikan.")
            break
    return rows


def summarize(rows, n_clauses):
    modes = Counter(r.get("analysis_mode", "ERROR") for r in rows)
    status = Counter(r.get("final_status", "ERROR") for r in rows)
    rag = [r for r in rows if r.get("analysis_mode") == "multi_agent_rag"]
    rag_status = Counter(r["final_status"] for r in rag)
    lat = [r["latency_ms"] for r in rag]
    n_errors = sum(1 for r in rows if r.get("error"))
    invalid = n_errors > 0 or modes.get("llm_only", 0) > 0 or len(rows) < n_clauses
    return {
        "n_clauses": n_clauses, "n_audited": len(rows), "n_errors": n_errors, "invalid": invalid,
        "analysis_mode": dict(modes), "final_status_all": dict(status),
        "final_status_rag": dict(rag_status),
        "avg_latency_ms_rag": round(sum(lat) / len(lat)) if lat else None,
        "gate_model": dict(Counter((r.get("gate") or {}).get("model") for r in rows)),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--accessed", required=True, help="Tanggal akses dokumen (YYYY-MM-DD)")
    ap.add_argument("--regulator", default="all")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true", help="Ekstraksi + segmentasi saja, tanpa API")
    ap.add_argument("--limit", type=int, default=None, help="Audit N klausul pertama saja (uji coba)")
    args = ap.parse_args()

    content = Path(args.pdf).read_bytes()
    text = _extract_pdf_text_pymupdf(content)
    clauses = _split_into_clauses(text)
    source = {
        "file": Path(args.pdf).name, "sha256": hashlib.sha256(content).hexdigest(),
        "accessed": args.accessed, "extractor": "pymupdf", "n_chars": len(text),
    }
    print(f"Dokumen: {source['file']} (akses {args.accessed}) → {len(clauses)} klausul")
    if args.dry_run:
        lengths = sorted(len(c) for c in clauses)
        print(f"Panjang klausul: min {lengths[0]}, median {lengths[len(lengths)//2]}, maks {lengths[-1]}")
        for i, c in enumerate(clauses[:5], 1):
            print(f"  [{i}] {c[:140]!r}")
        return

    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("OPENAI_API_KEY kosong — audit dihentikan.")
    target = clauses[: args.limit] if args.limit else clauses
    t0 = time.time()
    rows = asyncio.run(audit_all(target, args.regulator, args.top_k))
    summary = summarize(rows, len(target))
    out = {
        "source": source,
        "config": {
            "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
            "llm_model": os.getenv("LLM_MODEL", "gpt-5.4-mini"),
            "retrieval_strategy": os.getenv("RETRIEVAL_STRATEGY", "query_aware"),
            "gate_model": os.getenv("SOP_GATE_MODEL", "indobert"),
            "gate_threshold": float(os.getenv("SOP_GATE_THRESHOLD", "0.5")),
            "regulator": args.regulator, "top_k": args.top_k, "cache": False,
            "limit": args.limit,
        },
        "timestamp": datetime.now().isoformat(),
        "wall_time_s": round(time.time() - t0, 1),
        "summary": summary,
        "clauses": rows,
    }
    prefix = "invalid_gopay" if summary["invalid"] else "gopay"
    suffix = f"_limit{args.limit}" if args.limit else ""
    out_path = _ROOT / "data" / "audit_results" / f"{prefix}_{datetime.now():%Y%m%d_%H%M%S}{suffix}.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Hasil disimpan: {out_path}")
    if summary["invalid"]:
        sys.exit("RUN TIDAK VALID — ada error atau fallback llm_only.")


if __name__ == "__main__":
    main()
