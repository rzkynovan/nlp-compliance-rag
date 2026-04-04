from fastapi import APIRouter
from datetime import datetime
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/ready")
async def readiness_check():
    checks = {
        "chromadb": "unknown",
        "redis": "unknown",
        "mlflow": "unknown"
    }
    
    try:
        from chromadb import Client
        client = Client()
        client.heartbeat()
        checks["chromadb"] = "healthy"
    except Exception:
        checks["chromadb"] = "unhealthy"
    
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        checks["redis"] = "healthy"
    except Exception:
        checks["redis"] = "unhealthy"
    
    try:
        import requests
        response = requests.get(f"{settings.MLFLOW_TRACKING_URI}/health", timeout=2)
        if response.status_code == 200:
            checks["mlflow"] = "healthy"
    except Exception:
        checks["mlflow"] = "unhealthy"
    
    all_healthy = all(v == "healthy" or v == "unknown" for v in checks.values())
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks,
        "timestamp": datetime.now().isoformat()
    }