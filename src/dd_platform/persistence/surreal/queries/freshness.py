"""Freshness evaluation queries."""

from __future__ import annotations

from typing import Any

from ..client import SurrealClient


class FreshnessQueries:
    """Queries to evaluate evidence and profile freshness by section and field."""

    def __init__(self, client: SurrealClient) -> None:
        self._client = client

    async def get_section_freshness(
        self, company_id: str
    ) -> list[dict[str, Any]]:
        """Get the latest evidence timestamp per section for a company.

        Args:
            company_id: The company to evaluate.

        Returns:
            List of dicts with section_id and latest_evidence_at.
        """
        result = await self._client.execute(
            """
            SELECT section_id, math::max(retrieved_at) AS latest_evidence_at, count() AS evidence_count
            FROM evidence
            WHERE company_id = $cid
            GROUP BY section_id;
            """,
            {"cid": company_id},
        )
        return result[0].get("result", []) if result else []

    async def get_field_freshness(
        self, company_id: str, section_id: str
    ) -> list[dict[str, Any]]:
        """Get the latest evidence timestamp per field within a section.

        Args:
            company_id: The company to evaluate.
            section_id: The section to check.

        Returns:
            List of dicts with field_id and latest_evidence_at.
        """
        result = await self._client.execute(
            """
            SELECT field_id, math::max(retrieved_at) AS latest_evidence_at, count() AS evidence_count
            FROM evidence
            WHERE company_id = $cid AND section_id = $sid
            GROUP BY field_id;
            """,
            {"cid": company_id, "sid": section_id},
        )
        return result[0].get("result", []) if result else []

    async def get_latest_snapshot_time(self, company_id: str) -> str | None:
        """Get the creation time of the latest profile snapshot.

        Args:
            company_id: The company to check.

        Returns:
            ISO datetime string or None.
        """
        result = await self._client.execute(
            """
            SELECT created_at FROM profile_snapshot
            WHERE company_id = $cid AND is_latest = true
            LIMIT 1;
            """,
            {"cid": company_id},
        )
        if result and result[0].get("result"):
            records = result[0]["result"]
            if records:
                return records[0].get("created_at")
        return None
