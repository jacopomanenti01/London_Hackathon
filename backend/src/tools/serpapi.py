import os
from serpapi import GoogleSearch

from .base import BaseSearchTool, SearchResult

class SerpApiTool(BaseSearchTool):
    name = "serpapi"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        params = {
            "q": query,
            "api_key": self.api_key,
            "num": max_results,
        }
        search = GoogleSearch(params)
        data = search.get_dict()

        results = []
        for item in data.get("organic_results", [])[:max_results]:
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                content=item.get("snippet", ""),
                source="serpapi",
            ))
        return results
