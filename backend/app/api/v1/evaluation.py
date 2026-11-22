"""
evaluation.py — Golden dataset endpoint for testing documentation.

GET /evaluation/golden-dataset
  Returns 12 golden dataset clauses with ground truth labels and
  the latest system predictions (from most recent evaluation JSON if available).

Advanced users only.
"""

import json
import re
from pathlib import Path
from typing import List, Optional

import yaml

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import require_advanced
from app.models.user import UserResponse

router = APIRouter(prefix="/evaluation", tags=["evaluation"], dependencies=[Depends(require_advanced)])

# Golden dataset — sumber tunggal: data/golden_dataset.yaml
# (dipakai juga oleh src/evaluation_runner.py)
_GOLDEN_CANDIDATES = [
    Path("/app/data/golden_dataset.yaml"),                                   # Docker
    Path(__file__).resolve().parents[4] / "data" / "golden_dataset.yaml",   # lokal
]


def _load_golden_dataset() -> list:
    for path in _GOLDEN_CANDIDATES:
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return yaml.safe_load(f)["samples"]
    return []


GROUND_TRUTH = _load_golden_dataset()

AUDIT_RESULTS_DIR = Path("/app/data/audit_results")


_TS_RE = re.compile(r"(\d{8}_\d{6})\.json$")


def _is_valid_run(data: dict) -> bool:
    return not data.get("invalid") and not any(r.get("error") for r in data.get("results", []))


def _latest_eval() -> Optional[tuple]:
    """
    (path, isi) file evaluasi GPT-5.4-mini terbaru yang valid dengan konfigurasi proposal
    (RETRIEVAL_STRATEGY=query_aware). Run ablation (dense / rrf_equal) dan run yang
    berisi error API diabaikan. Urutan memakai timestamp di nama file, bukan mtime
    (mtime sama semua setelah git checkout di server).
    """
    if not AUDIT_RESULTS_DIR.exists():
        return None
    files = sorted(
        (f for f in AUDIT_RESULTS_DIR.glob("eval_openai_gpt-5.4-mini_*.json")
         if not any(tag in f.name for tag in ("_dense_", "_rrf_equal_")) and _TS_RE.search(f.name)),
        key=lambda f: _TS_RE.search(f.name).group(1),
        reverse=True,
    )
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if _is_valid_run(data):
            return f, data
    return None


def _repeat_summary(run_name: str) -> Optional[dict]:
    """Ringkasan repeat_*_xN.json yang memuat run ini (rerata ± SD di laporan)."""
    for f in sorted(AUDIT_RESULTS_DIR.glob("repeat_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if run_name in data.get("runs", []):
            acc = data.get("metrics", {}).get("accuracy_6class", {})
            return {
                "file": f.name,
                "n_runs": data.get("n_runs"),
                "run_index": data["runs"].index(run_name) + 1,
                "accuracy_mean": acc.get("mean"),
                "accuracy_sd": acc.get("sd"),
            }
    return None


class RepeatSummary(BaseModel):
    file: str
    n_runs: Optional[int] = None
    run_index: int
    accuracy_mean: Optional[float] = None
    accuracy_sd: Optional[float] = None


class GoldenDatasetItem(BaseModel):
    clause_id: str
    clause: str
    category: str
    expected_status: str
    expected_bi: str
    expected_ojk: str
    violated_articles: List[str]
    error_description: str
    predicted_status: Optional[str] = None
    predicted_bi: Optional[str] = None
    predicted_ojk: Optional[str] = None
    is_correct: Optional[bool] = None
    latency_ms: Optional[float] = None


class GoldenDatasetResponse(BaseModel):
    total: int
    correct: Optional[int] = None
    accuracy: Optional[float] = None
    has_predictions: bool
    evaluation_file: Optional[str] = None
    evaluation_timestamp: Optional[str] = None
    model: Optional[str] = None
    retrieval_strategy: Optional[str] = None
    repeat: Optional[RepeatSummary] = None
    items: List[GoldenDatasetItem]


@router.get("/golden-dataset", response_model=GoldenDatasetResponse)
def get_golden_dataset():
    latest = _latest_eval()
    eval_path, eval_data = latest if latest else (None, {})
    predictions = {r["clause_id"]: r for r in eval_data.get("results", [])}
    has_predictions = bool(predictions)

    items = []
    correct_count = 0

    for gt in GROUND_TRUTH:
        pred = predictions.get(gt["clause_id"], {})
        # evaluation_runner menulis verdik akhir sebagai `predicted_6` (skema 6 kelas);
        # `predicted_status` adalah nama kunci lama.
        predicted_status = pred.get("predicted_status") or pred.get("predicted_6") or pred.get("predicted")
        predicted_bi     = pred.get("predicted_bi")
        predicted_ojk    = pred.get("predicted_ojk")
        is_correct       = (predicted_status == gt["expected_status"]) if predicted_status else None
        if is_correct:
            correct_count += 1

        items.append(GoldenDatasetItem(
            clause_id=gt["clause_id"],
            clause=gt["clause"],
            category=gt["category"],
            expected_status=gt["expected_status"],
            expected_bi=gt["expected_bi"],
            expected_ojk=gt["expected_ojk"],
            violated_articles=gt["violated_articles"],
            error_description=gt["error_description"],
            predicted_status=predicted_status,
            predicted_bi=predicted_bi,
            predicted_ojk=predicted_ojk,
            is_correct=is_correct,
            latency_ms=pred.get("latency_ms"),
        ))

    accuracy = round(correct_count / len(items), 4) if has_predictions else None

    return GoldenDatasetResponse(
        total=len(items),
        correct=correct_count if has_predictions else None,
        accuracy=accuracy,
        has_predictions=has_predictions,
        evaluation_file=eval_path.name if eval_path else None,
        evaluation_timestamp=eval_data.get("timestamp"),
        model=eval_data.get("model"),
        retrieval_strategy=(eval_data.get("retrieval_setup") or {}).get("strategy"),
        repeat=_repeat_summary(eval_data["run_name"]) if eval_data.get("run_name") else None,
        items=items,
    )
