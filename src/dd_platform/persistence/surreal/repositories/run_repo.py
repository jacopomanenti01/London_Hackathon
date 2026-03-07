"""Agent run repository."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ....domain.run import AgentRun, RunStatus
from ....logging import get_logger
from ....utils.ids import generate_id
from ..client import SurrealClient

logger = get_logger(__name__)


class RunRepository:
    """Handles agent run persistence in SurrealDB."""

    def __init__(self, client: SurrealClient) -> None:
        self._client = client

    async def create(self, run: AgentRun) -> str:
        """Persist a new agent run.

        Args:
            run: The agent run to create.

        Returns:
            Created run record ID.
        """
        data = run.model_dump(exclude={"id"})
        run_id = run.id if run.id and run.id.startswith("agent_run:") else generate_id("agent_run")
        await self._client.create(run_id, data)

        # Link run to company
        await self._client.execute(
            f"RELATE {run_id}->run_for_company->{run.company_id};",
        )

        logger.info(
            "run_created",
            run_id=run_id,
            company_id=run.company_id,
            run_type=run.run_type,
        )
        return run_id

    async def update_status(
        self,
        run_id: str,
        status: RunStatus,
        output_summary: dict[str, Any] | None = None,
        error_summary: str | None = None,
        metrics: dict[str, Any] | None = None,
    ) -> None:
        """Update run status and optional summary fields.

        Args:
            run_id: The run to update.
            status: New status.
            output_summary: Optional output summary.
            error_summary: Optional error description.
            metrics: Optional run metrics.
        """
        updates: dict[str, Any] = {"status": status.value}
        if status in (RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.PARTIAL):
            updates["ended_at"] = datetime.utcnow()
        if output_summary:
            updates["output_summary"] = output_summary
        if error_summary:
            updates["error_summary"] = error_summary
        if metrics:
            updates["metrics"] = metrics

        await self._client.update(run_id, updates)
        logger.info("run_status_updated", run_id=run_id, status=status.value)

    async def get_by_id(self, run_id: str) -> AgentRun | None:
        """Get a run by ID."""
        try:
            result = await self._client.select(run_id)
            if result:
                data = result if isinstance(result, dict) else result[0] if result else None
                if data:
                    return AgentRun(**data)
        except Exception:
            pass
        return None

    async def find_by_company(
        self, company_id: str, limit: int = 20
    ) -> list[AgentRun]:
        """Find runs for a company, newest first."""
        result = await self._client.execute(
            "SELECT * FROM agent_run WHERE company_id = $cid ORDER BY started_at DESC LIMIT $limit;",
            {"cid": company_id, "limit": limit},
        )
        if result and result[0].get("result"):
            return [AgentRun(**r) for r in result[0]["result"]]
        return []
