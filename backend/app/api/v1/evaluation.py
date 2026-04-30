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

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import require_advanced
from app.models.user import UserResponse

router = APIRouter(prefix="/evaluation", tags=["evaluation"], dependencies=[Depends(require_advanced)])

# Golden dataset — mirrored from src/evaluation_runner.py
GROUND_TRUTH = [
    {"clause_id": "BAB1-01", "clause": "SOP ini mengatur standar operasional layanan uang elektronik \"NusantaraPay\" (selanjutnya disebut \"Perusahaan\").", "expected_status": "NOT_ADDRESSED", "expected_bi": "NOT_ADDRESSED", "expected_ojk": "NOT_ADDRESSED", "category": "GENERAL", "violated_articles": [], "error_description": "Klausa netral — tidak mengatur aspek yang diatur regulasi BI/OJK secara spesifik."},
    {"clause_id": "BAB1-02", "clause": "SOP ini wajib dipatuhi oleh seluruh karyawan dan mitra kerja Perusahaan.", "expected_status": "NOT_ADDRESSED", "expected_bi": "NOT_ADDRESSED", "expected_ojk": "NOT_ADDRESSED", "category": "GENERAL", "violated_articles": [], "error_description": "Klausa administratif internal — di luar cakupan regulasi BI/OJK."},
    {"clause_id": "BAB2-01", "clause": "Perusahaan wajib memperoleh persetujuan tertulis atau persetujuan elektronik (explicit consent) dari Nasabah sebelum mengumpulkan dan memproses Data Pribadi. Sebelum persetujuan diberikan, Perusahaan wajib menjelaskan secara tertulis dan/atau lisan mengenai tujuan pengumpulan data, jenis data yang dikumpulkan, serta konsekuensi dari persetujuan Nasabah.", "expected_status": "PARTIALLY_COMPLIANT", "expected_bi": "NOT_ADDRESSED", "expected_ojk": "PARTIALLY_COMPLIANT", "category": "PRIVACY", "violated_articles": ["POJK No. 22/2023 Pasal 23 Ayat 2"], "error_description": "Mencakup sub-elemen (A) consent dan (B) tujuan, namun tidak mencakup (C) standar keamanan, (D) hak akses/koreksi, (E) right to erasure, dan (F) larangan penjualan data."},
    {"clause_id": "BAB2-02", "clause": "Data Pribadi Nasabah akan dienkripsi menggunakan standar keamanan AES-256 baik saat in-transit maupun at-rest.", "expected_status": "PARTIALLY_COMPLIANT", "expected_bi": "NOT_ADDRESSED", "expected_ojk": "PARTIALLY_COMPLIANT", "category": "SECURITY", "violated_articles": ["POJK No. 22/2023 Pasal 23 Ayat 2"], "error_description": "Hanya mencakup sub-elemen (C) standar keamanan teknis — tidak mencakup (A) consent, (B) tujuan, (D) hak akses/koreksi, (E) right to erasure, (F) larangan penjualan."},
    {"clause_id": "BAB2-03", "clause": "Nasabah berhak untuk meminta penghapusan permanen (Right to Erasure) atas Data Pribadi mereka kapan saja melalui aplikasi, dan Perusahaan wajib memprosesnya selambat-lambatnya 3x24 jam.", "expected_status": "PARTIALLY_COMPLIANT", "expected_bi": "NOT_ADDRESSED", "expected_ojk": "PARTIALLY_COMPLIANT", "category": "PRIVACY", "violated_articles": ["POJK No. 22/2023 Pasal 23 Ayat 2"], "error_description": "Hanya mencakup sub-elemen (E) right to erasure — tidak mencakup (A) consent, (B) tujuan, (C) keamanan, (D) hak akses/koreksi, (F) larangan penjualan."},
    {"clause_id": "BAB2-04", "clause": "Data Pribadi Nasabah tidak akan pernah dijual kepada pihak ketiga mana pun tanpa izin eksplisit yang terpisah.", "expected_status": "PARTIALLY_COMPLIANT", "expected_bi": "NOT_ADDRESSED", "expected_ojk": "PARTIALLY_COMPLIANT", "category": "PRIVACY", "violated_articles": ["POJK No. 22/2023 Pasal 23 Ayat 2"], "error_description": "Hanya mencakup sub-elemen (F) larangan penjualan — tidak mencakup (A) consent, (B) tujuan, (C) keamanan, (D) hak akses/koreksi, (E) right to erasure."},
    {"clause_id": "BAB3-01", "clause": "Segala bentuk pengaduan atau keluhan nasabah hanya dapat diterima pada jam operasional kerja, Senin hingga Jumat (10:00 - 15:00 WIB). Keluhan yang masuk di luar jam tersebut akan diabaikan.", "expected_status": "NON_COMPLIANT", "expected_bi": "NOT_ADDRESSED", "expected_ojk": "NON_COMPLIANT", "category": "COMPLAINT", "violated_articles": ["POJK No. 22/2023 Pasal 69 Ayat 3"], "error_description": "Layanan pengaduan hanya 5 jam/hari (10:00–15:00) dan ditolak di luar jam tersebut. POJK Pasal 69 Ayat 3 mewajibkan ketersediaan layanan pengaduan yang memadai."},
    {"clause_id": "BAB3-02", "clause": "Tim Customer Service memiliki waktu maksimal 60 hari kerja sejak keluhan diterima untuk menyelesaikan masalah nasabah dan memberikan kompensasi (jika ada).", "expected_status": "NON_COMPLIANT", "expected_bi": "NOT_ADDRESSED", "expected_ojk": "NON_COMPLIANT", "category": "COMPLAINT", "violated_articles": ["POJK No. 22/2023 Pasal 75 Ayat 1"], "error_description": "SLA 60 hari kerja jauh melebihi batas maksimal POJK: 20 hari kerja (dengan perpanjangan 10 hari dalam kondisi tertentu)."},
    {"clause_id": "BAB3-03", "clause": "Nasabah yang memberikan rating bintang 1 pada aplikasi secara otomatis akan dibekukan sementara akunnya selama 7 hari tanpa pemberitahuan sebelumnya untuk \"investigasi keamanan\".", "expected_status": "NON_COMPLIANT", "expected_bi": "NOT_ADDRESSED", "expected_ojk": "NON_COMPLIANT", "category": "CONSUMER_RIGHTS", "violated_articles": ["POJK No. 22/2023 Pasal 46 Ayat 2"], "error_description": "Pembekuan akun otomatis tanpa pemberitahuan berdasarkan rating — klausula sepihak yang merugikan konsumen, melanggar Pasal 46 Ayat 2 POJK 22/2023."},
    {"clause_id": "BAB4-01", "clause": "Akun Unverified (Belum KYC): Nasabah yang belum mengunggah KTP (Unregistered) dapat menyimpan saldo maksimal hingga Rp 10.000.000 (Sepuluh Juta Rupiah).", "expected_status": "NON_COMPLIANT", "expected_bi": "NON_COMPLIANT", "expected_ojk": "NOT_ADDRESSED", "category": "LIMITS", "violated_articles": ["PBI No. 23/6/PBI/2021 Pasal 160 Ayat 1"], "error_description": "Batas saldo unverified Rp 10.000.000 melebihi batas maksimal PBI: Rp 2.000.000."},
    {"clause_id": "BAB4-02", "clause": "Akun Verified (Sudah KYC): Nasabah yang sudah diverifikasi identitasnya dapat menyimpan saldo maksimal Rp 500.000.000 (Lima Ratus Juta Rupiah).", "expected_status": "NON_COMPLIANT", "expected_bi": "NON_COMPLIANT", "expected_ojk": "NOT_ADDRESSED", "category": "LIMITS", "violated_articles": ["PBI No. 23/6/PBI/2021 Pasal 160 Ayat 1"], "error_description": "Batas saldo verified Rp 500.000.000 melebihi batas maksimal PBI: Rp 10.000.000."},
    {"clause_id": "BAB4-03", "clause": "Batas transaksi masuk bulanan (Monthly Incoming Limit) untuk semua pengguna tidak dibatasi untuk mendorong pertumbuhan Gross Transaction Value (GTV) perusahaan.", "expected_status": "NON_COMPLIANT", "expected_bi": "NON_COMPLIANT", "expected_ojk": "NOT_ADDRESSED", "category": "LIMITS", "violated_articles": ["PBI No. 23/6/PBI/2021 Pasal 160 Ayat 2"], "error_description": "Tidak ada batasan transaksi masuk — melanggar PBI yang menetapkan batas Rp 20.000.000/bulan."},
]

AUDIT_RESULTS_DIR = Path("/app/data/audit_results")


def _load_latest_predictions() -> dict:
    """Load latest GPT-5.4-mini evaluation results if available."""
    if not AUDIT_RESULTS_DIR.exists():
        return {}
    files = sorted(
        AUDIT_RESULTS_DIR.glob("eval_openai_gpt-5.4-mini_*.json"),
        reverse=True
    )
    if not files:
        return {}
    try:
        with open(files[0]) as f:
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
        files = sorted(AUDIT_RESULTS_DIR.glob("eval_openai_gpt-5.4-mini_*.json"), reverse=True)
        if files:
            eval_file = files[0].name

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
