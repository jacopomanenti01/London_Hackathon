"""Retrieval service — search and retrieval across multiple strategies."""

from __future__ import annotations

from typing import Any

from ...domain.retrieval import RetrievalContext, RetrievalResult
from ...logging import get_logger
from ...persistence.surreal.repositories.evidence_repo import EvidenceRepository
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
        evidence_repo: EvidenceRepository | None = None,
    ) -> None:
        self._retriever = retriever
        self._assembler = context_assembler
        self._evidence_repo = evidence_repo

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
        if not results and self._evidence_repo:
            # Resilient fallback: return latest persisted evidence when
            # retriever strategies produce no candidates.
            results = await self._fallback_results(company_id, section_ids, top_k, retrieval_profile)

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

    async def _fallback_results(
        self,
        company_id: str,
        section_ids: list[str] | None,
        top_k: int,
        retrieval_profile: str,
    ) -> list[RetrievalResult]:
        """Build retrieval results from persisted evidence as a fallback."""
        section_filter = section_ids[0] if section_ids else None
        evidence_rows = await self._evidence_repo.find_by_company(  # type: ignore[union-attr]
            company_id=company_id,
            section_id=section_filter,
            limit=top_k,
        )

        fallback_results: list[RetrievalResult] = []
        for idx, ev in enumerate(evidence_rows):
            fallback_results.append(
                RetrievalResult(
                    result_type="evidence",
                    score=max(0.0, float(ev.confidence or 0.0)),
                    score_breakdown={"fallback_evidence": 1.0},
                    text_snippet=ev.excerpt or "",
                    section_id=ev.section_id,
                    field_id=ev.field_id,
                    retrieval_profile=retrieval_profile,
                    provenance_path=[ev.id or f"fallback_evidence_{idx}"],
                    metadata={"fallback": True},
                )
            )

        logger.info(
            "retrieval_fallback_used",
            company_id=company_id,
            results=len(fallback_results),
            section_filter=section_filter,
        )
        return fallback_results
