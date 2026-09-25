"""
evaluation.py — Golden dataset endpoint for testing documentation.

GET /evaluation/golden-dataset
  Returns 12 golden dataset clauses with ground truth labels and
  the latest system predictions (from most recent evaluation JSON if available).

Advanced users only.
"""

import json
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


def _latest_eval_file() -> Optional[Path]:
    """
    File evaluasi GPT-5.4-mini terbaru dengan konfigurasi proposal
    (RETRIEVAL_STRATEGY=query_aware). Run ablation (dense / rrf_equal) diabaikan.
    Nama lama tanpa strategi (sebelum Phase 14) tetap dikenali sebagai fallback.
    """
    if not AUDIT_RESULTS_DIR.exists():
        return None
    files = [
        f for f in AUDIT_RESULTS_DIR.glob("eval_openai_gpt-5.4-mini_*.json")
        if not any(tag in f.name for tag in ("_dense_", "_rrf_equal_"))
    ]
    return max(files, key=lambda f: f.stat().st_mtime) if files else None


def _load_latest_predictions() -> dict:
    """Load latest GPT-5.4-mini evaluation results if available."""
    latest = _latest_eval_file()
    if latest is None:
        return {}
    try:
        with open(latest) as f:
            data = json.load(f)
        return {r["clause_id"]: r for r in data.get("results", [])}
    except Exception:
        return {}


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
    items: List[GoldenDatasetItem]


@router.get("/golden-dataset", response_model=GoldenDatasetResponse)
def get_golden_dataset():
    predictions = _load_latest_predictions()
    has_predictions = bool(predictions)
    eval_file = None

    if has_predictions:
        latest = _latest_eval_file()
        eval_file = latest.name if latest else None

    items = []
    correct_count = 0

    for gt in GROUND_TRUTH:
        pred = predictions.get(gt["clause_id"], {})
        predicted_status = pred.get("predicted_status")
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
        evaluation_file=eval_file,
        items=items,
    )
