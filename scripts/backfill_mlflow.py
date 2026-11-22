"""
Catat ulang file hasil evaluation_runner (data/audit_results/eval_*.json) ke MLflow.

Run Semhas dijalankan dengan --no-mlflow, sehingga MLflow (dan halaman Eksperimen
di website) kosong. Skrip ini tidak memanggil LLM: isi run diambil dari file JSON,
waktu mulai run memakai timestamp evaluasi aslinya, dan run yang termasuk ringkasan
repeat_*_x3.json diberi tag ``repeat_group``.

Run tidak valid (berisi error API) dilewati. Aman dijalankan ulang: run dengan nama
yang sudah ada di MLflow tidak dicatat lagi.

Contoh:
    python scripts/backfill_mlflow.py --mlflow-uri http://localhost:5001
    # di server (container backend sudah punya MLFLOW_TRACKING_URI):
    docker compose exec backend python scripts/backfill_mlflow.py
"""

import argparse
import glob
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from evaluation_runner import _log_to_mlflow, count_errors  # noqa: E402


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mlflow-uri", default=None,
                        help="MLflow tracking URI (default: $MLFLOW_TRACKING_URI)")
    parser.add_argument("--results-dir", default=str(ROOT / "data" / "audit_results"))
    parser.add_argument("--dry-run", action="store_true", help="Tampilkan saja, jangan catat")
    args = parser.parse_args()

    uri = args.mlflow_uri or os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5001")

    repeat_group = {}
    for f in sorted(glob.glob(os.path.join(args.results_dir, "repeat_*.json"))):
        for run in json.load(open(f, encoding="utf-8")).get("runs", []):
            repeat_group[run] = Path(f).stem

    existing = set()
    if not args.dry_run:
        from mlflow.tracking import MlflowClient
        client = MlflowClient(uri)
        exp = client.get_experiment_by_name("compliance_evaluation")
        if exp:
            existing = {r.info.run_name for r in client.search_runs([exp.experiment_id], max_results=5000)}

    logged = skipped = 0
    for f in sorted(glob.glob(os.path.join(args.results_dir, "eval_*.json"))):
        output = json.load(open(f, encoding="utf-8"))
        name = output["run_name"]
        if output.get("invalid") or count_errors(output.get("results", [])):
            print(f"  lewati (run tidak valid): {name}")
            skipped += 1
            continue
        if name in existing:
            print(f"  lewati (sudah ada): {name}")
            skipped += 1
            continue
        start_ms = int(datetime.fromisoformat(output["timestamp"]).timestamp() * 1000)
        tags = {"backfilled": "true"}
        if name in repeat_group:
            tags["repeat_group"] = repeat_group[name]
        if args.dry_run:
            print(f"  [dry-run] {name}  {tags}")
        else:
            _log_to_mlflow(output, name, uri, start_time_ms=start_ms, extra_tags=tags)
        logged += 1

    print(f"Selesai: {logged} run dicatat, {skipped} dilewati (MLflow: {uri})")


if __name__ == "__main__":
    main()
