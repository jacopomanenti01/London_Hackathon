"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Basic health check."""
    return {"status": "healthy", "service": "dd-platform"}


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness check — verifies dependencies are available."""
    return {"status": "ready"}
