"""Hybrid retriever combining keyword and graph retrieval strategies.

Merges results from multiple retrieval primitives, applies reranking,
and supports configurable retrieval profiles.
"""

from __future__ import annotations

from ..domain.retrieval import RetrievalResult
from ..logging import get_logger
from .interfaces import Retriever, RetrievalQuery

logger = get_logger(__name__)


class HybridRetriever(Retriever):
    """Hybrid retrieval combining multiple retrieval strategies.

    Merges results from keyword and graph retrievers, applies
    score normalization, deduplication, and configurable reranking.
    """

    name = "hybrid"

    def __init__(self, retrievers: list[Retriever], weights: dict[str, float] | None = None) -> None:
        self._retrievers = {r.name: r for r in retrievers}
        self._weights = weights or {r.name: 1.0 for r in retrievers}

    async def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        """Execute hybrid retrieval across all configured retrievers.

        Args:
            query: The retrieval query.

        Returns:
            Merged, deduplicated, and reranked results.
        """
        all_results: dict[str, RetrievalResult] = {}  # key by text snippet hash

        for name, retriever in self._retrievers.items():
            weight = self._weights.get(name, 1.0)
            try:
                results = await retriever.retrieve(query)
                for result in results:
                    key = self._result_key(result)
                    if key in all_results:
                        # Merge scores
                        existing = all_results[key]
                        existing.score += result.score * weight
                        existing.score_breakdown[f"{name}_score"] = result.score * weight
                        existing.provenance_path.extend(result.provenance_path)
                    else:
                        result.score *= weight
                        result.score_breakdown[f"{name}_score"] = result.score
                        result.retrieval_profile = query.retrieval_profile
                        all_results[key] = result

            except Exception as e:
                logger.warning(
                    "retriever_failed",
                    retriever=name,
                    error=str(e),
                )

        # Sort by merged score
        sorted_results = sorted(all_results.values(), key=lambda r: -r.score)

        # Apply contradiction boost if requested
        if query.include_contradictions:
            for result in sorted_results:
                if result.contradiction_flag:
                    result.score *= 1.2
                    result.score_breakdown["contradiction_boost"] = 0.2

        # Re-sort after boosts
        sorted_results.sort(key=lambda r: -r.score)

        logger.info(
            "hybrid_retrieval",
            company_id=query.company_id,
            total_candidates=len(sorted_results),
            retrievers_used=list(self._retrievers.keys()),
            profile=query.retrieval_profile,
        )

        return sorted_results[: query.top_k]

    @staticmethod
    def _result_key(result: RetrievalResult) -> str:
        """Create a deduplication key for a retrieval result."""
        return f"{result.result_type}:{result.text_snippet[:100]}"
