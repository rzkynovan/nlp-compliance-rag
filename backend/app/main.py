from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.config import settings
from app.api.v1 import audit, regulations, health, experiments, usage
from app.core.exceptions import ComplianceAuditError
import structlog
import time
import logging

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    log.info(f"MLflow Tracking URI: {settings.MLFLOW_TRACKING_URI}")
    log.info(f"LLM Model: {settings.LLM_MODEL}")
    log.info(f"Embedding Model: {settings.EMBEDDING_MODEL}")
    log.info(f"Cost Optimization Mode: {settings.COST_OPTIMIZATION_MODE}")
    log.info(f"Daily Budget Limit: ${settings.DAILY_BUDGET_LIMIT_USD}")
    log.info(f"Cache Enabled: {settings.ENABLE_CACHE}")
    log.info(f"Allowed Origins: {settings.ALLOWED_ORIGINS}")
    yield
    log.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    MLOps-ready RAG system for regulatory compliance auditing.

    ## Features

    * **Multi-Agent RAG**: Parallel BI and OJK specialist agents
    * **Conflict Resolution**: Hierarchical conflict resolution between regulators
    * **Evidence Trail**: Full citation of regulation articles
    * **Experiment Tracking**: MLflow integration for model tracking

    ## Endpoints

    * `/api/v1/audit/*` - SOP compliance audit
    * `/api/v1/regulations/*` - Regulation knowledge base
    * `/api/v1/experiments/*` - MLflow experiment tracking
    * `/api/v1/health/*` - System health checks
    """,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)

# CORS: never use allow_origins=["*"] with allow_credentials=True — browser blocks it.
# Use explicit origin list from ALLOWED_ORIGINS env var.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.exception_handler(ComplianceAuditError)
async def compliance_audit_exception_handler(request: Request, exc: ComplianceAuditError):
    log.error("Compliance audit error", error_code=exc.code, detail=exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.detail,
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    log.warning("Validation error", errors=exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters",
                "details": exc.errors()
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    log.exception("Unhandled exception", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred"
            }
        }
    )


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.include_router(health.router, prefix=settings.API_V1_PREFIX, tags=["health"])
app.include_router(audit.router, prefix=settings.API_V1_PREFIX, tags=["audit"])
app.include_router(regulations.router, prefix=settings.API_V1_PREFIX, tags=["regulations"])
app.include_router(experiments.router, prefix=settings.API_V1_PREFIX, tags=["experiments"])
app.include_router(usage.router, prefix=settings.API_V1_PREFIX, tags=["usage"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)