from fastapi import APIRouter, HTTPException
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/usage")
async def get_usage_stats():
    service = AuditService()
    return service.get_usage_stats()


@router.get("/budget")
async def get_budget_status():
    from app.core.cost_tracker import cost_tracker
    return cost_tracker.get_today_stats()


@router.get("/cache")
async def get_cache_stats():
    from app.core.cache import AuditCache
    cache = AuditCache()
    return cache.get_stats()


@router.delete("/cache")
async def clear_cache():
    from app.core.cache import AuditCache
    cache = AuditCache()
    cache.clear()
    return {"message": "Cache cleared"}


@router.get("/rate-limit")
async def get_rate_limit_status():
    from app.core.rate_limiter import rate_limiter
    return rate_limiter.get_stats()