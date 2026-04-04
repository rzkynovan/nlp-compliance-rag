from typing import Dict, Any, Optional
from fastapi import HTTPException, status


class ComplianceAuditError(Exception):
    def __init__(
        self,
        code: str,
        detail: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        **kwargs: Any
    ):
        self.code = code
        self.detail = detail
        self.status_code = status_code
        self.kwargs = kwargs
        super().__init__(detail)


class ValidationError(ComplianceAuditError):
    def __init__(self, detail: str, field: Optional[str] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            detail=detail,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            field=field
        )


class NotFoundError(ComplianceAuditError):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="NOT_FOUND",
            detail=f"{resource} with id '{identifier}' not found",
            status_code=status.HTTP_404_NOT_FOUND
        )


class LLMError(ComplianceAuditError):
    def __init__(self, detail: str, provider: str = "openai"):
        super().__init__(
            code="LLM_ERROR",
            detail=f"LLM provider '{provider}' error: {detail}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )


class VectorDBError(ComplianceAuditError):
    def __init__(self, detail: str, collection: Optional[str] = None):
        super().__init__(
            code="VECTOR_DB_ERROR",
            detail=f"Vector database error: {detail}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            collection=collection
        )


class IngestionError(ComplianceAuditError):
    def __init__(self, detail: str, document: Optional[str] = None):
        super().__init__(
            code="INGESTION_ERROR",
            detail=f"Document ingestion failed: {detail}",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            document=document
        )


class AuditError(ComplianceAuditError):
    def __init__(self, detail: str, clause_id: Optional[str] = None):
        super().__init__(
            code="AUDIT_ERROR",
            detail=f"Audit process failed: {detail}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            clause_id=clause_id
        )


class ExperimentError(ComplianceAuditError):
    def __init__(self, detail: str, run_id: Optional[str] = None):
        super().__init__(
            code="EXPERIMENT_ERROR",
            detail=f"Experiment tracking error: {detail}",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            run_id=run_id
        )


class RateLimitError(ComplianceAuditError):
    def __init__(self, retry_after: int = 60):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            detail=f"Rate limit exceeded. Retry after {retry_after} seconds.",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            retry_after=retry_after
        )


class AuthenticationError(ComplianceAuditError):
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            code="AUTHENTICATION_ERROR",
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED
        )


class AuthorizationError(ComplianceAuditError):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            code="AUTHORIZATION_ERROR",
            detail=detail,
            status_code=status.HTTP_403_FORBIDDEN
        )