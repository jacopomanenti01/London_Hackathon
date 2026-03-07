"""Graph neighborhood expansion queries for GraphRAG retrieval."""

from __future__ import annotations

from typing import Any

from ....logging import get_logger
from ..client import SurrealClient

logger = get_logger(__name__)


class GraphNeighborQueries:
    """Graph traversal queries for neighborhood expansion.

    Supports hop-limited expansion from company nodes through
    claims, evidence, and profile sections.
    """

    def __init__(self, client: SurrealClient) -> None:
        self._client = client

    async def get_company_claims_and_evidence(
        self, company_id: str, limit: int = 50
    ) -> dict[str, Any]:
        """Get all claims and their supporting evidence for a company.

        1-hop expansion: company -> claims -> evidence

        Args:
            company_id: The company node to expand from.
            limit: Max claims to return.

        Returns:
            Dict with 'claims' and 'evidence' lists.
        """
        result = await self._client.execute(
            """
            SELECT *,
                <-evidence_supports_claim<-evidence AS supporting_evidence
            FROM claim
            WHERE company_id = $cid
            ORDER BY last_verified_at DESC
            LIMIT $limit;
            """,
            {"cid": company_id, "limit": limit},
        )

        claims = result[0].get("result", []) if result else []
        return {"claims": claims, "total": len(claims)}

    async def get_evidence_neighborhood(
        self, evidence_id: str, hops: int = 1
    ) -> dict[str, Any]:
        """Expand graph neighborhood around an evidence record.

        Args:
            evidence_id: The evidence node to expand from.
            hops: Number of hops (1 or 2 supported).

        Returns:
            Dict with neighboring claims and related evidence.
        """
        if hops >= 1:
            # 1-hop: evidence -> claims it supports
            result = await self._client.execute(
                f"""
                SELECT *,
                    ->evidence_supports_claim->claim AS supported_claims
                FROM {evidence_id};
                """,
            )
        else:
            result = await self._client.execute(f"SELECT * FROM {evidence_id};")

        return {"evidence_id": evidence_id, "neighbors": result[0].get("result", []) if result else []}

    async def get_claim_neighborhood(
        self, claim_id: str, include_contradictions: bool = True
    ) -> dict[str, Any]:
        """Expand graph neighborhood around a claim.

        Args:
            claim_id: The claim node to expand from.
            include_contradictions: Whether to include contradiction links.

        Returns:
            Dict with supporting evidence and related claims.
        """
        query = f"""
            SELECT *,
                <-evidence_supports_claim<-evidence AS supporting_evidence,
                ->claim_related_to_claim->claim AS related_claims
            FROM {claim_id};
        """
        result = await self._client.execute(query)
        return {
            "claim_id": claim_id,
            "neighborhood": result[0].get("result", []) if result else [],
        }

    async def get_section_evidence_graph(
        self, company_id: str, section_id: str
    ) -> dict[str, Any]:
        """Get all evidence and claims linked to a specific profile section.

        Args:
            company_id: The company.
            section_id: The schema section ID.

        Returns:
            Dict with claims and evidence for the section.
        """
        result = await self._client.execute(
            """
            SELECT * FROM claim
            WHERE company_id = $cid AND section_id = $sid AND status = 'active'
            ORDER BY confidence DESC;
            """,
            {"cid": company_id, "sid": section_id},
        )

        claims = result[0].get("result", []) if result else []

        evidence_result = await self._client.execute(
            """
            SELECT * FROM evidence
            WHERE company_id = $cid AND section_id = $sid
            ORDER BY confidence DESC;
            """,
            {"cid": company_id, "sid": section_id},
        )

        evidence = evidence_result[0].get("result", []) if evidence_result else []

        return {
            "section_id": section_id,
            "claims": claims,
            "evidence": evidence,
        }
