"""API error handling and typed exception mapping."""

from __future__ import annotations

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ..logging import get_logger

logger = get_logger(__name__)


class APIError(HTTPException):
    """Base API error with machine-readable error code."""

    def __init__(
        self, status_code: int, error_code: str, detail: str, extra: dict | None = None
    ) -> None:
        self.error_code = error_code
        self.extra = extra or {}
        super().__init__(status_code=status_code, detail=detail)


class InvalidCompanyUrlError(APIError):
    def __init__(self, url: str, reason: str = "Invalid URL") -> None:
        super().__init__(400, "INVALID_COMPANY_URL", f"{reason}: {url}")


class SchemaNotFoundError(APIError):
    def __init__(self, schema_id: str) -> None:
        super().__init__(404, "SCHEMA_NOT_FOUND", f"Schema not found: {schema_id}")


class CompanyNotFoundError(APIError):
    def __init__(self, company_id: str) -> None:
        super().__init__(404, "COMPANY_NOT_FOUND", f"Company not found: {company_id}")


class ExternalToolTimeoutError(APIError):
    def __init__(self, tool: str) -> None:
        super().__init__(504, "TOOL_TIMEOUT", f"External tool timed out: {tool}")


class LLMProviderError(APIError):
    def __init__(self, detail: str = "LLM provider error") -> None:
        super().__init__(502, "LLM_PROVIDER_ERROR", detail)


class SurrealPersistenceError(APIError):
    def __init__(self, detail: str = "Database error") -> None:
        super().__init__(500, "DB_ERROR", detail)


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    """Global handler for API errors."""
    logger.error(
        "api_error",
        error_code=exc.error_code,
        detail=exc.detail,
        path=str(request.url),
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.error_code,
                "message": exc.detail,
                "details": exc.extra,
            }
        },
    )
