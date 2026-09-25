"""
evaluation_runner.py — Runner evaluasi sistematis Multi-Agent RAG
=================================================================
Menjalankan golden dataset (SOP Dummy NusantaraPay) melalui sistem audit,
menghitung metrik Precision/Recall/F1/MRR/HitRate@K, dan log ke MLflow.

Usage:
    # Evaluasi dengan model default dari env
    python src/evaluation_runner.py

    # Evaluasi GPT-5.4-mini
    LLM_PROVIDER=openai LLM_MODEL=gpt-5.4-mini python src/evaluation_runner.py

    # Evaluasi Claude Haiku 4.5
    LLM_PROVIDER=anthropic LLM_MODEL=claude-haiku-4-5-20251001 python src/evaluation_runner.py

    # Tanpa MLflow
    python src/evaluation_runner.py --no-mlflow
"""

import os
import sys
import json
import re
import time
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

# ── Path setup ────────────────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
_SRC  = _ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# ── Ground truth: sumber tunggal data/golden_dataset.yaml ─────────────────────
GOLDEN_PATH = _ROOT / "data" / "golden_dataset.yaml"


def load_golden_dataset(path: Path = GOLDEN_PATH) -> List[Dict]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)["samples"]


GROUND_TRUTH = load_golden_dataset()


# ── Normalisasi status ────────────────────────────────────────────────────────

def _normalize(status: str) -> str:
    s = str(status).upper().replace("-", "_").strip()
    mapping = {
        "COMPLIANT":           "COMPLIANT",
        "NON_COMPLIANT":       "NON_COMPLIANT",
        "PARTIALLY_COMPLIANT": "PARTIALLY_COMPLIANT",
        "NEEDS_REVIEW":        "NON_COMPLIANT",  # treat konservatif
        "NOT_ADDRESSED":       "NOT_ADDRESSED",
        "UNCLEAR":             "NOT_ADDRESSED",
    }
    return mapping.get(s, "NOT_ADDRESSED")


# ── Metrik ────────────────────────────────────────────────────────────────────

SIX_CLASSES = [
    "COMPLIANT", "NON_COMPLIANT", "PARTIALLY_COMPLIANT",
    "NEEDS_REVIEW", "NOT_ADDRESSED", "UNCLEAR",
]


def _normalize6(status: str) -> str:
    """Normalisasi tanpa peleburan kelas — enam kelas Tabel 3.6."""
    s = str(status).upper().replace("-", "_").strip()
    return s if s in SIX_CLASSES else "UNCLEAR"


def wilson_ci(successes: int, n: int, z: float = 1.96) -> Tuple[float, float]:
    """Interval kepercayaan Wilson 95% untuk proporsi (accuracy / recall)."""
    if n == 0:
        return (0.0, 0.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


def compute_metrics(
    results: List[Dict],
    classes: List[str] = None,
    pred_key: str = "predicted_norm",
    exp_key: str = "expected_norm",
) -> Dict:
    """
    Hitung Precision, Recall, F1 per kelas + Macro + detail per klausa.
    Default: skema 4 kelas lama (NEEDS_REVIEW→NON_COMPLIANT, UNCLEAR→NOT_ADDRESSED)
    agar sebanding dengan hasil sebelumnya. Untuk 6 kelas proposal gunakan
    classes=SIX_CLASSES, pred_key="predicted_6", exp_key="expected_6".
    """
    classes = classes or ["COMPLIANT", "NON_COMPLIANT", "PARTIALLY_COMPLIANT", "NOT_ADDRESSED"]
    tp = {c: 0 for c in classes}
    fp = {c: 0 for c in classes}
    fn = {c: 0 for c in classes}

    for r in results:
        pred = r[pred_key]
        exp  = r[exp_key]
        for c in classes:
            if pred == c and exp == c:
                tp[c] += 1
            elif pred == c and exp != c:
                fp[c] += 1
            elif pred != c and exp == c:
                fn[c] += 1

    per_class = {}
    for c in classes:
        p = tp[c] / (tp[c] + fp[c]) if (tp[c] + fp[c]) > 0 else 0.0
        r = tp[c] / (tp[c] + fn[c]) if (tp[c] + fn[c]) > 0 else 0.0
        f = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        per_class[c] = {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f, 4),
                        "tp": tp[c], "fp": fp[c], "fn": fn[c]}

    # Macro average (hanya kelas yang ada di ground truth)
    active = [c for c in classes if (tp[c] + fn[c]) > 0]
    macro_p = sum(per_class[c]["precision"] for c in active) / len(active) if active else 0
    macro_r = sum(per_class[c]["recall"]    for c in active) / len(active) if active else 0
    macro_f = sum(per_class[c]["f1"]        for c in active) / len(active) if active else 0

    # Accuracy
    correct = sum(1 for r in results if r[pred_key] == r[exp_key])
    accuracy = correct / len(results) if results else 0

    # NON_COMPLIANT detection: treat PARTIALLY_COMPLIANT pred as partial
    # TP_nc = predicted NON_COMPLIANT or PARTIALLY_COMPLIANT when expected is NON_COMPLIANT
    nc_expected = [r for r in results if r[exp_key] == "NON_COMPLIANT"]
    nc_detected = sum(1 for r in nc_expected
                      if r[pred_key] in ("NON_COMPLIANT", "PARTIALLY_COMPLIANT"))
    recall_nc_broad = nc_detected / len(nc_expected) if nc_expected else 0

    return {
        "classes": classes,
        "accuracy": round(accuracy, 4),
        "accuracy_ci95_wilson": wilson_ci(correct, len(results)),
        "macro_precision": round(macro_p, 4),
        "macro_recall":    round(macro_r, 4),
        "macro_f1":        round(macro_f, 4),
        "recall_non_compliant_strict": per_class["NON_COMPLIANT"]["recall"],
        "recall_non_compliant_broad":  round(recall_nc_broad, 4),
        "per_class": per_class,
        "total": len(results),
        "correct": correct,
    }


_QREL_RE = re.compile(
    r"(?P<reg>PBI|POJK)\D*?(?P<num>\d+(?:/\d+)?)(?:/PBI)?(?:/(?P<year>\d{4}))?.*?Pasal\s+(?P<pasal>\d+[A-Z]?)",
    re.IGNORECASE,
)


def parse_qrel(article: str) -> Dict:
    """
    "PBI No. 23/6/PBI/2021 Pasal 160 Ayat 1" → {"agent": "BI", "reg_num": "23/6", "pasal": "160"}
    "POJK No. 22/2023 Pasal 23 Ayat 2"        → {"agent": "OJK", "reg_num": "22", "pasal": "23"}
    """
    m = _QREL_RE.search(article or "")
    if not m:
        return {}
    reg = m.group("reg").upper()
    num = m.group("num")
    if reg == "POJK":
        num = num.split("/")[0]
    return {"agent": "BI" if reg == "PBI" else "OJK", "reg_num": num, "pasal": m.group("pasal")}


def _is_relevant(evidence: Dict, qrel: Dict) -> bool:
    if str(evidence.get("pasal_number", "")) != qrel["pasal"]:
        return False
    regulation = str(evidence.get("regulation", "")).replace(" ", "")
    # Jika metadata regulasi kosong (ingest lama), cukup cocokkan nomor pasal
    return not regulation or qrel["reg_num"] in regulation


def compute_mrr_hitrate(results: List[Dict], k_values: List[int] = [3, 5]) -> Dict:
    """
    MRR (Persamaan 2.32) dan Hit Rate@K (Persamaan 2.33) berbasis qrels tingkat
    pasal: violated_articles golden dataset dianotasi manual sebagai pasal
    relevan. Relevansi dicek dari METADATA chunk (pasal_number + kode regulasi)
    pada Top-K milik agen regulator yang bersangkutan, bukan string matching teks.
    Klausul tanpa qrels (NOT_ADDRESSED) tidak diikutkan.
    """
    rr_scores = []
    hit_at_k = {k: 0 for k in k_values}
    per_clause = []

    for r in results:
        qrels = [q for q in (parse_qrel(a) for a in r.get("expected_violated_articles", [])) if q]
        if not qrels:
            continue

        rank = None
        for q in qrels:
            evidence = r.get("evidence_bi" if q["agent"] == "BI" else "evidence_ojk", [])
            for e in evidence:
                if _is_relevant(e, q):
                    if rank is None or e["rank"] < rank:
                        rank = e["rank"]
                    break

        rr = 1.0 / rank if rank else 0.0
        rr_scores.append(rr)
        for k in k_values:
            if rank and rank <= k:
                hit_at_k[k] += 1
        per_clause.append({"clause_id": r["clause_id"], "first_relevant_rank": rank, "rr": round(rr, 4)})

    n = len(rr_scores)
    mrr = sum(rr_scores) / n if n > 0 else 0.0
    hit_rates = {f"hit_rate_at_{k}": round(hit_at_k[k] / n, 4) if n > 0 else 0.0
                 for k in k_values}
    return {"mrr": round(mrr, 4), **hit_rates, "evaluated_clauses": n, "per_clause": per_clause}


def compute_citation_grounding(results: List[Dict]) -> Dict:
    """Proporsi pasal yang dikutip LLM di violations yang ada di Top-K (evidence trail)."""
    grounded = checked = 0
    for r in results:
        for g in r.get("citation_grounded", []):
            if g is None:
                continue
            checked += 1
            grounded += int(bool(g))
    return {
        "citation_grounding_rate": round(grounded / checked, 4) if checked else None,
        "citations_checked": checked,
    }


def check_retrieval_ready(coordinator) -> Dict:
    """
    Evaluasi RAG wajib berjalan dengan basis pengetahuan terisi. Jika index
    ChromaDB gagal dimuat, agen akan diam-diam mengembalikan NOT_ADDRESSED
    tanpa retrieval — hasil semacam itu bukan evaluasi RAG, jadi hentikan.
    """
    from agents.base_agent import retrieval_strategy
    setup = {"strategy": retrieval_strategy()}
    for agent in (coordinator.bi_agent, coordinator.ojk_agent):
        if agent.index is None:
            raise RuntimeError(
                f"[{agent.name}] Vector store '{agent.collection_name}' tidak termuat — "
                "jalankan src/ingest.py terlebih dahulu. Evaluasi dihentikan."
            )
        setup[agent.name] = "hybrid" if agent.hybrid_retriever is not None else "dense"
        if agent.hybrid_retriever is None:
            print(f"  ⚠ [{agent.name}] BM25 index tidak ditemukan — retrieval dense-only")
    return setup


def _verdict_status(verdict) -> str:
    """AuditResult.bi_verdict/ojk_verdict berupa dict (model_dump)."""
    if not verdict:
        return "UNCLEAR"
    if isinstance(verdict, dict):
        return str(verdict.get("verdict") or verdict.get("status") or "UNCLEAR").upper()
    return str(getattr(verdict, "verdict", getattr(verdict, "status", "UNCLEAR"))).upper()


def _verdict_field(verdict, key: str, default):
    if isinstance(verdict, dict):
        return verdict.get(key, default)
    return getattr(verdict, key, default) if verdict else default


def build_result(sample: Dict, audit_result, latency: int) -> Dict:
    final_verdict = getattr(audit_result, "final_verdict", None)
    final_status = str(getattr(final_verdict, "final_status", "UNCLEAR")).upper()
    bi_v, ojk_v = audit_result.bi_verdict, audit_result.ojk_verdict

    grounded = []
    for v in (bi_v, ojk_v):
        for art in _verdict_field(v, "violated_articles", []) or []:
            grounded.append(art.get("grounded") if isinstance(art, dict) else getattr(art, "grounded", None))

    return {
        "clause_id":      sample["clause_id"],
        "category":       sample["category"],
        "clause":         sample["clause"][:100] + "...",
        "predicted":      final_status,
        "expected":       sample["expected_status"],
        "predicted_norm": _normalize(final_status),
        "expected_norm":  _normalize(sample["expected_status"]),
        "predicted_6":    _normalize6(final_status),
        "expected_6":     _normalize6(sample["expected_status"]),
        "predicted_bi":   _verdict_status(bi_v),
        "expected_bi":    sample["expected_bi"],
        "predicted_ojk":  _verdict_status(ojk_v),
        "expected_ojk":   sample["expected_ojk"],
        "correct":        _normalize(final_status) == _normalize(sample["expected_status"]),
        "correct_6":      _normalize6(final_status) == _normalize6(sample["expected_status"]),
        "latency_ms":     latency,
        "confidence":     getattr(final_verdict, "overall_confidence", None),
        "retrieval_mode_bi":  _verdict_field(bi_v, "retrieval_mode", None),
        "retrieval_mode_ojk": _verdict_field(ojk_v, "retrieval_mode", None),
        "sparse_boost":   _verdict_field(bi_v, "sparse_boost", None),
        "expected_violated_articles": sample["violated_articles"],
        "evidence_bi":    _verdict_field(bi_v, "evidence", []) or [],
        "evidence_ojk":   _verdict_field(ojk_v, "evidence", []) or [],
        "citation_grounded": grounded,
    }


def build_error_result(sample: Dict, error: Exception, latency: int) -> Dict:
    return {
        "clause_id":      sample["clause_id"],
        "category":       sample["category"],
        "clause":         sample["clause"][:100] + "...",
        "predicted":      "ERROR",
        "expected":       sample["expected_status"],
        "predicted_norm": "NOT_ADDRESSED",
        "expected_norm":  _normalize(sample["expected_status"]),
        "predicted_6":    "UNCLEAR",
        "expected_6":     _normalize6(sample["expected_status"]),
        "predicted_bi":   "ERROR",
        "expected_bi":    sample["expected_bi"],
        "predicted_ojk":  "ERROR",
        "expected_ojk":   sample["expected_ojk"],
        "correct":        False,
        "correct_6":      False,
        "latency_ms":     latency,
        "expected_violated_articles": sample["violated_articles"],
        "evidence_bi":    [],
        "evidence_ojk":   [],
        "citation_grounded": [],
        "error": str(error),
    }


# ── Runner utama ──────────────────────────────────────────────────────────────

def run_evaluation(use_mlflow: bool = True, mlflow_uri: str = None) -> Dict:
    from agents.coordinator import CoordinatorAgent

    api_key     = os.getenv("OPENAI_API_KEY", "")
    ant_key     = os.getenv("ANTHROPIC_API_KEY", "")
    provider    = os.getenv("LLM_PROVIDER", "openai")
    model       = os.getenv("LLM_MODEL", "gpt-5.4-mini")
    chroma_path = os.getenv("CHROMADB_PERSIST_DIR",
                            str(_ROOT / "data" / "processed" / "chroma_db"))

    print(f"\n{'='*60}")
    print(f"  Compliance Audit — Systematic Evaluation")
    print(f"  Provider : {provider}")
    print(f"  Model    : {model}")
    print(f"  Chroma   : {chroma_path}")
    print(f"  Samples  : {len(GROUND_TRUTH)}")
    print(f"{'='*60}\n")

    coordinator = CoordinatorAgent()
    # Selalu kirim OpenAI key ke coordinator — dipakai untuk ChromaDB embeddings
    # Anthropic key dibaca dari env (ANTHROPIC_API_KEY) langsung di agent initialize
    coordinator.initialize(
        api_key=api_key,
        chroma_path=chroma_path
    )
    retrieval_setup = check_retrieval_ready(coordinator)

    results = []
    import asyncio

    for i, sample in enumerate(GROUND_TRUTH, 1):
        print(f"[{i:02d}/{len(GROUND_TRUTH)}] {sample['clause_id']} — {sample['category']}")
        t0 = time.time()
        try:
            audit_result = asyncio.run(coordinator.audit_clause_async(
                clause=sample["clause"],
                clause_id=sample["clause_id"],
                context={"category": sample["category"], "regulator": "all", "top_k": 5}
            ))
            latency = round((time.time() - t0) * 1000)
            result = build_result(sample, audit_result, latency)
        except Exception as e:
            print(f"  ⚠ Error: {e}")
            result = build_error_result(sample, e, round((time.time() - t0) * 1000))

        results.append(result)
        status_icon = "✓" if result["correct"] else "✗"
        print(f"  {status_icon} pred={result['predicted']:20s} exp={result['expected']:20s} "
              f"({result['latency_ms']}ms)")

    # Hitung metrik
    metrics    = compute_metrics(results)
    metrics_6  = compute_metrics(results, classes=SIX_CLASSES,
                                 pred_key="predicted_6", exp_key="expected_6")
    retrieval  = compute_mrr_hitrate(results)
    grounding  = compute_citation_grounding(results)
    avg_latency = round(sum(r["latency_ms"] for r in results) / len(results))

    print(f"\n{'='*60}")
    print(f"  RESULTS — {provider.upper()} / {model}")
    print(f"{'='*60}")
    print(f"  Accuracy (4 kelas)    : {metrics['accuracy']:.4f}  CI95 {metrics['accuracy_ci95_wilson']}")
    print(f"  Accuracy (6 kelas)    : {metrics_6['accuracy']:.4f}  Macro-F1 6 kelas: {metrics_6['macro_f1']:.4f}")
    print(f"  Macro Precision       : {metrics['macro_precision']:.4f}")
    print(f"  Macro Recall          : {metrics['macro_recall']:.4f}")
    print(f"  Macro F1              : {metrics['macro_f1']:.4f}")
    print(f"  Recall NON_COMPLIANT  : {metrics['recall_non_compliant_strict']:.4f} "
          f"(broad: {metrics['recall_non_compliant_broad']:.4f})")
    print(f"  MRR                   : {retrieval['mrr']:.4f}")
    print(f"  Hit Rate@3            : {retrieval.get('hit_rate_at_3', 0):.4f}")
    print(f"  Hit Rate@5            : {retrieval.get('hit_rate_at_5', 0):.4f}")
    print(f"  Citation grounding    : {grounding['citation_grounding_rate']} "
          f"({grounding['citations_checked']} sitasi diperiksa)")
    print(f"  Avg Latency           : {avg_latency}ms")
    print(f"{'='*60}\n")

    # Per-class detail
    print("  Per-Class Metrics:")
    for cls, m in metrics["per_class"].items():
        if m["tp"] + m["fn"] > 0:
            print(f"    {cls:25s}  P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}  "
                  f"(TP={m['tp']} FP={m['fp']} FN={m['fn']})")

    # Simpan hasil
    run_name  = (f"{provider}_{model}_{retrieval_setup['strategy']}_"
                 f"{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    out_dir   = _ROOT / "data" / "audit_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path  = out_dir / f"eval_{run_name}.json"

    output = {
        "run_name":    run_name,
        "provider":    provider,
        "model":       model,
        "timestamp":   datetime.now().isoformat(),
        "retrieval_setup": retrieval_setup,
        "metrics":     metrics,
        "metrics_6class": metrics_6,
        "retrieval":   retrieval,
        "citation_grounding": grounding,
        "avg_latency_ms": avg_latency,
        "results":     results,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"  Hasil disimpan: {out_path}")

    # MLflow logging
    if use_mlflow:
        _log_to_mlflow(output, run_name, mlflow_uri)

    return output


def _log_to_mlflow(output: Dict, run_name: str, tracking_uri: str = None):
    try:
        import mlflow

        uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")
        mlflow.set_tracking_uri(uri)
        mlflow.set_experiment("compliance_evaluation")

        with mlflow.start_run(run_name=run_name):
            # Parameters
            mlflow.log_params({
                "provider":       output["provider"],
                "model":          output["model"],
                "n_samples":      output["metrics"]["total"],
                "retrieval_mode": ",".join(f"{k}={v}" for k, v in output.get("retrieval_setup", {}).items()),
            })

            # Metrics — classification
            m = output["metrics"]
            mlflow.log_metrics({
                "accuracy":                    m["accuracy"],
                "macro_precision":             m["macro_precision"],
                "macro_recall":                m["macro_recall"],
                "macro_f1":                    m["macro_f1"],
                "recall_non_compliant_strict": m["recall_non_compliant_strict"],
                "recall_non_compliant_broad":  m["recall_non_compliant_broad"],
                "avg_latency_ms":              output["avg_latency_ms"],
            })

            # Metrics — retrieval
            r = output["retrieval"]
            m6 = output.get("metrics_6class", {})
            mlflow.log_metrics({
                "accuracy_6class": m6.get("accuracy", 0),
                "macro_f1_6class": m6.get("macro_f1", 0),
                "citation_grounding_rate": output.get("citation_grounding", {}).get("citation_grounding_rate") or 0,
            })
            mlflow.log_metrics({
                "mrr":           r["mrr"],
                "hit_rate_at_3": r.get("hit_rate_at_3", 0),
                "hit_rate_at_5": r.get("hit_rate_at_5", 0),
            })

            # Per-class
            for cls, cm in m["per_class"].items():
                if cm["tp"] + cm["fn"] > 0:
                    key = cls.lower()
                    mlflow.log_metrics({
                        f"{key}_precision": cm["precision"],
                        f"{key}_recall":    cm["recall"],
                        f"{key}_f1":        cm["f1"],
                    })

            # Artifact
            import tempfile, os as _os
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                             encoding="utf-8") as tf:
                json.dump(output, tf, ensure_ascii=False, indent=2)
                tmp = tf.name
            mlflow.log_artifact(tmp, "evaluation_results")
            _os.unlink(tmp)

        print(f"  MLflow run logged: {run_name}")
    except Exception as e:
        print(f"  ⚠ MLflow logging gagal (skip): {e}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-mlflow", action="store_true",
                        help="Skip MLflow logging")
    parser.add_argument("--mlflow-uri", default=None,
                        help="MLflow tracking URI (default: $MLFLOW_TRACKING_URI)")
    args = parser.parse_args()

    run_evaluation(
        use_mlflow=not args.no_mlflow,
        mlflow_uri=args.mlflow_uri,
    )
