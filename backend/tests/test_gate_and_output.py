"""
test_gate_and_output.py — keselarasan RAGAuditService dengan proposal:
  - Gate: delta(q) = 1[P(klausul | q) >= threshold]   (Persamaan 2.17)
  - Status penolakan gate: NOT_REGULATION_CLAUSE
  - Evidence trail dari chunk Top-K (Subbab 3.3.3)
  - Risk score satu sumber (ConflictResolverAgent)
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.api.v1.audit import _map_risk_score, _map_status
from app.models.audit import ComplianceStatus


@pytest.fixture
def service(mock_settings, tmp_path):
    mock_settings.CHROMADB_PERSIST_DIR = str(tmp_path / "chroma")
    mock_settings.SOP_GATE_THRESHOLD = 0.5
    with patch("app.services.rag_service.OpenAI"), \
         patch("app.services.rag_service.AuditCache"), \
         patch("app.services.rag_service.cost_tracker"):
        from app.services.rag_service import RAGAuditService
        svc = RAGAuditService()
    return svc, mock_settings


def _gate(is_sop, confidence):
    return SimpleNamespace(predict=lambda text: SimpleNamespace(
        is_sop=is_sop, confidence=confidence, model="indobert"))


@pytest.mark.parametrize("is_sop,confidence,expected", [
    (True, 0.51, True),     # P(klausul)=0.51 ≥ 0.5 → lolos
    (False, 0.51, False),   # P(klausul)=0.49 < 0.5 → ditolak
    (False, 0.70, False),   # dulu lolos karena confidence < 0.8
    (True, 0.99, True),
])
def test_gate_decision_threshold(service, is_sop, confidence, expected):
    svc, settings = service
    svc._gate = _gate(is_sop, confidence)
    with patch("app.services.rag_service.settings", settings):
        out = svc._run_gate("klausul")
    assert out["is_sop"] is expected
    assert out["p_clause"] == pytest.approx(confidence if is_sop else 1 - confidence, abs=1e-4)


def test_not_regulation_clause_response(service):
    svc, _ = service
    resp = svc._build_not_sop_response("halo", "rid", {"confidence": 0.9, "model": "indobert"})
    assert resp["final_status"] == "NOT_REGULATION_CLAUSE"
    assert resp["gate_decision"] == "NOT_REGULATION_CLAUSE"
    assert _map_status("NOT_REGULATION_CLAUSE") == ComplianceStatus.NOT_ADDRESSED


def test_evidence_trail_built_from_topk(service):
    svc, _ = service
    ev = [{"regulator": "OJK", "regulation": "POJK 22/2023", "bab": "BAB II",
           "article": "Pasal 46 Ayat 2", "relevance_score": 0.92, "rank": 1}]
    result = SimpleNamespace(
        bi_verdict={}, ojk_verdict={"agent_id": "OJK_SPECIALIST", "evidence": ev},
        final_verdict=SimpleNamespace(risk_score="CRITICAL"),
    )
    [item] = svc._build_evidence_trail(result)
    assert item == {"agent": "OJK_SPECIALIST", "regulator": "OJK", "document": "POJK 22/2023",
                    "bab": "BAB II", "pasal": "Pasal 46 Ayat 2", "relevance_score": 0.92, "rank": 1}
    assert svc._calculate_risk_score(result) == "CRITICAL"


def test_risk_score_mapping_includes_critical():
    assert _map_risk_score("CRITICAL") == 1.0
    assert _map_risk_score("LOW") == 0.25
