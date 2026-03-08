import os
from tavily import AsyncTavilyClient

from .base import BaseSearchTool, SearchResult

class TavilyTool(BaseSearchTool):
    name = "tavily"

    def __init__(self, api_key: str | None = None):
        self.client = AsyncTavilyClient(api_key=api_key or os.getenv("TAVILY_API_KEY", ""))

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        response = await self.client.search(query=query, max_results=max_results)
        results = []
        for item in response.get("results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=item.get("content", ""),
                source="tavily",
            ))
        return results
