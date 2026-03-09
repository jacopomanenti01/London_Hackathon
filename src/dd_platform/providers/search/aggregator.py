"""Search result aggregation across multiple providers.

The aggregator fans out to multiple research tools, deduplicates results
by URL/content hash, and preserves provenance per provider.
"""

from __future__ import annotations

import asyncio
from typing import Any

from ...logging import get_logger
from ...utils.hashing import content_hash
from .base import ResearchTool, SearchResult, ToolInput, ToolOutput

logger = get_logger(__name__)


class SearchAggregator:
    """Aggregates search results across multiple research tools.

    Supports fan-out to multiple providers, provider-specific quotas,
    deduplication by canonical URL or content hash, and provenance
    preservation per provider.
    """

    def __init__(self, tools: list[ResearchTool]) -> None:
        self._tools = {tool.name: tool for tool in tools}

    @property
    def available_tools(self) -> list[str]:
        """Return names of available tools."""
        return list(self._tools.keys())

    async def search(
        self,
        tool_input: ToolInput,
        providers: list[str] | None = None,
    ) -> ToolOutput:
        """Execute search across specified or all providers.

        Args:
            tool_input: Common search parameters.
            providers: Specific providers to use, or None for all.

        Returns:
            Merged and deduplicated tool output.
        """
        target_tools = self._resolve_tools(providers)

        # Fan out to all providers concurrently
        tasks = [tool.execute(tool_input) for tool in target_tools]
        outputs: list[ToolOutput] = await asyncio.gather(*tasks, return_exceptions=False)

        # Merge and deduplicate
        all_results: list[SearchResult] = []
        seen_urls: set[str] = set()
        total_latency = 0.0
        errors: list[str] = []

        for output in outputs:
            total_latency = max(total_latency, output.latency_ms)
            if not output.success:
                errors.append(f"{output.provider}: {output.error}")
                continue

            for result in output.results:
                url_key = result.url.lower().rstrip("/")
                if url_key not in seen_urls:
                    seen_urls.add(url_key)
                    all_results.append(result)

        # Sort by score (descending) where available, then by rank
        all_results.sort(
            key=lambda r: (-(r.score or 0.0), r.rank)
        )

        success = len(errors) < len(target_tools)  # At least one provider succeeded

        logger.info(
            "search_aggregated",
            providers=len(target_tools),
            total_results=len(all_results),
            deduplicated_from=sum(o.total_results for o in outputs),
            errors=len(errors),
        )

        return ToolOutput(
            provider="aggregator",
            query=tool_input.query,
            results=all_results,
            total_results=len(all_results),
            latency_ms=total_latency,
            success=success,
            error="; ".join(errors) if errors else None,
        )

    def _resolve_tools(self, providers: list[str] | None) -> list[ResearchTool]:
        """Resolve which tools to use."""
        if providers:
            return [self._tools[p] for p in providers if p in self._tools]
        return list(self._tools.values())
