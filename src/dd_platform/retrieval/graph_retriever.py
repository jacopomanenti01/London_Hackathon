"""Graph-based retrieval using SurrealDB graph traversal.

This retriever uses graph structure as a first-class retrieval signal,
supporting neighborhood expansion, section-aware filtering, and
contradiction-aware traversal.
"""

from __future__ import annotations

from ..domain.retrieval import RetrievalResult
from ..logging import get_logger
from ..persistence.surreal.queries.graph_neighbors import GraphNeighborQueries
from .interfaces import Retriever, RetrievalQuery

logger = get_logger(__name__)


class GraphRetriever(Retriever):
    """Graph-based evidence and claim retrieval.

    Traverses the knowledge graph from company nodes through claims,
    evidence, and profile sections. Supports configurable hop depth,
    section-aware filtering, and contradiction-aware ranking.
    """

    name = "graph"

    def __init__(self, graph_queries: GraphNeighborQueries) -> None:
        self._queries = graph_queries

    async def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        """Retrieve evidence and claims via graph traversal.

        Args:
            query: Retrieval query with graph expansion parameters.

        Returns:
            Graph-ranked retrieval results.
        """
        results: list[RetrievalResult] = []

        # Section-specific retrieval
        if query.section_ids:
            for section_id in query.section_ids:
                section_graph = await self._queries.get_section_evidence_graph(
                    company_id=query.company_id,
                    section_id=section_id,
                )
                results.extend(self._process_section_graph(section_graph, section_id))
        else:
            # Full company graph traversal
            company_graph = await self._queries.get_company_claims_and_evidence(
                company_id=query.company_id,
                limit=query.top_k * 2,
            )
            results.extend(self._process_company_graph(company_graph))

        # Sort by score and limit
        results.sort(key=lambda r: -r.score)
        return results[: query.top_k]

    def _process_section_graph(
        self, graph_data: dict, section_id: str
    ) -> list[RetrievalResult]:
        """Convert section graph data to retrieval results."""
        results: list[RetrievalResult] = []

        for claim in graph_data.get("claims", []):
            score = float(claim.get("confidence", 0.5))
            results.append(
                RetrievalResult(
                    result_type="claim",
                    score=score * 1.1,  # Boost for graph proximity
                    score_breakdown={
                        "base_confidence": score,
                        "graph_proximity_boost": 0.1,
                    },
                    text_snippet=claim.get("value", ""),
                    section_id=section_id,
                    field_id=claim.get("field_id"),
                    contradiction_flag=claim.get("status") == "contradicted",
                    retrieval_profile="graph_only",
                    provenance_path=[str(claim.get("id", "")), f"section:{section_id}"],
                )
            )

        for evidence in graph_data.get("evidence", []):
            score = float(evidence.get("confidence", 0.5))
            results.append(
                RetrievalResult(
                    result_type="evidence",
                    score=score,
                    score_breakdown={"base_confidence": score},
                    text_snippet=evidence.get("excerpt", ""),
                    section_id=section_id,
                    field_id=evidence.get("field_id"),
                    retrieval_profile="graph_only",
                    provenance_path=[
                        str(evidence.get("id", "")),
                        str(evidence.get("source_document_id", "")),
                    ],
                )
            )

        return results

    def _process_company_graph(self, graph_data: dict) -> list[RetrievalResult]:
        """Convert full company graph data to retrieval results."""
        results: list[RetrievalResult] = []

        for claim in graph_data.get("claims", []):
            score = float(claim.get("confidence", 0.5))
            results.append(
                RetrievalResult(
                    result_type="claim",
                    score=score,
                    score_breakdown={"base_confidence": score},
                    text_snippet=claim.get("value", ""),
                    section_id=claim.get("section_id"),
                    field_id=claim.get("field_id"),
                    contradiction_flag=claim.get("status") == "contradicted",
                    retrieval_profile="graph_only",
                    provenance_path=[str(claim.get("id", ""))],
                )
            )

        return results
