"""Claim repository."""

from __future__ import annotations

from typing import Any

from ....domain.claim import Claim, ClaimStatus
from ....logging import get_logger
from ..client import SurrealClient

logger = get_logger(__name__)


class ClaimRepository:
    """Handles claim persistence in SurrealDB.

    Claims are versioned rather than deleted. Contradiction state is preserved.
    Graph edges to evidence, company, and profile sections are maintained.
    """

    def __init__(self, client: SurrealClient) -> None:
        self._client = client

    async def create(self, claim: Claim, evidence_ids: list[str] | None = None) -> str:
        """Persist a claim and create graph edges.

        Args:
            claim: The claim to persist.
            evidence_ids: Evidence records supporting this claim.

        Returns:
            The created claim record ID.
        """
        data = claim.model_dump(exclude={"id"})
        result = await self._client.create("claim", data)
        claim_id = result.get("id") if isinstance(result, dict) else str(result)

        # Link claim to company
        await self._client.execute(
            f"RELATE {claim_id}->claim_belongs_to_company->{claim.company_id};",
        )

        # Link evidence -> claim
        if evidence_ids:
            for eid in evidence_ids:
                await self._client.execute(
                    f"RELATE {eid}->evidence_supports_claim->{claim_id};",
                )

        logger.info(
            "claim_created",
            claim_id=claim_id,
            company_id=claim.company_id,
            section_id=claim.section_id,
            field_id=claim.field_id,
        )
        return claim_id

    async def find_by_company(
        self,
        company_id: str,
        section_id: str | None = None,
        field_id: str | None = None,
        status: ClaimStatus | None = None,
        limit: int = 100,
    ) -> list[Claim]:
        """Find claims for a company with optional filters.

        Args:
            company_id: The company to query.
            section_id: Optional section filter.
            field_id: Optional field filter.
            status: Optional status filter.
            limit: Max results.

        Returns:
            List of Claim records.
        """
        conditions = ["company_id = $company_id"]
        params: dict[str, Any] = {"company_id": company_id, "limit": limit}

        if section_id:
            conditions.append("section_id = $section_id")
            params["section_id"] = section_id
        if field_id:
            conditions.append("field_id = $field_id")
            params["field_id"] = field_id
        if status:
            conditions.append("status = $status")
            params["status"] = status.value

        where = " AND ".join(conditions)
        query = f"SELECT * FROM claim WHERE {where} ORDER BY last_verified_at DESC LIMIT $limit;"

        result = await self._client.execute(query, params)
        if result and result[0].get("result"):
            return [Claim(**r) for r in result[0]["result"]]
        return []

    async def find_contradictions(self, company_id: str) -> list[dict[str, Any]]:
        """Find contradicted claims for a company.

        Args:
            company_id: The company to check.

        Returns:
            List of contradiction pairs with claim details.
        """
        result = await self._client.execute(
            """
            SELECT * FROM claim WHERE company_id = $cid AND status = 'contradicted'
            ORDER BY last_verified_at DESC;
            """,
            {"cid": company_id},
        )
        if result and result[0].get("result"):
            return result[0]["result"]
        return []

    async def mark_contradicted(self, claim_id: str, contradicting_claim_id: str) -> None:
        """Mark two claims as contradicting each other.

        Args:
            claim_id: First claim.
            contradicting_claim_id: Second claim.
        """
        await self._client.execute(
            f"UPDATE {claim_id} SET status = 'contradicted';",
        )
        await self._client.execute(
            f"RELATE {claim_id}->claim_related_to_claim->{contradicting_claim_id} "
            f"SET relation_type = 'contradicts';",
        )
        logger.info(
            "claims_contradicted",
            claim_a=claim_id,
            claim_b=contradicting_claim_id,
        )
