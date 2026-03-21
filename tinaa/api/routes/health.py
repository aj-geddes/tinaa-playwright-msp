"""Health and root endpoint routes."""

from datetime import UTC, datetime

from fastapi import APIRouter

router = APIRouter()

API_VERSION = "2.0.0"


@router.get(
    "/health",
    summary="Health check",
    description="Returns service health status and version.",
)
async def health_check() -> dict:
    """Return current health status."""
    return {
        "status": "healthy",
        "version": API_VERSION,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get(
    "/",
    summary="API root",
    description="Returns service name, version, and docs URL.",
)
async def root() -> dict:
    """Return API root information."""
    return {
        "name": "TINAA MSP",
        "version": API_VERSION,
        "docs": "/api/docs",
    }
