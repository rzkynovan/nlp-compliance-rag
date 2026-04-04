"""
test_audit_api.py — unit tests for the audit API layer.

Tests:
  - Helper functions: _map_status, _map_risk_score, _extract_verdict_data
  - FastAPI endpoints via TestClient (all external deps mocked)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.models.audit import ComplianceStatus, AgentVerdict, EvidenceItem
from app.api.v1.audit import (
    _map_status,
    _map_risk_score,
    _extract_verdict_data,
)


# ── _map_status ───────────────────────────────────────────────────────────────

class TestMapStatus:
    @pytest.mark.parametrize("raw,expected", [
        ("COMPLIANT",           ComplianceStatus.COMPLIANT),
        ("NON_COMPLIANT",       ComplianceStatus.NON_COMPLIANT),
        ("PARTIALLY_COMPLIANT", ComplianceStatus.PARTIALLY_COMPLIANT),
        ("NEEDS_REVIEW",        ComplianceStatus.NEEDS_REVIEW),
        ("NOT_ADDRESSED",       ComplianceStatus.NOT_ADDRESSED),
        ("UNCLEAR",             ComplianceStatus.UNCLEAR),
    ])
    def test_known_statuses(self, raw, expected):
        assert _map_status(raw) == expected

    def test_unknown_status_defaults_to_unclear(self):
        assert _map_status("RANDOM_VALUE") == ComplianceStatus.UNCLEAR

    def test_empty_string_defaults_to_unclear(self):
        assert _map_status("") == ComplianceStatus.UNCLEAR

    def test_case_sensitive(self):
        # "compliant" (lowercase) should NOT match — map is case-sensitive
        assert _map_status("compliant") == ComplianceStatus.UNCLEAR


# ── _map_risk_score ───────────────────────────────────────────────────────────

class TestMapRiskScore:
    def test_string_low(self):
        assert _map_risk_score("LOW") == 0.25

    def test_string_medium(self):
        assert _map_risk_score("MEDIUM") == 0.5

    def test_string_high(self):
        assert _map_risk_score("HIGH") == 0.75

    def test_lowercase_string(self):
        assert _map_risk_score("low") == 0.25
        assert _map_risk_score("high") == 0.75

    def test_float_passthrough(self):
        assert _map_risk_score(0.8) == 0.8
        assert _map_risk_score(0.0) == 0.0

    def test_none_returns_half(self):
        assert _map_risk_score(None) == 0.5

    def test_unknown_string_returns_half(self):
        assert _map_risk_score("EXTREME") == 0.5


# ── _extract_verdict_data ─────────────────────────────────────────────────────

class TestExtractVerdictData:
    def test_none_input_returns_unclear_verdict(self):
        verdict = _extract_verdict_data(None, "BI_SPECIALIST")
        assert isinstance(verdict, AgentVerdict)
        assert verdict.agent_name == "BI_SPECIALIST"
        assert verdict.status == ComplianceStatus.UNCLEAR
        assert verdict.confidence == 0.5
        assert verdict.violations == []

    def test_dict_with_string_violations(self):
        raw = {
            "verdict": "NON_COMPLIANT",
            "confidence_score": 0.9,
            "violations": ["Pasal 160 melebihi saldo"],
            "evidence": [],
            "reasoning_trace": "Saldo melebihi batas",
        }
        verdict = _extract_verdict_data(raw, "BI_SPECIALIST")
        assert verdict.status == ComplianceStatus.NON_COMPLIANT
        assert verdict.confidence == 0.9
        assert "Pasal 160 melebihi saldo" in verdict.violations

    def test_dict_with_dict_violations(self):
        raw = {
            "verdict": "NON_COMPLIANT",
            "confidence_score": 0.85,
            "violations": [
                {"article": "Pasal 160", "description": "Melebihi batas saldo"}
            ],
            "evidence": [],
            "reasoning_trace": "test",
        }
        verdict = _extract_verdict_data(raw, "BI_SPECIALIST")
        assert len(verdict.violations) == 1
        assert "Pasal 160" in verdict.violations[0]
        assert "Melebihi batas saldo" in verdict.violations[0]

    def test_evidence_items_extracted(self):
        raw = {
            "verdict": "COMPLIANT",
            "confidence_score": 0.8,
            "violations": [],
            "evidence": [
                {
                    "regulation": "PBI 23/6/2021",
                    "article": "Pasal 5",
                    "article_text": "Batas saldo...",
                    "relevance_score": 0.95,
                }
            ],
            "reasoning_trace": "ok",
        }
        verdict = _extract_verdict_data(raw, "OJK_SPECIALIST")
        assert len(verdict.evidence) == 1
        assert verdict.evidence[0].regulation == "PBI 23/6/2021"
        assert verdict.evidence[0].relevance_score == 0.95

    def test_status_field_fallback(self):
        # Some agents return "status" instead of "verdict"
        raw = {
            "status": "COMPLIANT",
            "confidence": 0.75,
            "violations": [],
            "evidence": [],
            "reasoning_trace": "ok",
        }
        verdict = _extract_verdict_data(raw, "OJK_SPECIALIST")
        assert verdict.status == ComplianceStatus.COMPLIANT
        assert verdict.confidence == 0.75

    def test_confidence_field_fallback(self):
        raw = {
            "verdict": "UNCLEAR",
            "confidence": 0.6,    # "confidence" instead of "confidence_score"
            "violations": [],
            "evidence": [],
            "reasoning_trace": "unclear",
        }
        verdict = _extract_verdict_data(raw, "BI_SPECIALIST")
        assert verdict.confidence == 0.6


# ── FastAPI endpoints via TestClient ─────────────────────────────────────────

@pytest.fixture
def client(mock_settings):
    """
    Create a TestClient with the RAGAuditService fully mocked.
    We patch `get_rag_service` so no real OpenAI/ChromaDB calls occur.
    """
    from app.main import app

    mock_service = MagicMock()
    mock_service.analyze_with_rag = AsyncMock(return_value={
        "final_status": "COMPLIANT",
        "overall_confidence": 0.88,
        "risk_score": "LOW",
        "bi_verdict": {
            "verdict": "COMPLIANT",
            "confidence_score": 0.90,
            "violations": [],
            "evidence": [],
            "reasoning_trace": "No violations found",
        },
        "ojk_verdict": {
            "verdict": "COMPLIANT",
            "confidence_score": 0.85,
            "violations": [],
            "evidence": [],
            "reasoning_trace": "Consumer protection satisfied",
        },
        "violations": [],
        "recommendations": [],
        "analysis_mode": "multi_agent_rag",
        "latency_ms": 1200,
        "model_used": "gpt-4o-mini",
    })

    with patch("app.api.v1.audit.get_rag_service", return_value=mock_service):
        with TestClient(app) as c:
            import app.api.v1.audit as audit_mod
            audit_mod.audit_history.clear()
            yield c
            audit_mod.audit_history.clear()


class TestAnalyzeEndpoint:
    def test_success_200(self, client):
        resp = client.post(
            "/api/v1/audit/analyze",
            json={"clause": "Saldo maksimal akun unverified adalah Rp 2.000.000"},
        )
        assert resp.status_code == 200

    def test_response_has_required_fields(self, client):
        resp = client.post(
            "/api/v1/audit/analyze",
            json={"clause": "Test clause untuk audit kepatuhan"},
        )
        body = resp.json()
        required = {
            "request_id", "final_status", "overall_confidence",
            "risk_score", "bi_verdict", "ojk_verdict",
            "violations", "recommendations", "latency_ms",
        }
        assert required.issubset(body.keys())

    def test_final_status_is_compliant(self, client):
        resp = client.post(
            "/api/v1/audit/analyze",
            json={"clause": "Saldo maksimal Rp 2.000.000 untuk unverified"},
        )
        assert resp.json()["final_status"] == "COMPLIANT"

    def test_bi_ojk_verdict_present(self, client):
        resp = client.post(
            "/api/v1/audit/analyze",
            json={"clause": "Test clause"},
        )
        body = resp.json()
        assert body["bi_verdict"]["agent_name"] == "BI_SPECIALIST"
        assert body["ojk_verdict"]["agent_name"] == "OJK_SPECIALIST"

    def test_empty_clause_fails_validation(self, client):
        # Empty body
        resp = client.post("/api/v1/audit/analyze", json={})
        assert resp.status_code == 422

    def test_clause_with_regulator_and_top_k(self, client):
        resp = client.post(
            "/api/v1/audit/analyze",
            json={"clause": "Test clause", "regulator": "BI", "top_k": 3},
        )
        assert resp.status_code == 200

    def test_top_k_above_max_rejected(self, client):
        resp = client.post(
            "/api/v1/audit/analyze",
            json={"clause": "Test clause", "top_k": 999},
        )
        assert resp.status_code == 422

    def test_top_k_zero_rejected(self, client):
        resp = client.post(
            "/api/v1/audit/analyze",
            json={"clause": "Test clause", "top_k": 0},
        )
        assert resp.status_code == 422


class TestAuditHistoryEndpoint:
    def test_history_returns_list(self, client):
        resp = client.get("/api/v1/audit/history")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_history_populated_after_audit(self, client):
        client.post(
            "/api/v1/audit/analyze",
            json={"clause": "Saldo maksimal Rp 2.000.000"},
        )
        resp = client.get("/api/v1/audit/history")
        assert len(resp.json()) >= 1

    def test_history_item_fields(self, client):
        client.post(
            "/api/v1/audit/analyze",
            json={"clause": "Saldo test"},
        )
        history = client.get("/api/v1/audit/history").json()
        item = history[0]
        assert "request_id" in item
        assert "final_status" in item
        assert "overall_confidence" in item
        assert "latency_ms" in item

    def test_history_pagination_skip(self, client):
        # Run 3 audits then skip 2 — should get 1 item
        for i in range(3):
            client.post("/api/v1/audit/analyze", json={"clause": f"clause {i}"})
        resp = client.get("/api/v1/audit/history?skip=2&limit=10")
        assert len(resp.json()) == 1

    def test_history_pagination_limit(self, client):
        for i in range(5):
            client.post("/api/v1/audit/analyze", json={"clause": f"clause {i}"})
        resp = client.get("/api/v1/audit/history?skip=0&limit=2")
        assert len(resp.json()) == 2


class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_response_shape(self, client):
        body = client.get("/api/v1/health").json()
        assert "status" in body
