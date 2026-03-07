"""Evidence and source document repository."""

from __future__ import annotations

from typing import Any

from ....domain.evidence import Evidence, SourceDocument
from ....logging import get_logger
from ....utils.ids import generate_id
from ..client import SurrealClient

logger = get_logger(__name__)


class EvidenceRepository:
    """Handles evidence and source document persistence in SurrealDB.

    Evidence records are append-only — never overwrite, always timestamp.
    Graph edges from source->evidence and evidence->claim are maintained.
    """

    def __init__(self, client: SurrealClient) -> None:
        self._client = client

    async def create_source(self, source: SourceDocument) -> str:
        """Persist a source document and link it to the company.

        Args:
            source: The source document to persist.

        Returns:
            The created record ID.
        """
        data = source.model_dump(exclude={"id"})
        source_id = (
            source.id
            if source.id and source.id.startswith("source_document:")
            else generate_id("source_document")
        )
        await self._client.create(source_id, data)

        # Create graph edge: company -> source
        await self._client.execute(
            f"RELATE {source.company_id}->company_has_source->{source_id};",
        )

        logger.info(
            "source_created",
            source_id=source_id,
            company_id=source.company_id,
            provider=source.provider,
        )
        return source_id

    async def create_evidence(self, evidence: Evidence, source_id: str | None = None) -> str:
        """Persist an evidence record and create graph edges.

        Args:
            evidence: The evidence fragment to persist.
            source_id: Optional override for source document ID.

        Returns:
            The created evidence record ID.
        """
        data = evidence.model_dump(exclude={"id", "embedding"})
        evidence_id = (
            evidence.id
            if evidence.id and evidence.id.startswith("evidence:")
            else generate_id("evidence")
        )
        await self._client.create(evidence_id, data)

        # Create graph edge: source -> evidence
        src_id = source_id or evidence.source_document_id
        if src_id:
            await self._client.execute(
                f"RELATE {src_id}->source_has_evidence->{evidence_id};",
            )

        logger.info(
            "evidence_created",
            evidence_id=evidence_id,
            company_id=evidence.company_id,
            section_id=evidence.section_id,
        )
        return evidence_id

    async def find_by_company(
        self,
        company_id: str,
        section_id: str | None = None,
        field_id: str | None = None,
        limit: int = 50,
    ) -> list[Evidence]:
        """Find evidence records for a company with optional filters.

        Args:
            company_id: The company to query.
            section_id: Optional section filter.
            field_id: Optional field filter.
            limit: Max results.

        Returns:
            List of Evidence records.
        """
        conditions = ["company_id = $company_id"]
        params: dict[str, Any] = {"company_id": company_id, "limit": limit}

        if section_id:
            conditions.append("section_id = $section_id")
            params["section_id"] = section_id
        if field_id:
            conditions.append("field_id = $field_id")
            params["field_id"] = field_id

        where = " AND ".join(conditions)
        query = f"SELECT * FROM evidence WHERE {where} ORDER BY retrieved_at DESC LIMIT $limit;"

        result = await self._client.execute(query, params)
        if result and result[0].get("result"):
            return [Evidence(**r) for r in result[0]["result"]]
        return []

    async def find_sources_by_company(
        self, company_id: str, limit: int = 50
    ) -> list[SourceDocument]:
        """Find source documents for a company.

        Args:
            company_id: The company to query.
            limit: Max results.

        Returns:
            List of SourceDocument records.
        """
        result = await self._client.execute(
            "SELECT * FROM source_document WHERE company_id = $cid ORDER BY retrieved_at DESC LIMIT $limit;",
            {"cid": company_id, "limit": limit},
        )
        if result and result[0].get("result"):
            return [SourceDocument(**r) for r in result[0]["result"]]
        return []
