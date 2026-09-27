"""
Metrik turunan untuk Bab 4 Semhas dari file hasil evaluation_runner.

Menggabungkan beberapa run (mis. hasil --repeat 3) dan menghitung:
confusion matrix gabungan, akurasi + Wilson CI, recall NC ketat/longgar,
citation grounding, citation accuracy (pasal dikutip == qrels), ECE (10 bin),
rerata confidence benar vs salah, latensi, dan klausul tidak stabil.

Run yang memuat error API (field "error" pada hasil) ditolak.

Contoh:
    python scripts/semhas_metrics.py data/audit_results/eval_openai_gpt-5.4-mini_query_aware_20260927_1642*.json
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from evaluation_runner import wilson_ci  # noqa: E402

PASAL_RE = re.compile(r"Pasal\s+(\d+)")


def cited_pasals(result):
    diag = result.get("diagnostics") or {}
    out = set()
    for agent in ("bi", "ojk"):
        for v in (diag.get(agent) or {}).get("violations") or []:
            text = v.get("article", "") if isinstance(v, dict) else str(v)
            out.update(PASAL_RE.findall(text))
    return out


def ece(confs, corrects, bins=10):
    n = len(confs)
    buckets = defaultdict(list)
    for c, k in zip(confs, corrects):
        buckets[min(int(c * bins), bins - 1)].append((c, k))
    total = 0.0
    for items in buckets.values():
        acc = sum(k for _, k in items) / len(items)
        conf = sum(c for c, _ in items) / len(items)
        total += len(items) / n * abs(acc - conf)
    return round(total, 4), {f"{b/bins:.1f}-{(b+1)/bins:.1f}": len(v) for b, v in sorted(buckets.items())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    args = ap.parse_args()

    runs = [json.load(open(f)) for f in args.files]
    bad = [f for f, r in zip(args.files, runs) if any(x.get("error") for x in r["results"])]
    if bad:
        sys.exit(f"TIDAK VALID — run berisi error API: {bad}")

    cm, confs, corrects, lat = Counter(), [], [], []
    grounded = grounded_total = cit_hit = cit_total = 0
    verdicts = defaultdict(list)
    for r in runs:
        lat.append(r["avg_latency_ms"])
        for x in r["results"]:
            cm[(x["expected_6"], x["predicted_6"])] += 1
            verdicts[x["clause_id"]].append(x["predicted_6"])
            if x.get("confidence") is not None:
                confs.append(x["confidence"])
                corrects.append(bool(x["correct_6"]))
            flags = [g for g in x.get("citation_grounded", []) if g is not None]
            grounded += sum(flags)
            grounded_total += len(flags)
            if x["expected_6"] == "NON_COMPLIANT" and x.get("expected_violated_articles"):
                exp = {p for a in x["expected_violated_articles"] for p in PASAL_RE.findall(a)}
                cit_total += 1
                cit_hit += bool(exp & cited_pasals(x))

    n = sum(cm.values())
    correct = sum(v for (e, p), v in cm.items() if e == p)
    nc_total = sum(v for (e, _), v in cm.items() if e == "NON_COMPLIANT")
    nc_strict = cm[("NON_COMPLIANT", "NON_COMPLIANT")]
    nc_broad = nc_strict + cm[("NON_COMPLIANT", "PARTIALLY_COMPLIANT")]
    ece_val, ece_bins = ece(confs, corrects) if confs else (None, {})
    conf_ok = [c for c, k in zip(confs, corrects) if k]
    conf_bad = [c for c, k in zip(confs, corrects) if not k]

    out = {
        "files": args.files,
        "n_predictions": n,
        "confusion": {f"{e}->{p}": v for (e, p), v in sorted(cm.items())},
        "accuracy": round(correct / n, 4), "accuracy_wilson": wilson_ci(correct, n),
        "recall_nc_strict": round(nc_strict / nc_total, 4) if nc_total else None,
        "recall_nc_strict_wilson": wilson_ci(nc_strict, nc_total),
        "recall_nc_broad": round(nc_broad / nc_total, 4) if nc_total else None,
        "recall_nc_broad_wilson": wilson_ci(nc_broad, nc_total),
        "citation_grounding": f"{grounded}/{grounded_total}",
        "citation_grounding_wilson": wilson_ci(grounded, grounded_total),
        "citation_accuracy": f"{cit_hit}/{cit_total}",
        "citation_accuracy_wilson": wilson_ci(cit_hit, cit_total),
        "ece_10bin": ece_val, "ece_bins": ece_bins,
        "mean_conf": round(sum(confs) / len(confs), 4) if confs else None,
        "mean_conf_correct": round(sum(conf_ok) / len(conf_ok), 4) if conf_ok else None,
        "mean_conf_wrong": round(sum(conf_bad) / len(conf_bad), 4) if conf_bad else None,
        "latency_ms_per_run": lat,
        "unstable_clauses": {c: v for c, v in verdicts.items() if len(set(v)) > 1},
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
