"""Tavily search tool integration.

Tavily is used for broad topical search and extraction-rich workflows.
"""

from __future__ import annotations

import time
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from ...logging import get_logger
from ...settings import TavilySettings
from .base import ResearchTool, SearchResult, ToolInput, ToolOutput

logger = get_logger(__name__)


class TavilyTool(ResearchTool):
    """Tavily search API wrapper.

    Provides broad web search with content extraction capabilities.
    Results are normalized into the common SearchResult envelope.
    """

    name = "tavily"

    def __init__(self, settings: TavilySettings) -> None:
        self._settings = settings
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-initialize the Tavily client."""
        if self._client is None:
            from tavily import AsyncTavilyClient

            self._client = AsyncTavilyClient(api_key=self._settings.api_key)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        reraise=True,
    )
    async def execute(self, tool_input: ToolInput) -> ToolOutput:
        """Execute a Tavily search query.

        Args:
            tool_input: Search parameters including query and filters.

        Returns:
            Normalized tool output with Tavily results.
        """
        start = time.monotonic()
        try:
            client = self._get_client()
            search_params: dict[str, Any] = {
                "query": tool_input.query,
                "max_results": min(tool_input.max_results, self._settings.max_results),
                "search_depth": tool_input.search_depth,
            }

            if tool_input.include_domains:
                search_params["include_domains"] = tool_input.include_domains
            if tool_input.exclude_domains:
                search_params["exclude_domains"] = tool_input.exclude_domains

            response = await client.search(**search_params)

            results = []
            for i, item in enumerate(response.get("results", [])):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("content", ""),
                        provider="tavily",
                        source_type=self._classify_source(item.get("url", "")),
                        rank=i,
                        score=item.get("score"),
                        content_text=item.get("raw_content"),
                        metadata={"tavily_score": item.get("score")},
                    )
                )

            latency_ms = (time.monotonic() - start) * 1000
            logger.info(
                "tavily_search",
                query=tool_input.query,
                result_count=len(results),
                latency_ms=round(latency_ms, 1),
            )

            return ToolOutput(
                provider="tavily",
                query=tool_input.query,
                results=results,
                total_results=len(results),
                latency_ms=latency_ms,
                success=True,
            )

        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            logger.error("tavily_search_failed", error=str(e), query=tool_input.query)
            return ToolOutput(
                provider="tavily",
                query=tool_input.query,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )

    @staticmethod
    def _classify_source(url: str) -> str:
        """Attempt to classify source type from URL patterns."""
        url_lower = url.lower()
        if any(d in url_lower for d in [".gov", "registry", "sec.gov"]):
            return "registry"
        if any(d in url_lower for d in ["news", "reuters", "bloomberg", "bbc"]):
            return "news"
        if any(d in url_lower for d in ["linkedin", "twitter", "facebook"]):
            return "social_mention"
        return "search_result"
