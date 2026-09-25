"""Test evaluation_runner — regresi bug MRR/Hit Rate = 0 dan metrik 6 kelas."""

from types import SimpleNamespace

import pytest

import evaluation_runner as er


def _evidence(*pasals, regulation="POJK 22/2023"):
    return [{"rank": i, "pasal_number": p, "regulation": regulation} for i, p in enumerate(pasals, 1)]


def _audit_result(final="NON_COMPLIANT", bi=None, ojk=None):
    # AuditResult.bi_verdict / ojk_verdict berupa dict (model_dump) — penyebab bug lama
    return SimpleNamespace(
        final_verdict=SimpleNamespace(final_status=final, overall_confidence=0.8),
        bi_verdict=bi or {}, ojk_verdict=ojk or {},
    )


SAMPLE_OJK = {
    "clause_id": "BAB3-02", "category": "COMPLAINT", "clause": "SLA 60 hari kerja",
    "expected_status": "NON_COMPLIANT", "expected_bi": "NOT_ADDRESSED", "expected_ojk": "NON_COMPLIANT",
    "violated_articles": ["POJK No. 22/2023 Pasal 75 Ayat 1"],
}


def test_golden_dataset_single_source():
    samples = er.load_golden_dataset()
    assert len(samples) == 12
    assert {s["expected_status"] for s in samples} == {"NOT_ADDRESSED", "PARTIALLY_COMPLIANT", "NON_COMPLIANT"}


@pytest.mark.parametrize("article,expected", [
    ("PBI No. 23/6/PBI/2021 Pasal 160 Ayat 1", {"agent": "BI", "reg_num": "23/6", "pasal": "160"}),
    ("POJK No. 22/2023 Pasal 23 Ayat 2", {"agent": "OJK", "reg_num": "22", "pasal": "23"}),
    ("tanpa pasal", {}),
])
def test_parse_qrel(article, expected):
    assert er.parse_qrel(article) == expected


def test_build_result_reads_dict_verdicts():
    ojk = {"verdict": "NON_COMPLIANT", "evidence": _evidence("69", "75"),
           "violated_articles": [{"article": "Pasal 75 Ayat 1", "grounded": True}],
           "retrieval_mode": "hybrid", "sparse_boost": 0.3}
    bi = {"verdict": "NOT_ADDRESSED", "evidence": [], "violated_articles": [], "sparse_boost": 0.3}
    r = er.build_result(SAMPLE_OJK, _audit_result(bi=bi, ojk=ojk), latency=100)
    assert r["predicted_bi"] == "NOT_ADDRESSED"      # dulu selalu "UNCLEAR"
    assert r["predicted_ojk"] == "NON_COMPLIANT"
    assert r["evidence_ojk"][1]["pasal_number"] == "75"
    assert r["citation_grounded"] == [True]
    assert r["correct"] and r["correct_6"]


def test_mrr_hitrate_uses_metadata_of_regulator_topk():
    ojk = {"verdict": "NON_COMPLIANT", "evidence": _evidence("69", "70", "71", "75")}
    r = er.build_result(SAMPLE_OJK, _audit_result(ojk=ojk), latency=1)
    out = er.compute_mrr_hitrate([r])
    assert out["mrr"] == 0.25
    assert out["hit_rate_at_3"] == 0.0 and out["hit_rate_at_5"] == 1.0
    assert out["evaluated_clauses"] == 1


def test_mrr_ignores_same_pasal_from_other_regulation():
    ojk = {"verdict": "NON_COMPLIANT", "evidence": _evidence("75", regulation="PBI 23/6/PBI/2021")}
    r = er.build_result(SAMPLE_OJK, _audit_result(ojk=ojk), latency=1)
    assert er.compute_mrr_hitrate([r])["mrr"] == 0.0


def test_six_class_metrics_keep_needs_review_separate():
    r = er.build_result(SAMPLE_OJK, _audit_result(final="NEEDS_REVIEW"), latency=1)
    assert r["predicted_norm"] == "NON_COMPLIANT"    # skema 4 kelas lama (konservatif)
    assert r["predicted_6"] == "NEEDS_REVIEW"
    m4 = er.compute_metrics([r])
    m6 = er.compute_metrics([r], classes=er.SIX_CLASSES, pred_key="predicted_6", exp_key="expected_6")
    assert m4["accuracy"] == 1.0 and m6["accuracy"] == 0.0


def test_wilson_ci():
    lo, hi = er.wilson_ci(24, 24)
    assert lo == pytest.approx(0.8619, abs=1e-3) and hi == 1.0
    assert er.wilson_ci(0, 0) == (0.0, 0.0)


def test_citation_grounding_rate():
    rows = [{"citation_grounded": [True, False, None]}, {"citation_grounded": [True]}]
    out = er.compute_citation_grounding(rows)
    assert out == {"citation_grounding_rate": round(2 / 3, 4), "citations_checked": 3}
