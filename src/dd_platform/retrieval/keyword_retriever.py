"""Keyword-based retrieval using SurrealDB text matching."""

from __future__ import annotations

from ..domain.retrieval import RetrievalResult
from ..logging import get_logger
from ..persistence.surreal.queries.evidence_search import EvidenceSearchQueries
from .interfaces import Retriever, RetrievalQuery

logger = get_logger(__name__)


class KeywordRetriever(Retriever):
    """Keyword-based evidence and claim retrieval.

    Uses SurrealDB text matching to find relevant evidence
    and claims by keyword overlap.
    """

    name = "keyword"

    def __init__(self, evidence_queries: EvidenceSearchQueries) -> None:
        self._queries = evidence_queries

    async def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        """Retrieve evidence and claims by keyword matching.

        Args:
            query: The retrieval query with keywords extracted from query_text.

        Returns:
            Ranked retrieval results.
        """
        # Extract keywords from query text
        keywords = self._extract_keywords(query.query_text)
        if not keywords:
            return []

        results: list[RetrievalResult] = []

        # Search evidence
        for section_id in query.section_ids or [None]:  # type: ignore[list-item]
            evidence_records = await self._queries.search_by_keyword(
                company_id=query.company_id,
                keywords=keywords,
                section_id=section_id,
                limit=query.top_k,
            )
            for record in evidence_records:
                results.append(
                    RetrievalResult(
                        result_type="evidence",
                        score=record.get("confidence", 0.5),
                        score_breakdown={"keyword_match": 1.0},
                        text_snippet=record.get("excerpt", ""),
                        section_id=record.get("section_id"),
                        field_id=record.get("field_id"),
                        source_url=None,
                        retrieval_profile="keyword_only",
                        provenance_path=[str(record.get("id", ""))],
                    )
                )

        # Search claims
        claim_records = await self._queries.search_claims_by_keyword(
            company_id=query.company_id,
            keywords=keywords,
            limit=query.top_k,
        )
        for record in claim_records:
            results.append(
                RetrievalResult(
                    result_type="claim",
                    score=record.get("confidence", 0.5),
                    score_breakdown={"keyword_match": 1.0},
                    text_snippet=record.get("value", ""),
                    section_id=record.get("section_id"),
                    field_id=record.get("field_id"),
                    retrieval_profile="keyword_only",
                    provenance_path=[str(record.get("id", ""))],
                )
            )

        # Sort by score descending
        results.sort(key=lambda r: -r.score)
        return results[: query.top_k]

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        """Extract meaningful keywords from query text."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "shall", "can",
            "for", "and", "nor", "but", "or", "yet", "so", "at", "by",
            "in", "of", "on", "to", "up", "it", "its", "what", "which",
            "who", "whom", "this", "that", "these", "those", "with",
        }
        words = text.lower().split()
        return [w for w in words if len(w) > 2 and w not in stop_words]
