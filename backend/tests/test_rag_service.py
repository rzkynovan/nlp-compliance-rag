"""
test_rag_service.py — unit tests for RAGAuditService.

External dependencies (OpenAI, ChromaDB, CoordinatorAgent) are fully mocked.
Tests focus on: LLM response parsing, prompt building, fallback logic,
caching integration, and budget enforcement.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from pathlib import Path

from app.core.exceptions import ComplianceAuditError


# ── Helpers ─────────────────────────────────────────────────────────────────

def _make_service(mock_settings, tmp_path, chroma_available: bool = True):
    """
    Instantiate RAGAuditService with all external dependencies mocked.
    Returns (service, mock_openai_client).
    """
    mock_openai = MagicMock()
    mock_settings.CHROMADB_PERSIST_DIR = str(tmp_path / "chroma")
    mock_settings.ENABLE_CACHE = False   # disable cache unless explicitly needed

    with patch("app.services.rag_service.OpenAI", return_value=mock_openai), \
         patch("app.services.rag_service.settings", mock_settings), \
         patch("app.services.rag_service.AuditCache") as mock_cache_cls, \
         patch("app.services.rag_service.cost_tracker") as mock_cost:

        mock_cache_cls.return_value = MagicMock()
        mock_cost.estimate_cost.return_value = 0.001
        mock_cost.get_today_stats.return_value = {"remaining_usd": 4.99}

        from app.services.rag_service import RAGAuditService
        service = RAGAuditService()
        service._chroma_available = chroma_available
        service.openai_client = mock_openai

    return service, mock_openai


# ── _parse_llm_response ───────────────────────────────────────────────────────

class TestParseLlmResponse:
    def setup_method(self):
        import importlib
        import app.services.rag_service as mod
        importlib.reload(mod)

    @pytest.fixture
    def service(self, mock_settings, tmp_path):
        svc, _ = _make_service(mock_settings, tmp_path)
        return svc

    def test_valid_json_response(self, service):
        raw = """{
            "status": "NON_COMPLIANT",
            "confidence": 0.9,
            "violations": ["Pasal 160"],
            "recommendations": ["Kurangi batas"],
            "relevant_regulations": ["PBI 23/6/2021"],
            "reasoning": "Saldo melebihi batas BI"
        }"""
        result = service._parse_llm_response(raw, "BI")
        assert result["status"] == "NON_COMPLIANT"
        assert result["confidence"] == 0.9
        assert "Pasal 160" in result["violations"]
        assert "Kurangi batas" in result["recommendations"]

    def test_json_embedded_in_text(self, service):
        raw = """Berikut analisis saya:
        {"status": "COMPLIANT", "confidence": 0.8, "violations": [], "recommendations": [], "reasoning": "ok"}
        Demikian."""
        result = service._parse_llm_response(raw, "BI")
        assert result["status"] == "COMPLIANT"
        assert result["confidence"] == 0.8

    def test_fallback_non_compliant_keywords(self, service):
        raw = "Klausa ini melanggar regulasi BI dan tidak memenuhi standar."
        result = service._parse_llm_response(raw, "BI")
        assert result["status"] == "NON_COMPLIANT"
        assert result["confidence"] >= 0.5

    def test_fallback_compliant_keywords(self, service):
        raw = "Klausa ini sesuai dengan regulasi yang berlaku dan memenuhi standar."
        result = service._parse_llm_response(raw, "BI")
        assert result["status"] == "COMPLIANT"

    def test_fallback_partial_keywords(self, service):
        raw = "Sebagian klausa perlu perbaikan untuk memenuhi regulasi."
        result = service._parse_llm_response(raw, "BI")
        assert result["status"] == "PARTIALLY_COMPLIANT"

    def test_fallback_unclear_when_no_keywords(self, service):
        raw = "Tidak ada informasi yang relevan dengan regulasi ini."
        result = service._parse_llm_response(raw, "BI")
        assert result["status"] == "UNCLEAR"
        assert result["confidence"] == 0.5

    def test_result_has_all_keys(self, service):
        raw = '{"status": "COMPLIANT", "confidence": 0.7, "violations": [], "recommendations": [], "reasoning": "ok"}'
        result = service._parse_llm_response(raw, "BI")
        assert "status" in result
        assert "confidence" in result
        assert "violations" in result
        assert "recommendations" in result

    def test_malformed_json_falls_back_gracefully(self, service):
        raw = "{ invalid json {{ no quotes }}"
        result = service._parse_llm_response(raw, "BI")
        assert "status" in result
        assert isinstance(result["confidence"], float)


# ── _build_llm_prompt ────────────────────────────────────────────────────────

class TestBuildLlmPrompt:
    @pytest.fixture
    def service(self, mock_settings, tmp_path):
        svc, _ = _make_service(mock_settings, tmp_path)
        return svc

    def test_clause_in_prompt(self, service):
        clause = "Saldo maksimal Rp 10.000.000"
        prompt = service._build_llm_prompt(clause, "BI")
        assert clause in prompt

    def test_bi_regulator_context(self, service):
        prompt = service._build_llm_prompt("test", "BI")
        assert "Bank Indonesia" in prompt

    def test_ojk_regulator_context(self, service):
        prompt = service._build_llm_prompt("test", "OJK")
        assert "OJK" in prompt or "Otoritas Jasa Keuangan" in prompt

    def test_all_regulator_context(self, service):
        prompt = service._build_llm_prompt("test", "all")
        assert "Bank Indonesia" in prompt

    def test_prompt_instructs_json_output(self, service):
        prompt = service._build_llm_prompt("test", "BI")
        assert "JSON" in prompt

    def test_prompt_includes_status_options(self, service):
        prompt = service._build_llm_prompt("test", "BI")
        for status in ["COMPLIANT", "NON_COMPLIANT", "PARTIALLY_COMPLIANT", "UNCLEAR"]:
            assert status in prompt


# ── _calculate_risk_score ─────────────────────────────────────────────────────

class TestCalculateRiskScore:
    @pytest.fixture
    def service(self, mock_settings, tmp_path):
        svc, _ = _make_service(mock_settings, tmp_path)
        return svc

    def _make_result(self, status: str, num_conflicts: int = 0):
        result = MagicMock()
        result.final_verdict = MagicMock()
        result.final_verdict.final_status = status
        result.final_verdict.regulatory_conflicts = [MagicMock()] * num_conflicts
        return result

    def test_non_compliant_is_high(self, service):
        assert service._calculate_risk_score(self._make_result("NON_COMPLIANT")) == "HIGH"

    def test_two_conflicts_is_high(self, service):
        assert service._calculate_risk_score(self._make_result("COMPLIANT", 2)) == "HIGH"

    def test_partial_with_one_conflict_is_medium(self, service):
        assert service._calculate_risk_score(self._make_result("PARTIALLY_COMPLIANT", 1)) == "MEDIUM"

    def test_unclear_is_medium(self, service):
        assert service._calculate_risk_score(self._make_result("UNCLEAR")) == "MEDIUM"

    def test_compliant_no_conflicts_is_low(self, service):
        assert service._calculate_risk_score(self._make_result("COMPLIANT", 0)) == "LOW"

    def test_no_final_verdict_defaults_low(self, service):
        result = MagicMock()
        result.final_verdict = None
        assert service._calculate_risk_score(result) == "LOW"


# ── _extract_violations ───────────────────────────────────────────────────────

class TestExtractViolations:
    @pytest.fixture
    def service(self, mock_settings, tmp_path):
        svc, _ = _make_service(mock_settings, tmp_path)
        return svc

    def test_no_violations(self, service):
        result = MagicMock()
        result.final_verdict.regulatory_conflicts = []
        assert service._extract_violations(result) == []

    def test_violations_formatted(self, service):
        conflict = MagicMock()
        conflict.type = "DIRECT_CONFLICT"
        conflict.description = "Saldo melebihi batas"
        result = MagicMock()
        result.final_verdict.regulatory_conflicts = [conflict]
        violations = service._extract_violations(result)
        assert len(violations) == 1
        assert "DIRECT_CONFLICT" in violations[0]
        assert "Saldo melebihi batas" in violations[0]


# ── analyze_with_rag (integration-style, full mocks) ─────────────────────────

class TestAnalyzeWithRag:
    @pytest.fixture
    def service_with_llm_only(self, mock_settings, tmp_path):
        """Service with ChromaDB unavailable → forces LLM-only path."""
        svc, mock_openai = _make_service(mock_settings, tmp_path, chroma_available=False)

        # Mock OpenAI chat completion
        mock_choice = MagicMock()
        mock_choice.message.content = '{"status": "COMPLIANT", "confidence": 0.85, "violations": [], "recommendations": [], "reasoning": "ok"}'
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_openai.chat.completions.create.return_value = mock_response

        # Patch cost_tracker on the service
        svc_cost = MagicMock()
        svc_cost.estimate_cost.return_value = 0.001
        svc_cost.get_today_stats.return_value = {"remaining_usd": 4.99}
        svc_cost.record_usage.return_value = MagicMock()

        with patch("app.services.rag_service.cost_tracker", svc_cost):
            svc._cost_tracker = svc_cost

        return svc, mock_openai

    @pytest.mark.asyncio
    async def test_llm_only_returns_dict(self, service_with_llm_only):
        svc, _ = service_with_llm_only
        with patch("app.services.rag_service.cost_tracker") as mock_ct:
            mock_ct.estimate_cost.return_value = 0.001
            mock_ct.get_today_stats.return_value = {"remaining_usd": 4.99}
            mock_ct.record_usage.return_value = MagicMock()

            result = await svc._analyze_llm_only(
                clause="Saldo maksimal Rp 10.000.000",
                regulator="BI",
                request_id="test-001",
            )

        assert isinstance(result, dict)
        assert "final_status" in result
        assert "overall_confidence" in result
        assert result["analysis_mode"] == "llm_only"

    @pytest.mark.asyncio
    async def test_llm_only_bi_verdict_for_bi_regulator(self, service_with_llm_only):
        svc, _ = service_with_llm_only
        with patch("app.services.rag_service.cost_tracker") as mock_ct:
            mock_ct.estimate_cost.return_value = 0.001
            mock_ct.get_today_stats.return_value = {"remaining_usd": 4.99}
            mock_ct.record_usage.return_value = MagicMock()

            result = await svc._analyze_llm_only(
                clause="test", regulator="BI", request_id="x"
            )
        assert result["bi_verdict"] is not None
        assert result["ojk_verdict"] is None

    @pytest.mark.asyncio
    async def test_llm_only_ojk_verdict_for_ojk_regulator(self, service_with_llm_only):
        svc, _ = service_with_llm_only
        with patch("app.services.rag_service.cost_tracker") as mock_ct:
            mock_ct.estimate_cost.return_value = 0.001
            mock_ct.get_today_stats.return_value = {"remaining_usd": 4.99}
            mock_ct.record_usage.return_value = MagicMock()

            result = await svc._analyze_llm_only(
                clause="test", regulator="OJK", request_id="x"
            )
        assert result["bi_verdict"] is None
        assert result["ojk_verdict"] is not None

    @pytest.mark.asyncio
    async def test_budget_exceeded_raises(self, mock_settings, tmp_path):
        svc, _ = _make_service(mock_settings, tmp_path, chroma_available=False)
        with patch("app.services.rag_service.cost_tracker") as mock_ct:
            mock_ct.estimate_cost.return_value = 10.0      # exceeds $5 budget
            mock_ct.get_today_stats.return_value = {"remaining_usd": 0.001}

            with pytest.raises(ComplianceAuditError) as exc_info:
                await svc.analyze_with_rag(
                    clause="test clause",
                    regulator="all",
                    use_cache=False,
                )
            assert exc_info.value.code == "BUDGET_EXCEEDED"
            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(self, mock_settings, tmp_path):
        mock_settings.ENABLE_CACHE = True
        svc, _ = _make_service(mock_settings, tmp_path, chroma_available=False)
        mock_settings.ENABLE_CACHE = True

        cached_result = {
            "final_status": "COMPLIANT",
            "from_cache": True,
            "overall_confidence": 0.9,
        }
        svc.cache = MagicMock()
        svc.cache.get.return_value = cached_result

        with patch("app.services.rag_service.settings", mock_settings):
            result = await svc.analyze_with_rag(
                clause="cached clause",
                regulator="BI",
                use_cache=True,
            )

        assert result["from_cache"] is True
        assert result["final_status"] == "COMPLIANT"
