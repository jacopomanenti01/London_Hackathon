"""Retrieval interfaces and query models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field

from ..domain.retrieval import RetrievalResult


class RetrievalQuery(BaseModel):
    """A query sent to the retrieval layer."""

    company_id: str
    query_text: str = ""
    section_ids: list[str] = Field(default_factory=list)
    field_ids: list[str] = Field(default_factory=list)
    retrieval_profile: str = "hybrid_basic"
    top_k: int = 20
    freshness_required: bool = False
    include_contradictions: bool = True
    graph_hops: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class Retriever(ABC):
    """Base retriever interface."""

    name: str = "base"

    @abstractmethod
    async def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        """Execute a retrieval query.

        Args:
            query: The retrieval query parameters.

        Returns:
            Ranked list of retrieval results.
        """
        ...
