"""
Health check endpoints for monitoring and load balancers.
"""

import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.health import HealthResponse
from app.utils.cache.manager import get_cache_manager

router = APIRouter()


@router.get(
    "/health",
    response_model=Dict[str, Any],
    summary="Basic health check",
    description="Simple health check endpoint for load balancers",
)
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "weather-api",
    }


@router.get(
    "/health/detailed",
    response_model=HealthResponse,
    summary="Detailed health check",
    description="Comprehensive health check with service dependencies",
)
async def detailed_health_check(db: Session = Depends(get_db)):
    """Detailed health check with all dependencies."""
    try:
        services = {}
        overall_status = "healthy"

        # Database health
        try:
            db_start = time.time()
            db.execute(text("SELECT 1")).scalar()
            db_time = (time.time() - db_start) * 1000

            services["database"] = {
                "status": "healthy",
                "response_time_ms": round(db_time, 2),
            }
        except Exception as e:
            services["database"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "degraded"

        # Cache health
        try:
            cache_start = time.time()
            cache_manager = await get_cache_manager()
            await cache_manager.get("health_check")
            cache_time = (time.time() - cache_start) * 1000

            services["cache"] = {
                "status": "healthy",
                "response_time_ms": round(cache_time, 2),
            }
        except Exception as e:
            services["cache"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "degraded"

        return HealthResponse(
            status=overall_status,
            version="1.0.0",
            timestamp=time.time(),
            services=services,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}",
        )
