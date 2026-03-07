"""Retrieval service — search and retrieval across multiple strategies."""

from __future__ import annotations

from typing import Any

from ...domain.retrieval import RetrievalContext
from ...logging import get_logger
from ...retrieval.assembler import ContextAssembler
from ...retrieval.interfaces import Retriever, RetrievalQuery

logger = get_logger(__name__)


class RetrievalService:
    """Provides retrieval across graph, keyword, vector, and hybrid modes.

    Exposes a unified search interface with ranking metadata, provenance,
    and retrieval profile selection.
    """

    def __init__(
        self,
        retriever: Retriever,
        context_assembler: ContextAssembler,
    ) -> None:
        self._retriever = retriever
        self._assembler = context_assembler

    async def search(
        self,
        company_id: str,
        query: str,
        retrieval_profile: str = "hybrid_basic",
        section_ids: list[str] | None = None,
        top_k: int = 20,
    ) -> dict[str, Any]:
        """Execute a retrieval search with provenance metadata.

        Args:
            company_id: The company scope.
            query: Search query text.
            retrieval_profile: The retrieval strategy to use.
            section_ids: Optional section filters.
            top_k: Max results.

        Returns:
            Dict with ranked results, provenance, and scoring metadata.
        """
        retrieval_query = RetrievalQuery(
            company_id=company_id,
            query_text=query,
            section_ids=section_ids or [],
            retrieval_profile=retrieval_profile,
            top_k=top_k,
        )

        results = await self._retriever.retrieve(retrieval_query)

        context = self._assembler.assemble(
            company_id=company_id,
            retrieval_profile=retrieval_profile,
            results=results,
        )

        return {
            "company_id": company_id,
            "query": query,
            "retrieval_profile": retrieval_profile,
            "results": [r.model_dump() for r in context.results],
            "total_candidates": context.total_candidates,
            "selected_count": context.selected_count,
            "sections_covered": context.sections_covered,
            "has_contradictions": context.has_contradictions,
        }
