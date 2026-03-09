import asyncio
import logging
import os
import re
from apify_client import ApifyClientAsync

from .base import BaseSearchTool, SearchResult

logger = logging.getLogger(__name__)

DEFAULT_ACTOR = "apify/website-content-crawler"
LINKEDIN_PEOPLE_ACTOR = "harvestapi/linkedin-company-employees"


def _get_client(api_key: str | None = None) -> ApifyClientAsync:
    return ApifyClientAsync(token=api_key or os.getenv("APIFY_API_KEY", ""))


def _extract_url(query: str) -> str:
    match = re.search(r"https?://\S+", query)
    return match.group(0) if match else query


class ApifyTool(BaseSearchTool):
    name = "apify"

    def __init__(self, api_key: str | None = None, actor_id: str = DEFAULT_ACTOR, max_crawl_pages: int = 10):
        self.client = _get_client(api_key)
        self.actor_id = actor_id
        self.max_crawl_pages = max_crawl_pages
        self._cache: dict[str, list[SearchResult]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        url = _extract_url(query)
        if url in self._cache:
            logger.info("[ApifyTool] Cache hit for %s", url)
            return self._cache[url]

        if url not in self._locks:
            self._locks[url] = asyncio.Lock()
        async with self._locks[url]:
            if url in self._cache:
                logger.info("[ApifyTool] Cache hit for %s", url)
                return self._cache[url]
            logger.info("[ApifyTool] Crawling %s (max %d pages)", url, self.max_crawl_pages)

            run_input = {
                "startUrls": [{"url": url}],
                "maxCrawlPages": self.max_crawl_pages,
                "crawlerType": "playwright:adaptive",
                "maxConcurrency": 10,
                "navigationTimeoutSecs": 15,
                "requestTimeoutSecs": 30,
                "maxRequestRetries": 1,
            }
            run = await self.client.actor(self.actor_id).call(run_input=run_input, timeout_secs=60)
            if not run:
                return []
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                return []

            items = await self.client.dataset(dataset_id).list_items()
            results = []
            for item in (items.items if items else [])[:self.max_crawl_pages]:
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", url),
                    content=item.get("text", ""),
                    source="apify",
                ))
            self._cache[url] = results
            return results


class LinkedInPeopleTool(BaseSearchTool):
    name = "linkedin_people"

    def __init__(self, api_key: str | None = None):
        self.client = _get_client(api_key)
        self._cache: dict[str, list[SearchResult]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        url = _extract_url(query)
        if url in self._cache:
            logger.info("[LinkedInPeopleTool] Cache hit for %s", url)
            return self._cache[url]

        # Prevent parallel duplicate actor runs for the same URL
        if url not in self._locks:
            self._locks[url] = asyncio.Lock()
        async with self._locks[url]:
            if url in self._cache:
                return self._cache[url]

            # Pass company name so the actor can search LinkedIn for the right page
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace("www.", "")
            company_name = domain.split(".")[0]

            logger.info("[LinkedInPeopleTool] Searching LinkedIn for '%s'", company_name)

            run_input = {
                "companies": [company_name],
                "maxItems": max_results,
            }
            try:
                run = await self.client.actor(LINKEDIN_PEOPLE_ACTOR).call(
                    run_input=run_input, timeout_secs=60,
                )
            except Exception:
                logger.exception("[LinkedInPeopleTool] Actor call failed")
                return []
            if not run:
                return []
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                return []

            items = await self.client.dataset(dataset_id).list_items()
            results = []
            for item in (items.items if items else [])[:max_results]:
                first = item.get("firstName", "")
                last = item.get("lastName", "")
                name = f"{first} {last}".strip()
                position = item.get("headline", "")
                profile_url = item.get("linkedinUrl", "")
                content = f"{name} - {position}" if position else name
                results.append(SearchResult(
                    title=name,
                    url=profile_url,
                    content=content,
                    source="linkedin_people",
                ))

            self._cache[url] = results
            logger.info("[LinkedInPeopleTool] Found %d people for %s", len(results), company_name)
            return results
