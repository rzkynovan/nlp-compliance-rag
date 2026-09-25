"""Test weighted RRF (Persamaan 3.1–3.2), evidence trail, verifikasi sitasi, dan coordinator."""

import asyncio
import time
from types import SimpleNamespace

import pytest

from retrieval.bm25_retriever import RetrievedNode
from retrieval.hybrid_retriever import HybridRetriever, _RRF_K
from retrieval.query_analyzer import QueryAnalyzer, is_garbled_text
from agents.base_agent import (
    AgentVerdict, BaseAgent, ViolatedArticle,
    SPARSE_BOOST_SEMANTIC, SPARSE_BOOST_SPECIFIC,
)


# ── Fakes ────────────────────────────────────────────────────────────────────
def _chunk(pasal, text=None, doc="PBI 23/6/PBI/2021"):
    text = text or f"{doc} | Pasal {pasal}\nisi pasal {pasal} " + "x" * 90
    return text, {"pasal_number": pasal, "pasal": f"Pasal {pasal}", "ayat": "Ayat 1",
                  "document": doc, "regulation_type": "BI", "bab": "BAB III"}


class _FakeNode:
    def __init__(self, text, md, score):
        self._text, self.metadata, self.score = text, md, score

    def get_content(self):
        return self._text


class _FakeDenseIndex:
    def __init__(self, chunks):
        self.chunks = chunks

    def as_retriever(self, similarity_top_k):
        chunks = self.chunks[:similarity_top_k]
        return SimpleNamespace(retrieve=lambda q: [
            _FakeNode(t, md, 0.9 - 0.1 * i) for i, (t, md) in enumerate(chunks)])


class _FakeBM25:
    def __init__(self, chunks):
        self.chunks = chunks

    def retrieve(self, query, top_k=10):
        return [RetrievedNode(t, md, 10.0 - i, i + 1) for i, (t, md) in enumerate(self.chunks[:top_k])]


class _Agent(BaseAgent):
    def initialize(self, api_key, chroma_path):
        pass

    def analyze(self, clause, context=None):
        pass

    def build_prompt(self, clause, articles):
        return ""


# ── Weighted RRF ─────────────────────────────────────────────────────────────
def test_weighted_rrf_always_fuses_and_alpha_shifts_ranking():
    dense = [_chunk("1"), _chunk("2"), _chunk("3")]
    sparse = [_chunk("3"), _chunk("2"), _chunk("1")]
    hr = HybridRetriever(_FakeDenseIndex(dense), _FakeBM25(sparse))

    lexical = hr.retrieve_weighted("q", alpha=0.7, top_k=3)
    semantic = hr.retrieve_weighted("q", alpha=0.3, top_k=3)
    assert lexical[0]["metadata"]["pasal_number"] == "3"    # BM25 dominan
    assert semantic[0]["metadata"]["pasal_number"] == "1"   # dense dominan
    assert all(r["source"] == "hybrid" for r in lexical)    # hadir di kedua daftar

    # Persamaan 3.2: alpha/(k+rank_bm25) + (1-alpha)/(k+rank_dense)
    top = lexical[0]
    expected = 0.7 / (_RRF_K + 1) + 0.3 / (_RRF_K + 3)
    assert top["score"] == pytest.approx(expected)
    assert 0 < top["relevance_score"] <= 1
    assert top["alpha"] == 0.7


def test_relevance_score_is_one_when_rank1_in_both_lists():
    same = [_chunk("9")]
    hr = HybridRetriever(_FakeDenseIndex(same), _FakeBM25(same))
    [r] = hr.retrieve_weighted("q", alpha=0.3, top_k=1)
    assert r["relevance_score"] == pytest.approx(1.0)


# ── Query-aware alpha (Persamaan 3.1) ────────────────────────────────────────
def test_select_sparse_boost():
    agent = _Agent("T", "Bank Indonesia (BI)", "bi_regulations")
    agent.query_analyzer = QueryAnalyzer()
    assert agent.select_sparse_boost("sesuai dengan Pasal 160 PBI 23/6/2021") == SPARSE_BOOST_SPECIFIC
    assert agent.select_sparse_boost("aturan tentang batas saldo maksimal") == SPARSE_BOOST_SEMANTIC


def test_agent_retrieval_uses_hybrid_for_semantic_clause_too():
    chunks = [_chunk("160"), _chunk("161")]
    agent = _Agent("T", "Bank Indonesia (BI)", "bi_regulations")
    agent.index = _FakeDenseIndex(chunks)
    agent.hybrid_retriever = HybridRetriever(agent.index, _FakeBM25(chunks))
    agent.query_analyzer = QueryAnalyzer()
    arts = agent.retrieve_relevant_articles("batas saldo akun unverified Rp10.000.000", top_k=2)
    assert len(arts) == 2
    assert all(a["retrieval_source"] == "hybrid" and a["alpha"] == SPARSE_BOOST_SEMANTIC for a in arts)


def test_agent_retrieval_dense_fallback_without_bm25():
    agent = _Agent("T", "Bank Indonesia (BI)", "bi_regulations")
    agent.index = _FakeDenseIndex([_chunk("160")])
    [a] = agent.retrieve_relevant_articles("batas saldo", top_k=1)
    assert a["retrieval_source"] == "dense" and 0 <= a["relevance_score"] <= 1


# ── Evidence trail & verifikasi sitasi ───────────────────────────────────────
def test_build_evidence_and_verify_citations():
    arts = [{"content": t, "metadata": md, "relevance_score": 0.8, "found_in": "hybrid"}
            for t, md in (_chunk("160"), _chunk("161"))]
    evidence = BaseAgent.build_evidence(arts)
    assert evidence[0]["rank"] == 1
    assert evidence[0]["article"] == "Pasal 160 Ayat 1"
    assert evidence[0]["regulation"] == "PBI 23/6/PBI/2021"

    violations = [
        ViolatedArticle(article="Pasal 160 Ayat 1", regulation="PBI", violation_detail="x"),
        ViolatedArticle(article="Pasal 999", regulation="PBI", violation_detail="x"),
        ViolatedArticle(article="Unknown", regulation="PBI", violation_detail="x"),
    ]
    BaseAgent.verify_citations(violations, evidence)
    assert [v.grounded for v in violations] == [True, False, None]


def test_normalize_status_six_classes():
    assert BaseAgent.normalize_status("non-compliant") == "NON_COMPLIANT"
    assert BaseAgent.normalize_status("UNCLEAR") == "UNCLEAR"
    assert BaseAgent.normalize_status("bogus") == "NEEDS_REVIEW"


def test_is_garbled_text():
    assert is_garbled_text("d a t a p r i b a d i n a s a b a h a k a n d i")
    assert not is_garbled_text("Data Pribadi Nasabah akan dienkripsi menggunakan standar AES-256 saat in-transit.")


# ── Coordinator: paralel sungguhan + pemilihan regulator ─────────────────────
class _SlowAgent:
    def __init__(self, name, status, delay):
        self.name, self.status, self.delay = name, status, delay
        self.calls = []

    def analyze(self, clause, context=None):
        self.calls.append(context)
        time.sleep(self.delay)
        return AgentVerdict(agent_id=self.name, regulator=self.name, verdict=self.status,
                            confidence_score=0.8, violated_articles=[], retrieved_context="",
                            reasoning_trace="")


def _coordinator(bi_status="NOT_ADDRESSED", ojk_status="NON_COMPLIANT", delay=0.4):
    from agents.coordinator import CoordinatorAgent
    from agents.conflict_resolver import ConflictResolverAgent
    c = CoordinatorAgent.__new__(CoordinatorAgent)
    c.name = "COORDINATOR"
    c.bi_agent = _SlowAgent("BI", bi_status, delay)
    c.ojk_agent = _SlowAgent("OJK", ojk_status, delay)
    c.resolver = ConflictResolverAgent()
    c.initialized = True
    c._save_results = lambda *a, **k: None
    return c


def test_coordinator_runs_agents_in_parallel():
    c = _coordinator(delay=0.4)
    t0 = time.perf_counter()
    result = asyncio.run(c.audit_clause_async("klausul uji", context={"top_k": 7}))
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.7, f"agen berjalan berurutan ({elapsed:.2f}s)"
    assert result.final_verdict.final_status == "NON_COMPLIANT"
    assert c.bi_agent.calls[0]["top_k"] == 7


@pytest.mark.parametrize("regulator,ran_bi,ran_ojk,final", [
    ("BI", True, False, "NOT_ADDRESSED"),
    ("OJK", False, True, "NON_COMPLIANT"),
    ("all", True, True, "NON_COMPLIANT"),
])
def test_coordinator_respects_regulator_choice(regulator, ran_bi, ran_ojk, final):
    c = _coordinator(delay=0)
    result = asyncio.run(c.audit_clause_async("klausul uji", context={"regulator": regulator}))
    assert bool(c.bi_agent.calls) is ran_bi
    assert bool(c.ojk_agent.calls) is ran_ojk
    assert result.final_verdict.final_status == final


# ── Switch ablation RETRIEVAL_STRATEGY ───────────────────────────────────────
@pytest.mark.parametrize("strategy,source,alpha", [
    ("query_aware", "hybrid", SPARSE_BOOST_SEMANTIC),
    ("rrf_equal", "hybrid", 0.5),
    ("dense", "dense", None),
    ("tidak-valid", "hybrid", SPARSE_BOOST_SEMANTIC),   # fallback ke default proposal
])
def test_retrieval_strategy_switch(monkeypatch, strategy, source, alpha):
    monkeypatch.setenv("RETRIEVAL_STRATEGY", strategy)
    chunks = [_chunk("160")]
    agent = _Agent("T", "Bank Indonesia (BI)", "bi_regulations")
    agent.index = _FakeDenseIndex(chunks)
    agent.hybrid_retriever = HybridRetriever(agent.index, _FakeBM25(chunks))
    agent.query_analyzer = QueryAnalyzer()
    [a] = agent.retrieve_relevant_articles("batas saldo akun", top_k=1)
    assert a["retrieval_source"] == source and a["alpha"] == alpha
