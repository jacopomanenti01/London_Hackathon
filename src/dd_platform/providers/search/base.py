"""Research tool protocol and common models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolInput(BaseModel):
    """Common input for all research tools."""

    query: str
    company_host: str | None = None
    max_results: int = 10
    search_depth: str = "basic"  # basic, advanced
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)
    source_type_hint: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """A single normalized search result from any provider."""

    title: str
    url: str
    snippet: str
    provider: str
    source_type: str = "search_result"
    rank: int = 0
    score: float | None = None
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload_ref: str | None = None
    content_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolOutput(BaseModel):
    """Normalized output envelope from any research tool."""

    provider: str
    query: str
    results: list[SearchResult] = Field(default_factory=list)
    total_results: int = 0
    latency_ms: float = 0.0
    success: bool = True
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResearchTool(ABC):
    """Abstract base class for all research tools.

    Provides a common interface with retries, timeout handling,
    and structured logging of all invocations.
    """

    name: str = "base"

    @abstractmethod
    async def execute(self, tool_input: ToolInput) -> ToolOutput:
        """Execute a research query and return normalized results.

        Args:
            tool_input: The search parameters.

        Returns:
            Normalized tool output with results and metadata.
        """
        ...
