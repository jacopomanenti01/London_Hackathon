"""Company repository — persistence operations for company records and aliases."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ....domain.company import Company, CompanyRef, DomainAlias
from ....logging import get_logger
from ..client import SurrealClient

logger = get_logger(__name__)


class CompanyRepository:
    """Handles company and alias persistence in SurrealDB.

    All writes are idempotent where practical. Graph edges for aliases
    are maintained automatically.
    """

    def __init__(self, client: SurrealClient) -> None:
        self._client = client

    async def find_by_id(self, company_id: str) -> Company | None:
        """Find a company by its canonical ID.

        Args:
            company_id: e.g. 'company:www_example_com'

        Returns:
            Company record or None.
        """
        try:
            result = await self._client.select(company_id)
            if result:
                data = result if isinstance(result, dict) else result[0] if result else None
                if data:
                    return Company(**data)
        except Exception as e:
            logger.error("company_find_error", company_id=company_id, error=str(e))
        return None

    async def find_by_host(self, canonical_host: str) -> Company | None:
        """Find a company by canonical host.

        Args:
            canonical_host: e.g. 'www.example.com'

        Returns:
            Company record or None.
        """
        result = await self._client.execute(
            "SELECT * FROM company WHERE canonical_host = $host LIMIT 1;",
            {"host": canonical_host},
        )
        if result and result[0].get("result"):
            records = result[0]["result"]
            if records:
                return Company(**records[0])
        return None

    async def upsert(self, company_ref: CompanyRef) -> Company:
        """Create or update a company record from a CompanyRef.

        Args:
            company_ref: Normalized company identity.

        Returns:
            The created or updated Company record.
        """
        now = datetime.utcnow()
        data: dict[str, Any] = {
            "canonical_url": company_ref.canonical_url,
            "canonical_host": company_ref.canonical_host,
            "root_domain": company_ref.root_domain,
            "display_name": company_ref.display_name,
            "updated_at": now,
        }

        # Try to find existing
        existing = await self.find_by_id(company_ref.canonical_id)
        if existing:
            await self._client.update(company_ref.canonical_id, data)
            logger.info("company_updated", company_id=company_ref.canonical_id)
            return (await self.find_by_id(company_ref.canonical_id)) or existing
        else:
            data["created_at"] = now
            data["status"] = "active"
            await self._client.execute(
                f"CREATE {company_ref.canonical_id} CONTENT $data;",
                {"data": data},
            )
            logger.info("company_created", company_id=company_ref.canonical_id)
            return Company(
                id=company_ref.canonical_id,
                **data,  # type: ignore[arg-type]
            )

    async def add_alias(self, alias: DomainAlias) -> None:
        """Add a domain alias and create the graph edge.

        Args:
            alias: The domain alias to add.
        """
        alias_data = alias.model_dump(exclude={"id"})
        result = await self._client.create("domain_alias", alias_data)
        alias_id = result.get("id") if isinstance(result, dict) else None

        if alias_id:
            await self._client.execute(
                f"RELATE {alias.company_id}->company_has_alias->{alias_id};",
            )
            logger.info(
                "alias_added",
                company_id=alias.company_id,
                alias_host=alias.alias_host,
            )

    async def list_all(self, limit: int = 100) -> list[Company]:
        """List all company records.

        Args:
            limit: Maximum records to return.

        Returns:
            List of Company records.
        """
        result = await self._client.execute(
            "SELECT * FROM company ORDER BY updated_at DESC LIMIT $limit;",
            {"limit": limit},
        )
        if result and result[0].get("result"):
            return [Company(**r) for r in result[0]["result"]]
        return []
