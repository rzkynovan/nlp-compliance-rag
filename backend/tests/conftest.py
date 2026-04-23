"""
conftest.py — shared fixtures and test configuration.

Patches `app.config.settings` before any module that imports it is loaded,
so tests never need a real .env file or external services.
"""

import sys
import types
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Make sure backend/ is importable ─────────────────────────────────────────
BACKEND_DIR = Path(__file__).parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ── Stub heavy optional deps so imports don't crash in CI ────────────────────
def _stub_module(name: str):
    """Register a MagicMock under `name` so `import name` returns it."""
    if name not in sys.modules:
        mod = types.ModuleType(name)
        sys.modules[name] = mod
    return sys.modules[name]


for _heavy in [
    "chromadb", "chromadb.config",
    "llama_index", "llama_index.core",
    "llama_index.embeddings", "llama_index.embeddings.openai",
    "llama_index.llms", "llama_index.llms.openai",
    "llama_index.vector_stores", "llama_index.vector_stores.chroma",
    "celery",
]:
    _stub_module(_heavy)

# Modules that need attribute access must be MagicMock, not plain ModuleType.
for _mock_mod in ["structlog", "mlflow", "mlflow.tracking", "mlflow.exceptions", "mlflow.models"]:
    if _mock_mod not in sys.modules:
        sys.modules[_mock_mod] = MagicMock()


# ── Minimal Settings mock ─────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    """
    Patch `app.config.settings` globally so every module gets a predictable,
    dependency-free config object during tests.
    """
    settings_mock = MagicMock()
    settings_mock.OPENAI_API_KEY = "sk-test-key"
    settings_mock.LLAMA_CLOUD_API_KEY = None
    settings_mock.LLM_MODEL = "gpt-4o-mini"
    settings_mock.EMBEDDING_MODEL = "text-embedding-3-small"
    settings_mock.CHROMADB_PERSIST_DIR = "/tmp/test_chroma"
    settings_mock.CHROMADB_COLLECTION_BI = "bi_regulations"
    settings_mock.CHROMADB_COLLECTION_OJK = "ojk_regulations"
    settings_mock.DAILY_BUDGET_LIMIT_USD = 5.0
    settings_mock.ENABLE_CACHE = True
    settings_mock.CACHE_TTL_HOURS = 24
    settings_mock.COST_OPTIMIZATION_MODE = "development"
    settings_mock.ALLOWED_ORIGINS = ["http://localhost:3000"]
    settings_mock.API_V1_PREFIX = "/api/v1"
    settings_mock.PROJECT_NAME = "Compliance Audit RAG"
    settings_mock.VERSION = "1.0.0"
    settings_mock.RATE_LIMIT_REQUESTS_PER_MINUTE = 10
    settings_mock.MLFLOW_TRACKING_URI = "http://localhost:5000"

    import app.config as cfg_module
    monkeypatch.setattr(cfg_module, "settings", settings_mock)

    # Also patch the singleton inside cost_tracker if already imported
    try:
        import app.core.cost_tracker as ct_module
        monkeypatch.setattr(ct_module, "settings", settings_mock)
    except ImportError:
        pass

    return settings_mock


@pytest.fixture
def sample_clause() -> str:
    return "Saldo maksimal untuk akun unverified adalah Rp 10.000.000"


@pytest.fixture
def sample_audit_result() -> dict:
    return {
        "final_status": "NON_COMPLIANT",
        "overall_confidence": 0.92,
        "risk_score": "HIGH",
        "bi_verdict": {
            "verdict": "NON_COMPLIANT",
            "confidence_score": 0.95,
            "violations": [{"article": "Pasal 160", "description": "Melebihi batas saldo"}],
            "evidence": [],
            "reasoning_trace": "Saldo melebihi batas BI",
        },
        "ojk_verdict": {
            "verdict": "COMPLIANT",
            "confidence_score": 0.80,
            "violations": [],
            "evidence": [],
            "reasoning_trace": "Tidak ada pelanggaran OJK",
        },
        "violations": ["Pasal 160: Melebihi batas saldo"],
        "recommendations": ["Kurangi batas saldo ke Rp 2.000.000"],
        "analysis_mode": "multi_agent_rag",
    }
