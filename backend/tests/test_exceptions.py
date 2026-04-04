"""
test_exceptions.py — unit tests for custom exception hierarchy.

Validates: code, detail, status_code, inheritance, and kwargs storage
for every exception class in app.core.exceptions.
"""

import pytest
from fastapi import status as http_status

from app.core.exceptions import (
    ComplianceAuditError,
    ValidationError,
    NotFoundError,
    LLMError,
    VectorDBError,
    IngestionError,
    AuditError,
    ExperimentError,
    RateLimitError,
    AuthenticationError,
    AuthorizationError,
)


# ── ComplianceAuditError (base) ────────────────────────���──────────────────────

class TestComplianceAuditError:
    def test_basic_fields(self):
        exc = ComplianceAuditError(code="TEST_CODE", detail="test detail")
        assert exc.code == "TEST_CODE"
        assert exc.detail == "test detail"
        assert exc.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_custom_status_code(self):
        exc = ComplianceAuditError(code="X", detail="y", status_code=503)
        assert exc.status_code == 503

    def test_is_exception(self):
        exc = ComplianceAuditError(code="X", detail="y")
        assert isinstance(exc, Exception)

    def test_str_is_detail(self):
        exc = ComplianceAuditError(code="X", detail="my detail")
        assert str(exc) == "my detail"

    def test_extra_kwargs_stored(self):
        exc = ComplianceAuditError(code="X", detail="y", clause_id="clause-1")
        assert exc.kwargs.get("clause_id") == "clause-1"


# ── ValidationError ─────────────────────────────���─────────────────────────────

class TestValidationError:
    def test_code_and_status(self):
        exc = ValidationError(detail="field required")
        assert exc.code == "VALIDATION_ERROR"
        assert exc.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_optional_field_kwarg(self):
        exc = ValidationError(detail="bad value", field="clause")
        assert exc.kwargs.get("field") == "clause"

    def test_inherits_base(self):
        exc = ValidationError(detail="x")
        assert isinstance(exc, ComplianceAuditError)


# ── NotFoundError ─────────────────────────────��───────────────────────────────

class TestNotFoundError:
    def test_message_format(self):
        exc = NotFoundError(resource="Regulation", identifier="REG-001")
        assert "Regulation" in exc.detail
        assert "REG-001" in exc.detail

    def test_status_404(self):
        exc = NotFoundError(resource="Audit", identifier="123")
        assert exc.status_code == http_status.HTTP_404_NOT_FOUND

    def test_code(self):
        exc = NotFoundError(resource="X", identifier="y")
        assert exc.code == "NOT_FOUND"


# ── LLMError ───────────────────────────────────────────────────────���─────────

class TestLLMError:
    def test_default_provider(self):
        exc = LLMError(detail="timeout")
        assert "openai" in exc.detail
        assert "timeout" in exc.detail
        assert exc.code == "LLM_ERROR"
        assert exc.status_code == http_status.HTTP_503_SERVICE_UNAVAILABLE

    def test_custom_provider(self):
        exc = LLMError(detail="connection refused", provider="anthropic")
        assert "anthropic" in exc.detail


# ── VectorDBError ─────────────────────────────────────────────────────────────

class TestVectorDBError:
    def test_basic(self):
        exc = VectorDBError(detail="collection not found")
        assert exc.code == "VECTOR_DB_ERROR"
        assert exc.status_code == http_status.HTTP_503_SERVICE_UNAVAILABLE
        assert "collection not found" in exc.detail

    def test_collection_kwarg(self):
        exc = VectorDBError(detail="empty", collection="bi_regulations")
        assert exc.kwargs.get("collection") == "bi_regulations"


# ── IngestionError ───────────────────────────��───────────────────────────────���

class TestIngestionError:
    def test_detail_format(self):
        exc = IngestionError(detail="parse failed", document="regulation.pdf")
        assert "parse failed" in exc.detail
        assert exc.code == "INGESTION_ERROR"
        assert exc.status_code == http_status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_document_kwarg(self):
        exc = IngestionError(detail="x", document="file.pdf")
        assert exc.kwargs.get("document") == "file.pdf"


# ── AuditError ────────────────────────────────────────��───────────────────────

class TestAuditError:
    def test_code_and_status(self):
        exc = AuditError(detail="coordinator timeout")
        assert exc.code == "AUDIT_ERROR"
        assert exc.status_code == http_status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_clause_id_kwarg(self):
        exc = AuditError(detail="failed", clause_id="SOP-001")
        assert exc.kwargs.get("clause_id") == "SOP-001"


# ── ExperimentError ───────────────────────────��──────────────────────────────���

class TestExperimentError:
    def test_code_and_status(self):
        exc = ExperimentError(detail="mlflow unreachable")
        assert exc.code == "EXPERIMENT_ERROR"
        assert exc.status_code == http_status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_run_id_kwarg(self):
        exc = ExperimentError(detail="x", run_id="run-abc")
        assert exc.kwargs.get("run_id") == "run-abc"


# ── RateLimitError ──────────────────────────────────���─────────────────────────

class TestRateLimitError:
    def test_defaults(self):
        exc = RateLimitError()
        assert exc.code == "RATE_LIMIT_EXCEEDED"
        assert exc.status_code == http_status.HTTP_429_TOO_MANY_REQUESTS
        assert "60" in exc.detail

    def test_custom_retry_after(self):
        exc = RateLimitError(retry_after=120)
        assert "120" in exc.detail


# ── AuthenticationError ─────────────────────────────��─────────────────────────

class TestAuthenticationError:
    def test_defaults(self):
        exc = AuthenticationError()
        assert exc.code == "AUTHENTICATION_ERROR"
        assert exc.status_code == http_status.HTTP_401_UNAUTHORIZED

    def test_custom_detail(self):
        exc = AuthenticationError(detail="Token expired")
        assert exc.detail == "Token expired"


# ── AuthorizationError ─────────────────────────────────��──────────────────────

class TestAuthorizationError:
    def test_defaults(self):
        exc = AuthorizationError()
        assert exc.code == "AUTHORIZATION_ERROR"
        assert exc.status_code == http_status.HTTP_403_FORBIDDEN

    def test_custom_detail(self):
        exc = AuthorizationError(detail="Admin only")
        assert exc.detail == "Admin only"


# ── raise / catch behaviour ──────────────────────────────────��────────────────

class TestRaiseCatch:
    def test_catch_as_base(self):
        with pytest.raises(ComplianceAuditError) as exc_info:
            raise NotFoundError(resource="Clause", identifier="C-99")
        assert exc_info.value.status_code == 404

    def test_catch_as_exception(self):
        with pytest.raises(Exception):
            raise RateLimitError()

    def test_all_subclasses_are_compliance_error(self):
        subclasses = [
            ValidationError("x"),
            NotFoundError("R", "id"),
            LLMError("x"),
            VectorDBError("x"),
            IngestionError("x"),
            AuditError("x"),
            ExperimentError("x"),
            RateLimitError(),
            AuthenticationError(),
            AuthorizationError(),
        ]
        for exc in subclasses:
            assert isinstance(exc, ComplianceAuditError), f"{type(exc)} should be ComplianceAuditError"
