"""SerpAPI search tool integration.

SerpAPI is used for search engine coverage and result diversity.
"""

from __future__ import annotations

import time
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from ...logging import get_logger
from ...settings import SerpAPISettings
from .base import ResearchTool, SearchResult, ToolInput, ToolOutput

logger = get_logger(__name__)


class SerpAPITool(ResearchTool):
    """SerpAPI search wrapper.

    Provides Google Search results with structured metadata.
    Results are normalized into the common SearchResult envelope.
    """

    name = "serpapi"

    def __init__(self, settings: SerpAPISettings) -> None:
        self._settings = settings

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        reraise=True,
    )
    async def execute(self, tool_input: ToolInput) -> ToolOutput:
        """Execute a SerpAPI search query.

        Args:
            tool_input: Search parameters.

        Returns:
            Normalized tool output with SerpAPI results.
        """
        start = time.monotonic()
        try:
            from serpapi import GoogleSearch

            params: dict[str, Any] = {
                "q": tool_input.query,
                "api_key": self._settings.api_key,
                "num": min(tool_input.max_results, self._settings.max_results),
                "engine": "google",
            }

            # SerpAPI is synchronous — run in executor for async compatibility
            import asyncio
            loop = asyncio.get_event_loop()
            search = GoogleSearch(params)
            response = await loop.run_in_executor(None, search.get_dict)

            results = []
            organic = response.get("organic_results", [])
            for i, item in enumerate(organic):
                results.append(
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("link", ""),
                        snippet=item.get("snippet", ""),
                        provider="serpapi",
                        source_type="search_result",
                        rank=i,
                        metadata={
                            "position": item.get("position"),
                            "displayed_link": item.get("displayed_link"),
                        },
                    )
                )

            latency_ms = (time.monotonic() - start) * 1000
            logger.info(
                "serpapi_search",
                query=tool_input.query,
                result_count=len(results),
                latency_ms=round(latency_ms, 1),
            )

            return ToolOutput(
                provider="serpapi",
                query=tool_input.query,
                results=results,
                total_results=len(results),
                latency_ms=latency_ms,
                success=True,
            )

        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            logger.error("serpapi_search_failed", error=str(e), query=tool_input.query)
            return ToolOutput(
                provider="serpapi",
                query=tool_input.query,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )
