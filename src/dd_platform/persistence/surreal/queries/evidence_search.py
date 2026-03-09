"""Evidence search and filtering queries."""

from __future__ import annotations

from typing import Any

from ..client import SurrealClient


class EvidenceSearchQueries:
    """Specialized evidence search queries for retrieval layer."""

    def __init__(self, client: SurrealClient) -> None:
        self._client = client

    async def search_by_keyword(
        self,
        company_id: str,
        keywords: list[str],
        section_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search evidence by keyword matching.

        Args:
            company_id: The company scope.
            keywords: Keywords to match in excerpts.
            section_id: Optional section filter.
            limit: Max results.

        Returns:
            List of matching evidence records.
        """
        conditions = ["company_id = $cid"]
        params: dict[str, Any] = {"cid": company_id, "limit": limit}

        # Build keyword conditions using string::contains
        keyword_conditions = []
        for i, kw in enumerate(keywords):
            param_name = f"kw{i}"
            keyword_conditions.append(f"string::lowercase(excerpt) CONTAINS string::lowercase(${param_name})")
            params[param_name] = kw

        if keyword_conditions:
            conditions.append(f"({' OR '.join(keyword_conditions)})")

        if section_id:
            conditions.append("section_id = $sid")
            params["sid"] = section_id

        where = " AND ".join(conditions)
        query = f"SELECT * FROM evidence WHERE {where} ORDER BY confidence DESC LIMIT $limit;"

        result = await self._client.execute(query, params)
        return result[0].get("result", []) if result else []

    async def search_claims_by_keyword(
        self,
        company_id: str,
        keywords: list[str],
        section_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Search claims by keyword matching.

        Args:
            company_id: The company scope.
            keywords: Keywords to match in claim values.
            section_id: Optional section filter.
            limit: Max results.

        Returns:
            List of matching claim records.
        """
        conditions = ["company_id = $cid", "status = 'active'"]
        params: dict[str, Any] = {"cid": company_id, "limit": limit}

        keyword_conditions = []
        for i, kw in enumerate(keywords):
            param_name = f"kw{i}"
            keyword_conditions.append(f"string::lowercase(value) CONTAINS string::lowercase(${param_name})")
            params[param_name] = kw

        if keyword_conditions:
            conditions.append(f"({' OR '.join(keyword_conditions)})")

        if section_id:
            conditions.append("section_id = $sid")
            params["sid"] = section_id

        where = " AND ".join(conditions)
        query = f"SELECT * FROM claim WHERE {where} ORDER BY confidence DESC LIMIT $limit;"

        result = await self._client.execute(query, params)
        return result[0].get("result", []) if result else []
