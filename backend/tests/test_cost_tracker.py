"""
test_cost_tracker.py — unit tests for CostTracker.

Tests: calculate_cost pricing accuracy, estimate_cost,
check_budget, record_usage, get_today_stats, and budget warning.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.core.cost_tracker import CostTracker
from app.config import MODEL_COSTS


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def tracker(tmp_path, mock_settings):
    """CostTracker using a temp directory; budget = $5.00."""
    mock_settings.DAILY_BUDGET_LIMIT_USD = 5.0
    mock_settings.COST_OPTIMIZATION_MODE = "development"

    with patch("app.core.cost_tracker.settings", mock_settings):
        ct = CostTracker(log_dir=str(tmp_path / "costs"))
    return ct


# ── calculate_cost ─────────────────────────────────────────────────────────���──

class TestCalculateCost:
    def test_gpt4o_mini_input_only(self, tracker):
        # gpt-4o-mini: $0.15 / 1M input tokens
        cost = tracker.calculate_cost("gpt-4o-mini", input_tokens=1_000_000, output_tokens=0)
        assert abs(cost - 0.15) < 1e-6

    def test_gpt4o_mini_output_only(self, tracker):
        # gpt-4o-mini: $0.60 / 1M output tokens
        cost = tracker.calculate_cost("gpt-4o-mini", input_tokens=0, output_tokens=1_000_000)
        assert abs(cost - 0.60) < 1e-6

    def test_gpt4o_combined(self, tracker):
        # gpt-4o: $2.50 / 1M input + $10.00 / 1M output
        cost = tracker.calculate_cost("gpt-4o", input_tokens=500_000, output_tokens=100_000)
        expected = (500_000 / 1_000_000 * 2.50) + (100_000 / 1_000_000 * 10.00)
        assert abs(cost - expected) < 1e-6

    def test_embedding_model_no_output_cost(self, tracker):
        # text-embedding-3-small has output cost = 0
        cost = tracker.calculate_cost("text-embedding-3-small", input_tokens=100_000, output_tokens=999)
        expected = 100_000 / 1_000_000 * 0.02
        assert abs(cost - expected) < 1e-6

    def test_unknown_model_returns_zero(self, tracker):
        cost = tracker.calculate_cost("unknown-model-xyz", input_tokens=1000, output_tokens=500)
        assert cost == 0.0

    def test_zero_tokens_returns_zero(self, tracker):
        cost = tracker.calculate_cost("gpt-4o-mini", input_tokens=0, output_tokens=0)
        assert cost == 0.0

    def test_result_rounded_to_6_decimals(self, tracker):
        cost = tracker.calculate_cost("gpt-4o-mini", input_tokens=1, output_tokens=1)
        assert isinstance(cost, float)
        assert len(str(cost).rstrip("0").split(".")[-1]) <= 6


# ── estimate_cost ─────────────────────────────────────────────────────────────

class TestEstimateCost:
    def test_estimate_matches_calculate(self, tracker):
        estimated = tracker.estimate_cost("gpt-4o-mini", 1000, 500)
        calculated = tracker.calculate_cost("gpt-4o-mini", 1000, 500)
        assert estimated == calculated

    def test_default_output_tokens(self, tracker):
        # Default output = 500
        estimated = tracker.estimate_cost("gpt-4o-mini", 1000)
        manual = tracker.calculate_cost("gpt-4o-mini", 1000, 500)
        assert estimated == manual


# ── check_budget ──────────────────────────────────────────────────────────────

class TestCheckBudget:
    def test_within_budget(self, tracker):
        # No usage yet → remaining = $5.00
        assert tracker.check_budget(estimated_cost=1.0) is True

    def test_zero_cost_always_within(self, tracker):
        assert tracker.check_budget(estimated_cost=0.0) is True

    def test_exactly_at_limit(self, tracker):
        # $5.00 budget, $5.00 cost → remaining = $0.00, not enough for any extra
        assert tracker.check_budget(estimated_cost=5.0) is True

    def test_exceeds_budget(self, tracker):
        assert tracker.check_budget(estimated_cost=6.0) is False

    def test_after_usage_reduces_remaining(self, tracker):
        with patch("app.core.cost_tracker.settings", tracker.__class__.__init__.__self__  # type: ignore
                   if hasattr(tracker, "__self__") else MagicMock()):
            pass
        tracker.record_usage(
            model="gpt-4o-mini",
            input_tokens=10_000_000,   # $1.50
            output_tokens=0,
            endpoint="test",
        )
        # Remaining ~$3.50, so $4.00 should fail
        assert tracker.check_budget(estimated_cost=4.0) is False


# ── record_usage ──────────────────────────────────────────────────────────────

class TestRecordUsage:
    def test_record_creates_file(self, tracker, tmp_path):
        tracker.record_usage(
            model="gpt-4o-mini",
            input_tokens=1000,
            output_tokens=200,
            endpoint="audit/analyze",
            clause_id="SOP-001",
        )
        cost_files = list(tracker.log_dir.glob("usage_*.json"))
        assert len(cost_files) == 1

    def test_record_accumulates_tokens(self, tracker):
        tracker.record_usage("gpt-4o-mini", 1000, 200, "test")
        tracker.record_usage("gpt-4o-mini", 500, 100, "test")
        stats = tracker.get_today_stats()
        assert stats["total_tokens"] == 1800
        assert stats["api_calls"] == 2

    def test_record_returns_usage_record(self, tracker):
        record = tracker.record_usage("gpt-4o-mini", 1000, 200, "audit/analyze", "SOP-001")
        assert record.model == "gpt-4o-mini"
        assert record.input_tokens == 1000
        assert record.output_tokens == 200
        assert record.clause_id == "SOP-001"
        assert record.cost_usd > 0

    def test_cost_correctly_calculated(self, tracker):
        # 1M input tokens for gpt-4o-mini = $0.15
        record = tracker.record_usage("gpt-4o-mini", 1_000_000, 0, "test")
        assert abs(record.cost_usd - 0.15) < 1e-6


# ── get_today_stats ─────────────────────────────────────────────────────────

class TestGetTodayStats:
    def test_empty_stats(self, tracker):
        stats = tracker.get_today_stats()
        assert stats["total_tokens"] == 0
        assert stats["total_cost_usd"] == 0.0
        assert stats["api_calls"] == 0
        assert stats["budget_limit_usd"] == 5.0
        assert stats["remaining_usd"] == 5.0
        assert stats["budget_percentage"] == 0.0

    def test_stats_after_usage(self, tracker):
        tracker.record_usage("gpt-4o-mini", 1000, 200, "test")
        stats = tracker.get_today_stats()
        assert stats["api_calls"] == 1
        assert stats["total_tokens"] == 1200
        assert stats["total_cost_usd"] > 0
        assert stats["remaining_usd"] < 5.0

    def test_remaining_never_negative(self, tracker):
        # Simulate spending over budget by directly patching
        today_file = tracker._get_today_file()
        today_file.parent.mkdir(parents=True, exist_ok=True)
        import json
        from datetime import datetime
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        with open(today_file, "w") as f:
            json.dump({
                "date": today_str,
                "total_tokens": 100,
                "total_cost_usd": 10.0,  # Over $5.00 limit
                "api_calls": 1,
                "records": []
            }, f)

        stats = tracker.get_today_stats()
        assert stats["remaining_usd"] == 0.0  # max(0, negative) = 0

    def test_keys_present(self, tracker):
        stats = tracker.get_today_stats()
        expected_keys = {
            "date", "total_tokens", "total_cost_usd",
            "api_calls", "budget_limit_usd", "remaining_usd", "budget_percentage"
        }
        assert expected_keys.issubset(stats.keys())


# ── MODEL_COSTS completeness ──────────────────────────────────────────────────

class TestModelCosts:
    def test_required_models_present(self):
        required = ["gpt-4o", "gpt-4o-mini", "text-embedding-3-small", "text-embedding-3-large"]
        for model in required:
            assert model in MODEL_COSTS, f"MODEL_COSTS missing: {model}"

    def test_each_model_has_input_output_keys(self):
        for model, costs in MODEL_COSTS.items():
            assert "input" in costs, f"{model} missing 'input'"
            assert "output" in costs, f"{model} missing 'output'"
            assert isinstance(costs["input"], (int, float))
            assert isinstance(costs["output"], (int, float))

    def test_embedding_output_cost_is_zero(self):
        assert MODEL_COSTS["text-embedding-3-small"]["output"] == 0.0
        assert MODEL_COSTS["text-embedding-3-large"]["output"] == 0.0
