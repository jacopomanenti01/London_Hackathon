"""LLM request and response models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """A single message in an LLM conversation."""

    role: str = "user"  # system, user, assistant
    content: str = ""


class LLMRequest(BaseModel):
    """Request envelope for LLM generation."""

    messages: list[LLMMessage]
    model: str | None = None
    deployment: str | None = None
    temperature: float = 0.2
    max_tokens: int = 4096
    top_p: float = 1.0
    task_type: str = "general"  # general, extraction, synthesis, planning, chat
    metadata: dict[str, Any] = Field(default_factory=dict)


class StructuredLLMRequest(BaseModel):
    """Request envelope for structured LLM output."""

    messages: list[LLMMessage]
    response_schema: dict[str, Any]
    model: str | None = None
    deployment: str | None = None
    temperature: float = 0.1
    max_tokens: int = 4096
    task_type: str = "extraction"
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMUsage(BaseModel):
    """Token usage metadata."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResponse(BaseModel):
    """Normalized LLM response."""

    content: str = ""
    structured_output: dict[str, Any] | None = None
    model: str | None = None
    usage: LLMUsage = Field(default_factory=LLMUsage)
    latency_ms: float = 0.0
    provider: str = "azure_openai"
    metadata: dict[str, Any] = Field(default_factory=dict)
