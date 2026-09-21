"""Health and uptime check endpoint."""

from datetime import datetime, timezone
from fastapi import APIRouter
from app.config import settings

router = APIRouter(tags=["Health"])

_start_time = datetime.now(timezone.utc)


@router.get("/api/health")
async def health_check():
    """Liveness check returning service status, runtime environment, and current timestamp."""
    uptime_seconds = (datetime.now(timezone.utc) - _start_time).total_seconds()
    return {
        "status": "healthy",
        "service": "phishguard-backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(uptime_seconds, 2),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
