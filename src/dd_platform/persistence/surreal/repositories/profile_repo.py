"""Profile snapshot repository."""

from __future__ import annotations

from typing import Any

from ....domain.profile import ProfileSnapshot
from ....logging import get_logger
from ....utils.ids import generate_id
from ..client import SurrealClient

logger = get_logger(__name__)


class ProfileRepository:
    """Handles profile snapshot persistence in SurrealDB.

    Snapshots are immutable. The is_latest flag manages the materialized
    current profile view. Old snapshots are retained for reproducibility.
    """

    def __init__(self, client: SurrealClient) -> None:
        self._client = client

    async def create_snapshot(
        self, snapshot: ProfileSnapshot, run_id: str | None = None
    ) -> str:
        """Persist an immutable profile snapshot.

        Marks previous latest snapshot as non-latest and creates graph edges.

        Args:
            snapshot: The profile snapshot to persist.
            run_id: The run that created this snapshot.

        Returns:
            Created snapshot record ID.
        """
        # Mark previous snapshots as non-latest
        await self._client.execute(
            "UPDATE profile_snapshot SET is_latest = false "
            "WHERE company_id = $cid AND is_latest = true;",
            {"cid": snapshot.company_id},
        )

        data = snapshot.model_dump(exclude={"id", "sections"})
        data["created_by_run_id"] = run_id
        data["is_latest"] = True

        snapshot_id = (
            snapshot.id
            if snapshot.id and snapshot.id.startswith("profile_snapshot:")
            else generate_id("profile_snapshot")
        )
        await self._client.create(snapshot_id, data)

        # Create graph edge: company -> snapshot
        await self._client.execute(
            f"RELATE {snapshot.company_id}->company_has_snapshot->{snapshot_id};",
        )

        # Update company with latest snapshot reference
        await self._client.execute(
            f"UPDATE {snapshot.company_id} SET latest_profile_snapshot_id = $sid, updated_at = time::now();",
            {"sid": snapshot_id},
        )

        # Persist sections
        for section in snapshot.sections:
            section_data = section.model_dump(exclude={"id"})
            section_data["profile_snapshot_id"] = snapshot_id
            section_record_id = (
                section.id
                if section.id and section.id.startswith("profile_section:")
                else generate_id("profile_section")
            )
            await self._client.create(section_record_id, section_data)
            await self._client.execute(
                f"RELATE {snapshot_id}->snapshot_has_section->{section_record_id};",
            )

        logger.info(
            "snapshot_created",
            snapshot_id=snapshot_id,
            company_id=snapshot.company_id,
            schema_id=snapshot.schema_id,
        )
        return snapshot_id

    async def get_latest(self, company_id: str) -> ProfileSnapshot | None:
        """Get the latest profile snapshot for a company.

        Args:
            company_id: The company to query.

        Returns:
            Latest ProfileSnapshot or None.
        """
        result = await self._client.execute(
            "SELECT * FROM profile_snapshot WHERE company_id = $cid AND is_latest = true "
            "ORDER BY created_at DESC LIMIT 1;",
            {"cid": company_id},
        )
        if result and result[0].get("result"):
            records = result[0]["result"]
            if records:
                return ProfileSnapshot(**records[0])

        # Fallback for legacy/inconsistent rows where is_latest may be absent/incorrect.
        fallback = await self._client.execute(
            "SELECT * FROM profile_snapshot WHERE company_id = $cid "
            "ORDER BY created_at DESC LIMIT 1;",
            {"cid": company_id},
        )
        if fallback and fallback[0].get("result"):
            records = fallback[0]["result"]
            if records:
                return ProfileSnapshot(**records[0])
        return None

    async def get_by_id(self, snapshot_id: str) -> ProfileSnapshot | None:
        """Get a specific profile snapshot by ID.

        Args:
            snapshot_id: The snapshot record ID.

        Returns:
            ProfileSnapshot or None.
        """
        try:
            result = await self._client.select(snapshot_id)
            if result:
                data = result if isinstance(result, dict) else result[0] if result else None
                if data:
                    return ProfileSnapshot(**data)
        except Exception as e:
            logger.error("snapshot_fetch_error", snapshot_id=snapshot_id, error=str(e))
        return None

    async def list_snapshots(
        self, company_id: str, limit: int = 20
    ) -> list[ProfileSnapshot]:
        """List profile snapshots for a company, newest first.

        Args:
            company_id: The company to query.
            limit: Max results.

        Returns:
            List of ProfileSnapshot records.
        """
        result = await self._client.execute(
            "SELECT * FROM profile_snapshot WHERE company_id = $cid ORDER BY created_at DESC LIMIT $limit;",
            {"cid": company_id, "limit": limit},
        )
        if result and result[0].get("result"):
            return [ProfileSnapshot(**r) for r in result[0]["result"]]
        return []
