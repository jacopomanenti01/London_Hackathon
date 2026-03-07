"""FastAPI application entry point.

Start with: uvicorn dd_platform.main:app --reload --port 8080
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.deps import AppDependencies
from .api.errors import APIError, api_error_handler
from .api.router import create_api_router
from .logging import setup_logging
from .settings import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown hooks."""
    settings = get_settings()
    setup_logging(settings.log_level)

    # Initialize all dependencies
    deps = AppDependencies(settings)
    await deps.startup()
    app.state.deps = deps

    yield

    # Cleanup
    await deps.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Company Due Diligence Agent Platform",
        description=(
            "AI-powered platform for building, updating, and chatting with "
            "company due diligence profiles. Uses GraphRAG retrieval and "
            "LangGraph orchestration for supply-chain risk analysis."
        ),
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Error handlers
    app.add_exception_handler(APIError, api_error_handler)  # type: ignore[arg-type]

    # Routes
    app.include_router(create_api_router())

    return app


app = create_app()
