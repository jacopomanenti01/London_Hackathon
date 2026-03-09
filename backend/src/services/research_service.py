import asyncio
import logging
import os
from typing import Any

from ..tools.base import BaseSearchTool, SearchResult
from ..tools.mock import MockSectionSearchTool

logger = logging.getLogger(__name__)


def _init_tools() -> dict[str, BaseSearchTool]:
    use_mock = os.getenv("USE_MOCK", "true").lower() in ("true", "1", "yes")

    if use_mock:
        logger.info("USE_MOCK=true: using mock search tools")
        mock = MockSectionSearchTool()
        return {
            "tavily": mock,
            "serpapi": mock,
            "apify": mock,
            "linkedin_people": mock,
            "mock": mock,
        }

    # Lazy import real tools only when needed
    from ..tools.tavily import TavilyTool
    from ..tools.serpapi import SerpApiTool
    from ..tools.apify import ApifyTool, LinkedInPeopleTool

    tools: dict[str, BaseSearchTool] = {}
    if os.getenv("TAVILY_API_KEY", "").strip():
        tools["tavily"] = TavilyTool()
    else:
        logger.warning("TAVILY_API_KEY not set, skipping Tavily tool")
    if os.getenv("SERPAPI_API_KEY", "").strip():
        tools["serpapi"] = SerpApiTool()
    else:
        logger.warning("SERPAPI_API_KEY not set, skipping SerpApi tool")
    if os.getenv("APIFY_API_KEY", "").strip():
        tools["apify"] = ApifyTool()
        tools["linkedin_people"] = LinkedInPeopleTool()
    else:
        logger.warning("APIFY_API_KEY not set, skipping Apify tool")
    return tools


class ResearchService:
    def __init__(self, tools: dict[str, BaseSearchTool] | None = None):
        self.tools = tools or _init_tools()

    async def search(
        self,
        query: str,
        sources: list[str] | None = None,
        max_results: int = 5,
    ) -> list[SearchResult]:
        sources = sources or list(self.tools.keys())
        tasks = []
        for source in sources:
            tool = self.tools.get(source)
            if tool:
                tasks.append(tool.search(query, max_results=max_results))

        all_results: list[SearchResult] = []
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, list):
                all_results.extend(result)
        return all_results

    async def research_company(
        self,
        company_url: str,
        queries: dict[str, str],
    ) -> dict[str, list[SearchResult]]:
        section_results: dict[str, list[SearchResult]] = {}
        for section_name, query in queries.items():
            full_query = f"{company_url} {query}"
            section_results[section_name] = await self.search(full_query)
        return section_results
