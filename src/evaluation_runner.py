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

# ── Ground truth dari SOP Dummy + POJK/PBI labels ────────────────────────────
# Derived dari SOP_Dummy_EWallet_Palsu.md + proposal Lampiran A
GROUND_TRUTH = [
    {
        "clause_id": "BAB1-01",
        "clause": (
            "SOP ini mengatur standar operasional layanan uang elektronik "
            "\"NusantaraPay\" (selanjutnya disebut \"Perusahaan\")."
        ),
        "expected_status": "NOT_ADDRESSED",
        "expected_bi":  "NOT_ADDRESSED",
        "expected_ojk": "NOT_ADDRESSED",
        "category": "GENERAL",
        "violated_articles": [],
    },
    {
        "clause_id": "BAB1-02",
        "clause": "SOP ini wajib dipatuhi oleh seluruh karyawan dan mitra kerja Perusahaan.",
        "expected_status": "NOT_ADDRESSED",
        "expected_bi":  "NOT_ADDRESSED",
        "expected_ojk": "NOT_ADDRESSED",
        "category": "GENERAL",
        "violated_articles": [],
    },
    {
        "clause_id": "BAB2-01",
        "clause": (
            "Perusahaan wajib memperoleh persetujuan tertulis atau persetujuan elektronik "
            "(explicit consent) dari Nasabah sebelum mengumpulkan dan memproses Data Pribadi. "
            "Sebelum persetujuan diberikan, Perusahaan wajib menjelaskan secara tertulis "
            "dan/atau lisan mengenai tujuan pengumpulan data, jenis data yang dikumpulkan, "
            "serta konsekuensi dari persetujuan Nasabah terkait dengan pemberian data "
            "dan/atau informasi Nasabah kepada Perusahaan."
        ),
        "expected_status": "PARTIALLY_COMPLIANT",
        "expected_bi":  "NOT_ADDRESSED",
        "expected_ojk": "PARTIALLY_COMPLIANT",
        "category": "PRIVACY",
        "violated_articles": ["POJK No. 22/2023 Pasal 23 Ayat 2"],
    },
    {
        "clause_id": "BAB2-02",
        "clause": (
            "Data Pribadi Nasabah akan dienkripsi menggunakan standar keamanan AES-256 "
            "baik saat in-transit maupun at-rest."
        ),
        "expected_status": "PARTIALLY_COMPLIANT",
        "expected_bi":  "NOT_ADDRESSED",
        "expected_ojk": "PARTIALLY_COMPLIANT",
        "category": "SECURITY",
        "violated_articles": ["POJK No. 22/2023 Pasal 23 Ayat 2"],
    },
    {
        "clause_id": "BAB2-03",
        "clause": (
            "Nasabah berhak untuk meminta penghapusan permanen (Right to Erasure) atas "
            "Data Pribadi mereka kapan saja melalui aplikasi, dan Perusahaan wajib "
            "memprosesnya selambat-lambatnya 3x24 jam."
        ),
        "expected_status": "PARTIALLY_COMPLIANT",
        "expected_bi":  "NOT_ADDRESSED",
        "expected_ojk": "PARTIALLY_COMPLIANT",
        "category": "PRIVACY",
        "violated_articles": ["POJK No. 22/2023 Pasal 23 Ayat 2"],
    },
    {
        "clause_id": "BAB2-04",
        "clause": (
            "Data Pribadi Nasabah tidak akan pernah dijual kepada pihak ketiga mana pun "
            "tanpa izin eksplisit yang terpisah."
        ),
        "expected_status": "PARTIALLY_COMPLIANT",
        "expected_bi":  "NOT_ADDRESSED",
        "expected_ojk": "PARTIALLY_COMPLIANT",
        "category": "PRIVACY",
        "violated_articles": ["POJK No. 22/2023 Pasal 23 Ayat 2"],
    },
    {
        "clause_id": "BAB3-01",
        "clause": (
            "Segala bentuk pengaduan atau keluhan nasabah hanya dapat diterima pada jam "
            "operasional kerja, Senin hingga Jumat (10:00 - 15:00 WIB). Keluhan yang masuk "
            "di luar jam tersebut akan diabaikan."
        ),
        "expected_status": "NON_COMPLIANT",
        "expected_bi":  "NOT_ADDRESSED",
        "expected_ojk": "NON_COMPLIANT",
        "category": "COMPLAINT",
        "violated_articles": ["POJK No. 22/2023 Pasal 69 Ayat 3"],
    },
    {
        "clause_id": "BAB3-02",
        "clause": (
            "Tim Customer Service memiliki waktu maksimal 60 hari kerja sejak keluhan "
            "diterima untuk menyelesaikan masalah nasabah dan memberikan kompensasi (jika ada)."
        ),
        "expected_status": "NON_COMPLIANT",
        "expected_bi":  "NOT_ADDRESSED",
        "expected_ojk": "NON_COMPLIANT",
        "category": "COMPLAINT",
        "violated_articles": ["POJK No. 22/2023 Pasal 75 Ayat 1"],
    },
    {
        "clause_id": "BAB3-03",
        "clause": (
            "Nasabah yang memberikan rating bintang 1 pada aplikasi secara otomatis akan "
            "dibekukan sementara akunnya selama 7 hari tanpa pemberitahuan sebelumnya "
            "untuk \"investigasi keamanan\"."
        ),
        "expected_status": "NON_COMPLIANT",
        "expected_bi":  "NOT_ADDRESSED",
        "expected_ojk": "NON_COMPLIANT",
        "category": "CONSUMER_RIGHTS",
        "violated_articles": ["POJK No. 22/2023 Pasal 46 Ayat 2"],
    },
    {
        "clause_id": "BAB4-01",
        "clause": (
            "Akun Unverified (Belum KYC): Nasabah yang belum mengunggah KTP (Unregistered) "
            "dapat menyimpan saldo maksimal hingga Rp 10.000.000 (Sepuluh Juta Rupiah)."
        ),
        "expected_status": "NON_COMPLIANT",
        "expected_bi":  "NON_COMPLIANT",
        "expected_ojk": "NOT_ADDRESSED",
        "category": "LIMITS",
        "violated_articles": ["PBI No. 23/6/PBI/2021 Pasal 160 Ayat 1"],
    },
    {
        "clause_id": "BAB4-02",
        "clause": (
            "Akun Verified (Sudah KYC): Nasabah yang sudah diverifikasi identitasnya "
            "dapat menyimpan saldo maksimal Rp 500.000.000 (Lima Ratus Juta Rupiah)."
        ),
        "expected_status": "NON_COMPLIANT",
        "expected_bi":  "NON_COMPLIANT",
        "expected_ojk": "NOT_ADDRESSED",
        "category": "LIMITS",
        "violated_articles": ["PBI No. 23/6/PBI/2021 Pasal 160 Ayat 1"],
    },
    {
        "clause_id": "BAB4-03",
        "clause": (
            "Batas transaksi masuk bulanan (Monthly Incoming Limit) untuk semua pengguna "
            "tidak dibatasi untuk mendorong pertumbuhan Gross Transaction Value (GTV) perusahaan."
        ),
        "expected_status": "NON_COMPLIANT",
        "expected_bi":  "NON_COMPLIANT",
        "expected_ojk": "NOT_ADDRESSED",
        "category": "LIMITS",
        "violated_articles": ["PBI No. 23/6/PBI/2021 Pasal 160 Ayat 2"],
    },
]


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

def compute_metrics(results: List[Dict]) -> Dict:
    """
    Hitung Precision, Recall, F1 per kelas + Macro + detail per klausa.
    Kelas positif utama: NON_COMPLIANT (termasuk PARTIALLY_COMPLIANT sebagai partial TP).
    """
    classes = ["COMPLIANT", "NON_COMPLIANT", "PARTIALLY_COMPLIANT", "NOT_ADDRESSED"]
    tp = {c: 0 for c in classes}
    fp = {c: 0 for c in classes}
    fn = {c: 0 for c in classes}

    for r in results:
        pred = r["predicted_norm"]
        exp  = r["expected_norm"]
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
    correct = sum(1 for r in results if r["predicted_norm"] == r["expected_norm"])
    accuracy = correct / len(results) if results else 0

    # NON_COMPLIANT detection: treat PARTIALLY_COMPLIANT pred as partial
    # TP_nc = predicted NON_COMPLIANT or PARTIALLY_COMPLIANT when expected is NON_COMPLIANT
    nc_expected = [r for r in results if r["expected_norm"] == "NON_COMPLIANT"]
    nc_detected = sum(1 for r in nc_expected
                      if r["predicted_norm"] in ("NON_COMPLIANT", "PARTIALLY_COMPLIANT"))
    recall_nc_broad = nc_detected / len(nc_expected) if nc_expected else 0

    return {
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_p, 4),
        "macro_recall":    round(macro_r, 4),
        "macro_f1":        round(macro_f, 4),
        "recall_non_compliant_strict": per_class["NON_COMPLIANT"]["recall"],
        "recall_non_compliant_broad":  round(recall_nc_broad, 4),
        "per_class": per_class,
        "total": len(results),
        "correct": correct,
    }


def compute_mrr_hitrate(results: List[Dict], k_values: List[int] = [3, 5]) -> Dict:
    """
    MRR dan HitRate@K berdasarkan apakah artikel yang benar muncul
    di retrieved_articles setiap klausa.
    """
    mrr_scores = []
    hit_at_k = {k: 0 for k in k_values}

    for r in results:
        expected_articles = r.get("expected_violated_articles", [])
        retrieved = r.get("retrieved_articles", [])

        if not expected_articles:
            continue

        # Cari rank pertama artikel yang relevan
        rank = None
        for i, art in enumerate(retrieved, start=1):
            for exp_art in expected_articles:
                # Fuzzy match: cek substring pasal number
                if any(token in art for token in exp_art.split() if len(token) > 3):
                    rank = i
                    break
            if rank:
                break

        if rank:
            mrr_scores.append(1.0 / rank)
            for k in k_values:
                if rank <= k:
                    hit_at_k[k] += 1
        else:
            mrr_scores.append(0.0)

    n = len(mrr_scores)
    mrr = sum(mrr_scores) / n if n > 0 else 0.0
    hit_rates = {f"hit_rate_at_{k}": round(hit_at_k[k] / n, 4) if n > 0 else 0.0
                 for k in k_values}
    return {"mrr": round(mrr, 4), **hit_rates, "evaluated_clauses": n}


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

    results = []
    import asyncio

    for i, sample in enumerate(GROUND_TRUTH, 1):
        print(f"[{i:02d}/{len(GROUND_TRUTH)}] {sample['clause_id']} — {sample['category']}")
        t0 = time.time()
        try:
            audit_result = asyncio.run(coordinator.audit_clause_async(
                clause=sample["clause"],
                clause_id=sample["clause_id"],
                context={"category": sample["category"]}
            ))
            latency = round((time.time() - t0) * 1000)

            # Ambil status akhir
            final_status = str(getattr(
                getattr(audit_result, "final_verdict", None), "final_status",
                getattr(audit_result, "final_status", "UNCLEAR")
            )).upper()

            bi_status = str(getattr(
                getattr(audit_result, "bi_verdict", None), "verdict",
                getattr(getattr(audit_result, "bi_verdict", None), "status", "UNCLEAR")
            )).upper()

            ojk_status = str(getattr(
                getattr(audit_result, "ojk_verdict", None), "verdict",
                getattr(getattr(audit_result, "ojk_verdict", None), "status", "UNCLEAR")
            )).upper()

            # Kumpulkan retrieved articles dari context
            retrieved_arts = []
            for agent_v in [audit_result.bi_verdict, audit_result.ojk_verdict]:
                if agent_v and hasattr(agent_v, "retrieved_context"):
                    ctx = agent_v.retrieved_context or ""
                    retrieved_arts.extend([line.strip() for line in ctx.split("\n")
                                           if "Pasal" in line or "PBI" in line or "POJK" in line])

            result = {
                "clause_id":    sample["clause_id"],
                "category":     sample["category"],
                "clause":       sample["clause"][:100] + "...",
                "predicted":    final_status,
                "expected":     sample["expected_status"],
                "predicted_norm": _normalize(final_status),
                "expected_norm":  _normalize(sample["expected_status"]),
                "predicted_bi":  bi_status,
                "expected_bi":   sample["expected_bi"],
                "predicted_ojk": ojk_status,
                "expected_ojk":  sample["expected_ojk"],
                "correct":       _normalize(final_status) == _normalize(sample["expected_status"]),
                "latency_ms":    latency,
                "expected_violated_articles": sample["violated_articles"],
                "retrieved_articles": retrieved_arts[:10],
            }
        except Exception as e:
            print(f"  ⚠ Error: {e}")
            result = {
                "clause_id":      sample["clause_id"],
                "category":       sample["category"],
                "clause":         sample["clause"][:100] + "...",
                "predicted":      "ERROR",
                "expected":       sample["expected_status"],
                "predicted_norm": "NOT_ADDRESSED",
                "expected_norm":  _normalize(sample["expected_status"]),
                "predicted_bi":   "ERROR",
                "expected_bi":    sample["expected_bi"],
                "predicted_ojk":  "ERROR",
                "expected_ojk":   sample["expected_ojk"],
                "correct":        False,
                "latency_ms":     round((time.time() - t0) * 1000),
                "expected_violated_articles": sample["violated_articles"],
                "retrieved_articles": [],
                "error": str(e),
            }

        results.append(result)
        status_icon = "✓" if result["correct"] else "✗"
        print(f"  {status_icon} pred={result['predicted']:20s} exp={result['expected']:20s} "
              f"({result['latency_ms']}ms)")

    # Hitung metrik
    metrics    = compute_metrics(results)
    retrieval  = compute_mrr_hitrate(results)
    avg_latency = round(sum(r["latency_ms"] for r in results) / len(results))

    print(f"\n{'='*60}")
    print(f"  RESULTS — {provider.upper()} / {model}")
    print(f"{'='*60}")
    print(f"  Accuracy              : {metrics['accuracy']:.4f}")
    print(f"  Macro Precision       : {metrics['macro_precision']:.4f}")
    print(f"  Macro Recall          : {metrics['macro_recall']:.4f}")
    print(f"  Macro F1              : {metrics['macro_f1']:.4f}")
    print(f"  Recall NON_COMPLIANT  : {metrics['recall_non_compliant_strict']:.4f} "
          f"(broad: {metrics['recall_non_compliant_broad']:.4f})")
    print(f"  MRR                   : {retrieval['mrr']:.4f}")
    print(f"  Hit Rate@3            : {retrieval.get('hit_rate_at_3', 0):.4f}")
    print(f"  Hit Rate@5            : {retrieval.get('hit_rate_at_5', 0):.4f}")
    print(f"  Avg Latency           : {avg_latency}ms")
    print(f"{'='*60}\n")

    # Per-class detail
    print("  Per-Class Metrics:")
    for cls, m in metrics["per_class"].items():
        if m["tp"] + m["fn"] > 0:
            print(f"    {cls:25s}  P={m['precision']:.3f}  R={m['recall']:.3f}  F1={m['f1']:.3f}  "
                  f"(TP={m['tp']} FP={m['fp']} FN={m['fn']})")

    # Simpan hasil
    run_name  = f"{provider}_{model}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    out_dir   = _ROOT / "data" / "audit_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path  = out_dir / f"eval_{run_name}.json"

    output = {
        "run_name":    run_name,
        "provider":    provider,
        "model":       model,
        "timestamp":   datetime.now().isoformat(),
        "metrics":     metrics,
        "retrieval":   retrieval,
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
                "retrieval_mode": os.getenv("RETRIEVAL_MODE", "hybrid"),
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
