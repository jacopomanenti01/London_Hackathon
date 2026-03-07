"""Azure OpenAI LLM adapter implementation."""

from __future__ import annotations

import json
import time
from urllib.parse import urlsplit
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ...logging import get_logger
from ...settings import AzureLLMSettings
from .base import LLMAdapter
from .models import LLMRequest, LLMResponse, LLMUsage, StructuredLLMRequest

logger = get_logger(__name__)


class AzureOpenAIAdapter(LLMAdapter):
    """Azure OpenAI-compatible LLM adapter.

    Supports chat completions and structured (JSON mode) generation.
    Handles retries, timeouts, and rate-limit backoff. Captures prompt
    version, model, token usage, latency, and failure metadata.
    """

    def __init__(self, settings: AzureLLMSettings) -> None:
        self._settings = settings
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(settings.timeout_seconds),
            headers={
                "api-key": settings.api_key,
                "Content-Type": "application/json",
            },
        )

    def _is_foundry_endpoint(self) -> bool:
        """Return True when endpoint targets Azure AI Foundry inference."""
        return "services.ai.azure.com" in self._settings.endpoint

    def _effective_api_version(self) -> str:
        """Return API version adjusted for endpoint family when needed."""
        if self._is_foundry_endpoint() and self._settings.api_version == "2024-10-21":
            # 2024-10-21 is for Azure OpenAI data plane; Foundry chat endpoints
            # commonly require the inference preview version.
            return "2024-05-01-preview"
        return self._settings.api_version

    def _build_url(self, deployment: str | None = None) -> tuple[str, bool]:
        """Build the chat completions URL.

        Returns:
            (url, include_model_in_payload)
        """
        deploy = deployment or self._settings.deployment_name
        base = self._settings.endpoint.rstrip("/")
        api_version = self._effective_api_version()
        if self._is_foundry_endpoint():
            # Azure AI Foundry project URL:
            #   https://<resource>.services.ai.azure.com/api/projects/<project>
            # Azure AI Foundry resource URL:
            #   https://<resource>.services.ai.azure.com
            if "/api/projects/" in base:
                # Project endpoint does not always expose chat/completions for the
                # same API versions as inference endpoints; normalize to /models.
                parsed = urlsplit(base)
                root = f"{parsed.scheme}://{parsed.netloc}"
                return (
                    f"{root}/models/chat/completions?api-version={api_version}",
                    True,
                )
            if base.endswith("/models"):
                return (
                    f"{base}/chat/completions?api-version={api_version}",
                    True,
                )
            return (
                f"{base}/models/chat/completions?api-version={api_version}",
                True,
            )

        return (
            f"{base}/openai/deployments/{deploy}"
            f"/chat/completions?api-version={api_version}",
            False,
        )

    def _build_messages(self, messages: list[Any]) -> list[dict[str, str]]:
        """Convert LLMMessage objects to API format."""
        return [{"role": m.role, "content": m.content} for m in messages]

    def _request_timeout_for_task(self, task_type: str) -> float:
        """Return per-task timeout to reduce false timeouts on long generations."""
        base = float(self._settings.timeout_seconds)
        if task_type == "synthesis":
            return max(base, 180.0)
        if task_type == "extraction":
            return max(base, 90.0)
        return base

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a chat completion via Azure OpenAI.

        Args:
            request: The LLM request envelope.

        Returns:
            Normalized response with content, usage, and latency.
        """
        url, include_model = self._build_url(request.deployment)
        payload: dict[str, Any] = {
            "messages": self._build_messages(request.messages),
            "temperature": request.temperature,
            "top_p": request.top_p,
        }
        if include_model:
            payload["max_completion_tokens"] = request.max_tokens
        else:
            payload["max_tokens"] = request.max_tokens
        if include_model:
            payload["model"] = request.deployment or self._settings.deployment_name

        start = time.monotonic()
        try:
            resp = await self._client.post(
                url,
                json=payload,
                timeout=self._request_timeout_for_task(request.task_type),
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "llm_request_failed",
                status_code=e.response.status_code,
                response_text=e.response.text[:1000],
                request_url=str(e.request.url) if e.request else None,
                task_type=request.task_type,
            )
            raise
        except httpx.RequestError as e:
            logger.error(
                "llm_request_error",
                error=str(e),
                error_type=type(e).__name__,
                error_repr=repr(e),
                task_type=request.task_type,
            )
            raise

        latency_ms = (time.monotonic() - start) * 1000

        content = data["choices"][0]["message"]["content"]
        usage_data = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        logger.info(
            "llm_generate",
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
            provider="azure_openai",
            metadata={"deployment": request.deployment or self._settings.deployment_name},
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=30),
        reraise=True,
    )
    async def generate_structured(
        self, request: StructuredLLMRequest
    ) -> LLMResponse:
        """Generate a structured (JSON) completion via Azure OpenAI.

        Uses JSON mode or response_format to enforce structured output.

        Args:
            request: The structured LLM request with response schema.

        Returns:
            Normalized response with structured_output parsed from JSON.
        """
        url, include_model = self._build_url(request.deployment)

        # Add schema instruction to system message
        schema_instruction = (
            f"You MUST respond with valid JSON matching this schema:\n"
            f"{json.dumps(request.response_schema, indent=2)}"
        )
        messages = self._build_messages(request.messages)
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] += f"\n\n{schema_instruction}"
        else:
            messages.insert(0, {"role": "system", "content": schema_instruction})

        payload: dict[str, Any] = {
            "messages": messages,
            "temperature": request.temperature,
            "response_format": {"type": "json_object"},
        }
        if include_model:
            payload["max_completion_tokens"] = request.max_tokens
        else:
            payload["max_tokens"] = request.max_tokens
        if include_model:
            payload["model"] = request.deployment or self._settings.deployment_name

        start = time.monotonic()
        try:
            resp = await self._client.post(
                url,
                json=payload,
                timeout=self._request_timeout_for_task(request.task_type),
            )
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "llm_structured_request_failed",
                status_code=e.response.status_code,
                response_text=e.response.text[:1000],
                request_url=str(e.request.url) if e.request else None,
                task_type=request.task_type,
            )
            raise
        except httpx.RequestError as e:
            logger.error(
                "llm_structured_request_error",
                error=str(e),
                error_type=type(e).__name__,
                error_repr=repr(e),
                task_type=request.task_type,
            )
            raise

        latency_ms = (time.monotonic() - start) * 1000

        content = data["choices"][0]["message"]["content"]
        usage_data = data.get("usage", {})
        usage = LLMUsage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

        # Parse JSON content
        try:
            structured_output = json.loads(content)
        except json.JSONDecodeError:
            logger.warning("llm_structured_parse_failed", content_preview=content[:200])
            structured_output = None

        logger.info(
            "llm_generate_structured",
            task_type=request.task_type,
            model=data.get("model"),
            tokens=usage.total_tokens,
            latency_ms=round(latency_ms, 1),
            parsed=structured_output is not None,
        )

        return LLMResponse(
            content=content,
            structured_output=structured_output,
            model=data.get("model"),
            usage=usage,
            latency_ms=latency_ms,
            provider="azure_openai",
            metadata={"deployment": request.deployment or self._settings.deployment_name},
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
