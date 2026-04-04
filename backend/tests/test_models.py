"""
test_models.py — unit tests for Pydantic models in app.models.audit.

Tests: field validation, enum values, default values,
boundary conditions, and response serialisation.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError as PydanticValidationError

from app.models.audit import (
    AuditRequest,
    AuditResponse,
    AgentVerdict,
    EvidenceItem,
    AuditHistoryItem,
    BatchAuditRequest,
    ComplianceStatus,
)


# ── ComplianceStatus enum ─────────────────────────────────────────────────────

class TestComplianceStatus:
    def test_all_values_exist(self):
        expected = {
            "COMPLIANT", "NON_COMPLIANT", "NEEDS_REVIEW",
            "NOT_ADDRESSED", "UNCLEAR", "PARTIALLY_COMPLIANT",
        }
        actual = {s.value for s in ComplianceStatus}
        assert actual == expected

    def test_is_string_enum(self):
        assert ComplianceStatus.COMPLIANT == "COMPLIANT"
        assert isinstance(ComplianceStatus.NON_COMPLIANT, str)


# ── EvidenceItem ──────────────────────────────────────────────────────────────

class TestEvidenceItem:
    def test_valid_item(self):
        item = EvidenceItem(
            regulation="PBI 23/6/2021",
            article="Pasal 160",
            article_text="Batas saldo...",
            relevance_score=0.9,
        )
        assert item.regulation == "PBI 23/6/2021"
        assert item.relevance_score == 0.9

    def test_relevance_score_at_boundaries(self):
        EvidenceItem(regulation="R", article="A", article_text="T", relevance_score=0.0)
        EvidenceItem(regulation="R", article="A", article_text="T", relevance_score=1.0)

    def test_relevance_score_below_zero_raises(self):
        with pytest.raises(PydanticValidationError):
            EvidenceItem(regulation="R", article="A", article_text="T", relevance_score=-0.1)

    def test_relevance_score_above_one_raises(self):
        with pytest.raises(PydanticValidationError):
            EvidenceItem(regulation="R", article="A", article_text="T", relevance_score=1.1)


# ── AgentVerdict ─────────────────────────────────────────────────────────────

class TestAgentVerdict:
    def test_valid_verdict(self):
        verdict = AgentVerdict(
            agent_name="BI_SPECIALIST",
            status=ComplianceStatus.NON_COMPLIANT,
            confidence=0.95,
            violations=["Pasal 160"],
            evidence=[],
            reasoning="Saldo melebihi batas",
        )
        assert verdict.agent_name == "BI_SPECIALIST"
        assert verdict.status == ComplianceStatus.NON_COMPLIANT

    def test_confidence_boundaries(self):
        AgentVerdict(agent_name="X", status=ComplianceStatus.COMPLIANT,
                     confidence=0.0, reasoning="ok")
        AgentVerdict(agent_name="X", status=ComplianceStatus.COMPLIANT,
                     confidence=1.0, reasoning="ok")

    def test_confidence_below_zero_raises(self):
        with pytest.raises(PydanticValidationError):
            AgentVerdict(agent_name="X", status=ComplianceStatus.COMPLIANT,
                         confidence=-0.01, reasoning="ok")

    def test_confidence_above_one_raises(self):
        with pytest.raises(PydanticValidationError):
            AgentVerdict(agent_name="X", status=ComplianceStatus.COMPLIANT,
                         confidence=1.01, reasoning="ok")

    def test_default_empty_lists(self):
        verdict = AgentVerdict(
            agent_name="X", status=ComplianceStatus.UNCLEAR,
            confidence=0.5, reasoning="unclear"
        )
        assert verdict.violations == []
        assert verdict.evidence == []

    def test_status_accepts_string(self):
        verdict = AgentVerdict(
            agent_name="X", status="COMPLIANT",
            confidence=0.8, reasoning="ok"
        )
        assert verdict.status == ComplianceStatus.COMPLIANT

    def test_invalid_status_raises(self):
        with pytest.raises(PydanticValidationError):
            AgentVerdict(agent_name="X", status="INVALID_STATUS",
                         confidence=0.5, reasoning="ok")


# ── AuditRequest ─────────────────────────────────────────────────────────────

class TestAuditRequest:
    def test_minimal_valid(self):
        req = AuditRequest(clause="Saldo maksimal Rp 2.000.000")
        assert req.clause == "Saldo maksimal Rp 2.000.000"
        assert req.regulator == "all"
        assert req.top_k == 5

    def test_all_fields(self):
        req = AuditRequest(
            clause="Test clause",
            clause_id="SOP-001",
            context="e-wallet context",
            top_k=3,
            regulator="BI",
        )
        assert req.clause_id == "SOP-001"
        assert req.top_k == 3
        assert req.regulator == "BI"

    def test_top_k_min_1(self):
        AuditRequest(clause="test", top_k=1)
        with pytest.raises(PydanticValidationError):
            AuditRequest(clause="test", top_k=0)

    def test_top_k_max_10(self):
        AuditRequest(clause="test", top_k=10)
        with pytest.raises(PydanticValidationError):
            AuditRequest(clause="test", top_k=11)

    def test_missing_clause_raises(self):
        with pytest.raises(PydanticValidationError):
            AuditRequest()  # type: ignore

    def test_optional_fields_default_none(self):
        req = AuditRequest(clause="test")
        assert req.clause_id is None
        assert req.context is None


# ── AuditResponse ─────────────────────────────────────────────────────────────

def _make_verdict(agent: str, status: ComplianceStatus) -> AgentVerdict:
    return AgentVerdict(
        agent_name=agent,
        status=status,
        confidence=0.9,
        reasoning="test reasoning",
    )


def _make_response(**overrides) -> AuditResponse:
    defaults = dict(
        request_id="req-001",
        clause="test clause",
        bi_verdict=_make_verdict("BI_SPECIALIST", ComplianceStatus.COMPLIANT),
        ojk_verdict=_make_verdict("OJK_SPECIALIST", ComplianceStatus.COMPLIANT),
        final_status=ComplianceStatus.COMPLIANT,
        overall_confidence=0.9,
        risk_score=0.1,
        latency_ms=1500.0,
    )
    defaults.update(overrides)
    return AuditResponse(**defaults)


class TestAuditResponse:
    def test_valid_response(self):
        resp = _make_response()
        assert resp.request_id == "req-001"
        assert resp.final_status == ComplianceStatus.COMPLIANT

    def test_overall_confidence_boundaries(self):
        _make_response(overall_confidence=0.0)
        _make_response(overall_confidence=1.0)

    def test_overall_confidence_out_of_range_raises(self):
        with pytest.raises(PydanticValidationError):
            _make_response(overall_confidence=1.1)
        with pytest.raises(PydanticValidationError):
            _make_response(overall_confidence=-0.1)

    def test_risk_score_boundaries(self):
        _make_response(risk_score=0.0)
        _make_response(risk_score=1.0)

    def test_risk_score_out_of_range_raises(self):
        with pytest.raises(PydanticValidationError):
            _make_response(risk_score=1.01)

    def test_default_timestamp_is_datetime(self):
        resp = _make_response()
        assert isinstance(resp.timestamp, datetime)

    def test_default_empty_lists(self):
        resp = _make_response()
        assert resp.violations == []
        assert resp.recommendations == []

    def test_violations_and_recommendations(self):
        resp = _make_response(
            violations=["Pasal 160: saldo lebih"],
            recommendations=["Kurangi batas saldo"],
        )
        assert len(resp.violations) == 1
        assert len(resp.recommendations) == 1

    def test_serialise_to_dict(self):
        resp = _make_response()
        d = resp.model_dump()
        assert "final_status" in d
        assert "bi_verdict" in d
        assert "ojk_verdict" in d


# ── AuditHistoryItem ──────────────────────────────────────────────────────────

class TestAuditHistoryItem:
    def test_valid(self):
        item = AuditHistoryItem(
            request_id="req-123",
            timestamp=datetime.now(),
            clause="test",
            final_status=ComplianceStatus.COMPLIANT,
            overall_confidence=0.9,
            latency_ms=1200.5,
        )
        assert item.request_id == "req-123"

    def test_missing_required_raises(self):
        with pytest.raises(PydanticValidationError):
            AuditHistoryItem(request_id="x")  # type: ignore


# ── BatchAuditRequest ─────────────────────────────────────────────────────────

class TestBatchAuditRequest:
    def test_single_clause(self):
        batch = BatchAuditRequest(clauses=[AuditRequest(clause="test")])
        assert len(batch.clauses) == 1

    def test_multiple_clauses(self):
        clauses = [AuditRequest(clause=f"clause {i}") for i in range(5)]
        batch = BatchAuditRequest(clauses=clauses)
        assert len(batch.clauses) == 5

    def test_empty_clauses_raises(self):
        with pytest.raises(PydanticValidationError):
            BatchAuditRequest(clauses=[])

    def test_over_100_clauses_raises(self):
        clauses = [AuditRequest(clause=f"clause {i}") for i in range(101)]
        with pytest.raises(PydanticValidationError):
            BatchAuditRequest(clauses=clauses)
