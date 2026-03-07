"""Central API router — assembles all route modules."""

from __future__ import annotations

from fastapi import APIRouter

from .routes import chat, continuation, health, profile, retrieval, schemas


def create_api_router() -> APIRouter:
    """Create and return the assembled API router."""
    api_router = APIRouter()

    # Health (no prefix)
    api_router.include_router(health.router)

    # Profile endpoints
    api_router.include_router(profile.router)

    # Chat endpoint
    api_router.include_router(chat.router)

    # Continuation research
    api_router.include_router(continuation.router)

    # Retrieval search
    api_router.include_router(retrieval.router)

    # Schema management
    api_router.include_router(schemas.router)

    return api_router
