"""
Health Check Router
===================
Endpoints for monitoring API health and status.
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel


# Track server start time for uptime calculation
_start_time = time.time()

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    uptime_seconds: int
    
    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-02-05T17:30:00+00:00",
                "version": "1.0.0",
                "uptime_seconds": 3600
            }
        }


class DetailedHealthResponse(HealthResponse):
    """Detailed health check with component status."""
    components: dict[str, str]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the health status of the API server.",
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.
    
    This endpoint does not require authentication.
    Useful for load balancers and monitoring systems.
    """
    uptime = int(time.time() - _start_time)
    
    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        uptime_seconds=uptime,
    )


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed Health Check",
    description="Returns detailed health status including component checks.",
)
async def detailed_health_check() -> DetailedHealthResponse:
    """
    Detailed health check with component status.
    
    Checks:
    - API server status
    - Data files availability
    - Memory usage (placeholder)
    """
    from mock_server.data.loader import DATA_DIR
    
    uptime = int(time.time() - _start_time)
    
    # Check data files
    data_status = "healthy" if DATA_DIR.exists() else "unhealthy"
    
    components = {
        "api_server": "healthy",
        "data_files": data_status,
        "authentication": "healthy",
    }
    
    # Overall status is unhealthy if any component is unhealthy
    overall_status = "healthy" if all(v == "healthy" for v in components.values()) else "degraded"
    
    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        uptime_seconds=uptime,
        components=components,
    )


@router.get(
    "/ready",
    summary="Readiness Check",
    description="Returns 200 if the server is ready to accept requests.",
)
async def readiness_check() -> dict:
    """
    Kubernetes-style readiness probe.
    
    Returns 200 if the server can handle requests.
    """
    return {"ready": True}


@router.get(
    "/live",
    summary="Liveness Check",
    description="Returns 200 if the server is alive.",
)
async def liveness_check() -> dict:
    """
    Kubernetes-style liveness probe.
    
    Returns 200 if the server process is running.
    """
    return {"alive": True}
