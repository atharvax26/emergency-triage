"""Health check endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database.session import get_async_db
from app.cache.client import RedisClient, get_redis


router = APIRouter(prefix="/api/v1/health", tags=["Health"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    summary="Basic health check",
    description="Returns 200 OK if service is running"
)
async def health_check() -> dict:
    """
    Basic health check endpoint.
    
    Returns:
        Status message indicating service is healthy
    """
    return {
        "status": "healthy",
        "message": "Service is running"
    }


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description="Checks if service is ready to accept traffic (DB and Redis connections)"
)
async def readiness_check(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    cache: Annotated[RedisClient, Depends(get_redis)],
) -> dict:
    """
    Readiness probe endpoint.
    
    Checks database and Redis connectivity to determine if service
    is ready to accept traffic.
    
    Args:
        db: Database session
        cache: Redis client
        
    Returns:
        Status message with component health details
        
    Raises:
        HTTPException: 503 if any component is unhealthy
    """
    checks = {
        "database": False,
        "redis": False,
    }
    
    # Check database connection
    try:
        result = await db.execute(text("SELECT 1"))
        checks["database"] = result.scalar() == 1
    except Exception:
        checks["database"] = False
    
    # Check Redis connection
    try:
        checks["redis"] = await cache.ping()
    except Exception:
        checks["redis"] = False
    
    # Determine overall status
    all_healthy = all(checks.values())
    
    response = {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks
    }
    
    # Return 503 if any component is unhealthy
    if not all_healthy:
        from fastapi import Response
        return Response(
            content=str(response),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json"
        )
    
    return response


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Returns 200 OK if service is alive"
)
async def liveness_check() -> dict:
    """
    Liveness probe endpoint.
    
    Simple check to verify the service process is alive and responding.
    Does not check external dependencies.
    
    Returns:
        Status message indicating service is alive
    """
    return {
        "status": "alive",
        "message": "Service is alive"
    }
