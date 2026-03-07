"""Apify actor integration for targeted site crawling.

Apify is used for targeted site crawling, structured page extraction,
or actor-based pipelines.
"""

from __future__ import annotations

import time
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

from ...logging import get_logger
from ...settings import ApifySettings
from .base import ResearchTool, SearchResult, ToolInput, ToolOutput

logger = get_logger(__name__)


class ApifyTool(ResearchTool):
    """Apify actor wrapper for web scraping.

    Runs Apify actors for targeted web crawling and content extraction.
    Results are normalized into the common SearchResult envelope.
    """

    name = "apify"

    def __init__(self, settings: ApifySettings) -> None:
        self._settings = settings
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazy-initialize the Apify client."""
        if self._client is None:
            from apify_client import ApifyClientAsync

            self._client = ApifyClientAsync(token=self._settings.token)
        return self._client

    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        reraise=True,
    )
    async def execute(self, tool_input: ToolInput) -> ToolOutput:
        """Execute an Apify web scraping task.

        For Apify, the query is interpreted as a URL to crawl, or a search
        instruction depending on the actor configuration.

        Args:
            tool_input: Input with query (URL or instruction) and parameters.

        Returns:
            Normalized tool output with scraped content.
        """
        start = time.monotonic()
        try:
            client = self._get_client()
            actor_id = self._settings.web_scraper_actor_id

            # Build actor input
            start_urls = []
            if tool_input.company_host:
                start_urls.append({"url": f"https://{tool_input.company_host}"})
            if tool_input.include_domains:
                for domain in tool_input.include_domains:
                    start_urls.append({"url": f"https://{domain}"})

            if not start_urls:
                # Fall back to using the query as a URL
                start_urls.append({"url": tool_input.query})

            actor_input: dict[str, Any] = {
                "startUrls": start_urls,
                "maxCrawlPages": min(tool_input.max_results, 20),
                "maxCrawlDepth": 2,
            }
            if actor_id == "apify/web-scraper":
                actor_input["pageFunction"] = (
                    "async function pageFunction(context) { "
                    "const { request } = context; "
                    "const title = (typeof document !== 'undefined' && document.title) ? document.title : ''; "
                    "const text = (typeof document !== 'undefined' && document.body && document.body.innerText) ? document.body.innerText : ''; "
                    "return { url: request.url, title, text: text.slice(0, 12000) }; "
                    "}"
                )

            target_urls = [u.get("url", "") for u in start_urls if u.get("url")]
            logger.info(
                "apify_crawl_start",
                actor_id=actor_id,
                query=tool_input.query,
                target_urls=target_urls,
            )

            # Run actor and wait for results
            run = await client.actor(actor_id).call(run_input=actor_input)
            dataset_items = await client.dataset(
                run["defaultDatasetId"]
            ).list_items()

            results = []
            for i, item in enumerate(dataset_items.items or []):
                results.append(
                    SearchResult(
                        title=item.get("title", item.get("pageName", "")),
                        url=item.get("url", item.get("loadedUrl", "")),
                        snippet=item.get("text", item.get("description", ""))[:500],
                        provider="apify",
                        source_type="crawled_page",
                        rank=i,
                        content_text=item.get("text", ""),
                        metadata={
                            "actor_id": actor_id,
                            "crawl_depth": item.get("depth", 0),
                        },
                    )
                )

            latency_ms = (time.monotonic() - start) * 1000
            logger.info(
                "apify_crawl",
                actor_id=actor_id,
                result_count=len(results),
                crawled_urls=[r.url for r in results[:20]],
                latency_ms=round(latency_ms, 1),
            )

            return ToolOutput(
                provider="apify",
                query=tool_input.query,
                results=results,
                total_results=len(results),
                latency_ms=latency_ms,
                success=True,
            )

        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            logger.error("apify_crawl_failed", error=str(e))
            return ToolOutput(
                provider="apify",
                query=tool_input.query,
                success=False,
                error=str(e),
                latency_ms=latency_ms,
            )
