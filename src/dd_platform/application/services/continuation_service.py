"""Continuation research service — directed follow-up research."""

from __future__ import annotations

from typing import Any

from ...domain.run import AgentRun, RunType
from ...logging import get_logger
from ...utils.ids import generate_run_id

logger = get_logger(__name__)


class ContinuationService:
    """Handles directed continuation research into specific areas.

    Users can instruct agents to continue research into selected
    sections, fields, or risk topics. The service maps instructions
    to schema scope, reuses existing evidence, and produces deltas.
    """

    def __init__(self, dependencies: dict[str, Any]) -> None:
        self._deps = dependencies

    async def continue_research(
        self,
        company_id: str,
        instruction: str,
        target_sections: list[str] | None = None,
        retrieval_profile: str = "graph_hybrid_expanded",
        publish_snapshot: bool = True,
    ) -> dict[str, Any]:
        """Execute targeted continuation research.

        Args:
            company_id: The company to research further.
            instruction: Natural language research directive.
            target_sections: Specific sections to target.
            retrieval_profile: Retrieval strategy.
            publish_snapshot: Whether to publish a new snapshot.

        Returns:
            Delta summary with new evidence, claims, and optional snapshot.
        """
        run_id = generate_run_id()

        logger.info(
            "continuation_started",
            company_id=company_id,
            instruction=instruction[:100],
        )

        # Create run record
        run_repo = self._deps["run_repo"]
        run = AgentRun(
            company_id=company_id,
            run_type=RunType.CONTINUATION,
            retrieval_profile=retrieval_profile,
            input_payload={
                "instruction": instruction,
                "target_sections": target_sections,
            },
        )
        db_run_id = await run_repo.create(run)

        # Use profile service to run a targeted build
        profile_service = self._deps.get("profile_service")
        if profile_service:
            # Extract the company URL from the ID
            host = company_id.replace("company:", "").replace("_", ".")
            result = await profile_service.build_profile(
                company_url=f"https://{host}",
                force_refresh=True,
                retrieval_profile=retrieval_profile,
                target_sections=target_sections,
                publish_snapshot=publish_snapshot,
            )

            return {
                "company_id": company_id,
                "run_id": db_run_id,
                "instruction": instruction,
                "delta": result.get("profile", {}),
                "new_evidence_count": result.get("metrics", {}).get("new_evidence_count", 0),
                "new_claims_count": result.get("metrics", {}).get("extracted_claims_count", 0),
                "snapshot_id": result.get("snapshot_id"),
                "retrieval_profile": retrieval_profile,
            }

        return {
            "company_id": company_id,
            "run_id": db_run_id,
            "instruction": instruction,
            "status": "not_implemented_yet",
        }
