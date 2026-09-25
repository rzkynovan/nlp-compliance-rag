"""Test ConflictResolverAgent — Persamaan 2.26 & Subbab 3.5.5 proposal."""

import itertools

import pytest

from agents.conflict_resolver import ConflictResolverAgent

STATUSES = list(ConflictResolverAgent.STATUS_PRIORITY)


def _v(status, violations=(), missing=(), confidence=0.8, recs=()):
    return {
        "verdict": status,
        "confidence_score": confidence,
        "violated_articles": [{"article": a, "required_value": "x", "actual_value": "y"} for a in violations],
        "missing_elements": list(missing),
        "recommendations": list(recs),
        "risk_level": "LOW",
    }


@pytest.fixture
def resolver():
    return ConflictResolverAgent()


@pytest.mark.parametrize("status", STATUSES)
def test_phi_identity_when_agents_agree(resolver, status):
    # c_hat = v_BI jika v_BI == v_OJK
    assert resolver.phi(status, status) == status


@pytest.mark.parametrize("a,b", list(itertools.permutations(STATUSES, 2)))
def test_phi_picks_higher_priority_and_is_symmetric(resolver, a, b):
    expected = a if resolver.STATUS_PRIORITY[a] > resolver.STATUS_PRIORITY[b] else b
    assert resolver.phi(a, b) == expected == resolver.phi(b, a)


def test_non_compliant_dominates(resolver):
    out = resolver.resolve(_v("NON_COMPLIANT", ["Pasal 160 Ayat 1"]), _v("COMPLIANT"))
    assert out.final_status == "NON_COMPLIANT"


def test_both_partial_with_missing_elements_stays_partial(resolver):
    # Perilaku lama: PARTIALLY+PARTIALLY tanpa violations → COMPLIANT (melanggar Phi)
    out = resolver.resolve(
        _v("PARTIALLY_COMPLIANT", missing=["(B) tujuan"]),
        _v("PARTIALLY_COMPLIANT", missing=["(C) keamanan"]),
    )
    assert out.final_status == "PARTIALLY_COMPLIANT"


def test_unsupported_partial_downgraded_before_phi(resolver):
    out = resolver.resolve(_v("PARTIALLY_COMPLIANT"), _v("NOT_ADDRESSED"))
    assert out.final_status == "COMPLIANT"


def test_partial_with_missing_elements_beats_not_addressed(resolver):
    out = resolver.resolve(_v("NOT_ADDRESSED"), _v("PARTIALLY_COMPLIANT", missing=["(A) consent"]))
    assert out.final_status == "PARTIALLY_COMPLIANT"


def test_both_unclear_stays_unclear(resolver):
    out = resolver.resolve(_v("UNCLEAR"), _v("UNCLEAR"))
    assert out.final_status == "UNCLEAR"


def test_unknown_status_becomes_needs_review(resolver):
    out = resolver.resolve(_v("SOMETHING_ELSE"), _v("NOT_ADDRESSED"))
    assert out.final_status == "NEEDS_REVIEW"


def test_primary_regulator_orders_recommendations(resolver):
    out = resolver.resolve(
        _v("NON_COMPLIANT", recs=["perbaiki batas saldo"]),
        _v("NON_COMPLIANT", recs=["perbaiki SLA"]),
        clause_category="OJK_PRIORITY",
    )
    assert out.recommendations[0].startswith("[OJK]")
    assert out.evidence_matrix["resolution"]["primary_regulator"] == "OJK"


def test_resolve_single_regulator(resolver):
    out = resolver.resolve_single(_v("NON_COMPLIANT", ["Pasal 160 Ayat 1"], confidence=0.9), "BI")
    assert out.final_status == "NON_COMPLIANT"
    assert out.ojk_verdict is None
    assert out.overall_confidence == 0.9
    assert out.recommendations and out.recommendations[0].startswith("[BI]")
