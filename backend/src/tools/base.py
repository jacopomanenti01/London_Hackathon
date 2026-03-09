from abc import ABC, abstractmethod
from pydantic import BaseModel


class SearchResult(BaseModel):
    title: str = ""
    url: str = ""
    content: str = ""
    source: str = ""


class BaseSearchTool(ABC):
    name: str = "base"

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        ...
