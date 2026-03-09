"""OpenRouter LLM adapter implementation."""

from __future__ import annotations

import json
import time
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ...logging import get_logger
from ...settings import OpenRouterLLMSettings
from .base import LLMAdapter
from .models import LLMRequest, LLMResponse, LLMUsage, StructuredLLMRequest

logger = get_logger(__name__)


class OpenRouterAdapter(LLMAdapter):
    """OpenRouter-compatible LLM adapter using chat completions API."""

    def __init__(self, settings: OpenRouterLLMSettings) -> None:
        self._settings = settings
        headers: dict[str, str] = {
            "Authorization": f"Bearer {settings.api_key}",
            "Content-Type": "application/json",
        }
        if settings.http_referer:
            headers["HTTP-Referer"] = settings.http_referer
        if settings.x_title:
            headers["X-Title"] = settings.x_title

        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.timeout_seconds),
            headers=headers,
        )

    def _build_url(self) -> str:
        return f"{self._settings.base_url.rstrip('/')}/chat/completions"

    def _model_name(self, request: LLMRequest | StructuredLLMRequest) -> str:
        return request.deployment or request.model or self._settings.model

    def _build_messages(self, messages: list[Any]) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in messages]

    def _log_raw_response(self, data: dict[str, Any], task_type: str, structured: bool) -> None:
        choices = data.get("choices", [])
        first_choice = choices[0] if choices else {}
        message = first_choice.get("message", {}) if isinstance(first_choice, dict) else {}
        raw_content = message.get("content")
        logger.info(
            "llm_raw_response",
            provider="openrouter",
            task_type=task_type,
            structured=structured,
            finish_reason=(
                first_choice.get("finish_reason") if isinstance(first_choice, dict) else None
            ),
            content_type=type(raw_content).__name__,
            content_preview=str(raw_content)[:2000],
            response_preview=json.dumps(data, default=str)[:3000],
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a chat completion via OpenRouter."""
        payload: dict[str, Any] = {
            "model": self._model_name(request),
            "messages": self._build_messages(request.messages),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "max_tokens": request.max_tokens,
        }

        start = time.monotonic()
        try:
            resp = await self._client.post(self._build_url(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            self._log_raw_response(data, request.task_type, structured=False)
        except httpx.HTTPStatusError as e:
            logger.error(
                "llm_request_failed",
                provider="openrouter",
                status_code=e.response.status_code,
                response_text=e.response.text[:1000],
                request_url=str(e.request.url) if e.request else None,
                task_type=request.task_type,
            )
            raise
        except httpx.RequestError as e:
            logger.error(
                "llm_request_error",
                provider="openrouter",
                error=str(e),
                error_type=type(e).__name__,
                error_repr=repr(e),
                task_type=request.task_type,
            )
            raise

        latency_ms = (time.monotonic() - start) * 1000
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        usage_data = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=int(usage_data.get("prompt_tokens", 0)),
            completion_tokens=int(usage_data.get("completion_tokens", 0)),
            total_tokens=int(usage_data.get("total_tokens", 0)),
        )

        logger.info(
            "llm_generate",
            provider="openrouter",
            task_type=request.task_type,
            model=data.get("model"),
            tokens=usage.total_tokens,
            latency_ms=round(latency_ms, 1),
        )

        return LLMResponse(
            content=content,
            model=data.get("model"),
            usage=usage,
            latency_ms=latency_ms,
            provider="openrouter",
            metadata={"model": self._model_name(request)},
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def generate_structured(self, request: StructuredLLMRequest) -> LLMResponse:
        """Generate structured JSON output via OpenRouter."""
        payload: dict[str, Any] = {
            "model": self._model_name(request),
            "messages": self._build_messages(request.messages),
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "response_format": {"type": "json_object"},
        }

        start = time.monotonic()
        try:
            resp = await self._client.post(self._build_url(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            self._log_raw_response(data, request.task_type, structured=True)
        except httpx.HTTPStatusError as e:
            logger.error(
                "llm_structured_request_failed",
                provider="openrouter",
                status_code=e.response.status_code,
                response_text=e.response.text[:1000],
                request_url=str(e.request.url) if e.request else None,
                task_type=request.task_type,
            )
            raise
        except httpx.RequestError as e:
            logger.error(
                "llm_structured_request_error",
                provider="openrouter",
                error=str(e),
                error_type=type(e).__name__,
                error_repr=repr(e),
                task_type=request.task_type,
            )
            raise

        latency_ms = (time.monotonic() - start) * 1000
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

        usage_data = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=int(usage_data.get("prompt_tokens", 0)),
            completion_tokens=int(usage_data.get("completion_tokens", 0)),
            total_tokens=int(usage_data.get("total_tokens", 0)),
        )

        try:
            structured_output = json.loads(content)
        except json.JSONDecodeError:
            logger.warning(
                "llm_structured_parse_failed",
                provider="openrouter",
                content_preview=content[:200],
            )
            structured_output = None

        logger.info(
            "llm_generate_structured",
            provider="openrouter",
            task_type=request.task_type,
            model=data.get("model"),
            tokens=usage.total_tokens,
            latency_ms=round(latency_ms, 1),
            parsed=structured_output is not None,
        )

        return LLMResponse(
            content=content,
            structured_output=structured_output if isinstance(structured_output, dict) else None,
            model=data.get("model"),
            usage=usage,
            latency_ms=latency_ms,
            provider="openrouter",
            metadata={"model": self._model_name(request)},
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
