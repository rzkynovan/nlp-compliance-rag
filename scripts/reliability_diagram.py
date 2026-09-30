"""
Reliability diagram + ECE (R8 / S-01) dari file hasil evaluation_runner.

Menggabungkan beberapa run (mis. hasil --repeat 3), lalu menggambar:
  - atas : akurasi per bin confidence (10 bin) vs garis kalibrasi sempurna
  - bawah: jumlah prediksi per bin
ECE dihitung dengan fungsi yang sama seperti scripts/semhas_metrics.py.
Confidence = skor kepercayaan verbal LLM (overall_confidence), benar = correct_6.

Contoh:
    python scripts/reliability_diagram.py --label "GPT-5.4-mini" \\
        data/audit_results/eval_openai_gpt-5.4-mini_query_aware_20260927_164235.json \\
        data/audit_results/eval_openai_gpt-5.4-mini_query_aware_20260927_164312.json \\
        data/audit_results/eval_openai_gpt-5.4-mini_query_aware_20260927_164347.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))
from semhas_metrics import ece  # noqa: E402

BINS = 10


def load_predictions(files):
    confs, corrects = [], []
    for f in files:
        run = json.load(open(f))
        if run.get("invalid") or any(x.get("error") for x in run["results"]):
            sys.exit(f"TIDAK VALID — run berisi error API: {f}")
        for x in run["results"]:
            if x.get("confidence") is not None:
                confs.append(float(x["confidence"]))
                corrects.append(bool(x["correct_6"]))
    if not confs:
        sys.exit("Tidak ada prediksi dengan confidence.")
    return confs, corrects


def bin_stats(confs, corrects, bins=BINS):
    stats = []
    for b in range(bins):
        items = [(c, k) for c, k in zip(confs, corrects) if min(int(c * bins), bins - 1) == b]
        if items:
            stats.append({
                "bin": b, "n": len(items),
                "acc": sum(k for _, k in items) / len(items),
                "conf": sum(c for c, _ in items) / len(items),
            })
        else:
            stats.append({"bin": b, "n": 0, "acc": None, "conf": None})
    return stats


def id_num(x, digits=3):
    return f"{x:.{digits}f}".replace(".", ",")


def plot(confs, corrects, label, out_path):
    ece_val, _ = ece(confs, corrects, BINS)
    stats = bin_stats(confs, corrects)
    width = 1 / BINS
    lefts = [s["bin"] * width for s in stats]

    fig, (ax, axh) = plt.subplots(
        2, 1, figsize=(5.2, 6.2), sharex=True,
        gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08},
    )
    ax.plot([0, 1], [0, 1], "--", color="#888888", linewidth=1, label="Kalibrasi sempurna")
    filled = [s for s in stats if s["n"]]
    ax.bar([s["bin"] * width for s in filled], [s["acc"] for s in filled], width=width,
           align="edge", color="#1B5CB0", edgecolor="white", label="Akurasi per bin")
    # Selisih digambar dari nilai terkecil ke terbesar agar tidak menimpa batang akurasi
    # (overconfident: di atas akurasi; underconfident: di atas confidence, akurasi tetap terlihat)
    ax.bar([s["bin"] * width for s in filled],
           [abs(s["conf"] - s["acc"]) for s in filled],
           bottom=[min(s["conf"], s["acc"]) for s in filled],
           width=width, align="edge", color="none", edgecolor="#B03A2E", hatch="///",
           linewidth=0.8, label="Selisih |confidence − akurasi|")
    ax.scatter([s["bin"] * width + width / 2 for s in filled], [s["conf"] for s in filled],
               marker="_", s=260, color="#B03A2E", zorder=3, label="Rerata confidence bin")
    ax.set_ylim(0, 1.02)
    ax.set_yticks([i / 5 for i in range(6)])
    ax.set_yticklabels([id_num(i / 5, 1) for i in range(6)])
    ax.set_ylabel("Akurasi (6 kelas)")
    ax.set_title(f"{label}  —  ECE = {id_num(ece_val, 4)}  (n = {len(confs)})", fontsize=11)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.grid(alpha=0.25)

    axh.bar(lefts, [s["n"] for s in stats], width=width, align="edge",
            color="#56627A", edgecolor="white")
    for s in stats:
        if s["n"]:
            axh.text(s["bin"] * width + width / 2, s["n"], str(s["n"]),
                     ha="center", va="bottom", fontsize=8)
    axh.set_xlim(0, 1)
    axh.set_ylim(0, max(s["n"] for s in stats) * 1.3)
    axh.set_xticks([i / BINS for i in range(BINS + 1)])
    axh.set_xticklabels([id_num(i / BINS, 1) for i in range(BINS + 1)], fontsize=8)
    axh.set_xlabel("Confidence (skor kepercayaan verbal)")
    axh.set_ylabel("Jumlah")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return ece_val, stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--label", required=True, help="Nama model untuk judul, mis. 'GPT-5.4-mini'")
    ap.add_argument("--out", default=None, help="Default: data/audit_results/figures/reliability_<label>.png")
    args = ap.parse_args()

    slug = re.sub(r"[^a-z0-9.]+", "-", args.label.lower()).strip("-")
    out = Path(args.out) if args.out else _ROOT / "data" / "audit_results" / "figures" / f"reliability_{slug}.png"
    confs, corrects = load_predictions(args.files)
    ece_val, stats = plot(confs, corrects, args.label, out)
    print(json.dumps({
        "label": args.label, "files": args.files, "n": len(confs), "ece_10bin": ece_val,
        "bins": [{k: (round(v, 4) if isinstance(v, float) else v) for k, v in s.items()}
                 for s in stats if s["n"]],
        "figure": str(out),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
