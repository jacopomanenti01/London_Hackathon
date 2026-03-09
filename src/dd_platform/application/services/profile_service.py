"""Profile service — orchestrates full profile build workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ...domain.run import AgentRun, RunType
from ...logging import get_logger
from ...orchestration.graph import create_build_profile_graph
from ...orchestration.state import BuildProfileState
from ...utils.ids import generate_id, generate_run_id

logger = get_logger(__name__)


class ProfileService:
    """Coordinates the profile build use case.

    Wires together the LangGraph workflow with all required dependencies,
    creates run records, and manages the full lifecycle.
    """

    def __init__(self, dependencies: dict[str, Any]) -> None:
        self._deps = dependencies

    async def build_profile(
        self,
        company_url: str,
        schema_id: str | None = None,
        force_refresh: bool = False,
        retrieval_profile: str = "graph_hybrid_expanded",
        target_sections: list[str] | None = None,
        experiment_tags: list[str] | None = None,
        publish_snapshot: bool = True,
    ) -> dict[str, Any]:
        """Build a due diligence profile for a company.

        The system:
        1. Normalizes the URL into canonical company ID
        2. Checks SurrealDB for existing data
        3. Evaluates freshness per schema section
        4. Fetches only missing/stale evidence
        5. Extracts claims using LLM
        6. Synthesizes profile under active schema
        7. Persists everything to SurrealDB

        Args:
            company_url: The company's main URL.
            schema_id: Schema to use (defaults to active).
            force_refresh: Force full refresh ignoring TTLs.
            retrieval_profile: Retrieval strategy to use.
            target_sections: Limit to specific sections.
            experiment_tags: Tags for experiment tracking.
            publish_snapshot: Whether to publish a profile snapshot.

        Returns:
            Dict with profile data, run metadata, and coverage info.
        """
        run_id = generate_run_id()
        request_id = generate_id("req")

        # Load schema
        schema_service = self._deps["schema_service"]
        schema = schema_service.get_active_schema() if not schema_id else schema_service.get_schema(schema_id)

        # Check company existence first; create if missing.
        run_repo = self._deps["run_repo"]
        company_repo = self._deps["company_repo"]
        from ...utils.url_normalization import resolve_company_identity
        company_ref = resolve_company_identity(company_url)
        existing_company = await company_repo.find_by_id(company_ref.canonical_id)
        company_in_db_at_start = existing_company is not None
        if not company_in_db_at_start:
            await company_repo.upsert(company_ref)

        run = AgentRun(
            company_id=company_ref.canonical_id,
            run_type=RunType.BUILD,
            retrieval_profile=retrieval_profile,
            experiment_tags=experiment_tags or [],
            active_schema_version=schema.version,
            input_payload={
                "company_url": company_url,
                "force_refresh": force_refresh,
                "target_sections": target_sections,
            },
        )
        db_run_id = await run_repo.create(run)

        # Build initial state
        initial_state = BuildProfileState(
            request_id=request_id,
            run_id=db_run_id,
            company_url=company_url,
            force_refresh=force_refresh,
            company_in_db_at_start=company_in_db_at_start,
            target_sections=target_sections or [],
            retrieval_profile=retrieval_profile,
            experiment_tags=experiment_tags or [],
            publish_snapshot=publish_snapshot,
            schema_id=schema.schema_id,
            schema_version=schema.version,
            schema_sections=schema.all_section_ids,
        )

        # Create and run the workflow
        graph = create_build_profile_graph({**self._deps, "schema": schema})

        logger.info(
            "profile_build_started",
            company_url=company_url,
            run_id=db_run_id,
            retrieval_profile=retrieval_profile,
        )

        try:
            final_state = await graph.ainvoke(initial_state)

            # Extract results
            if isinstance(final_state, dict):
                state_data = final_state
            else:
                state_data = final_state.dict() if hasattr(final_state, 'dict') else {}

            return {
                "company_id": state_data.get("company_id", company_ref.canonical_id),
                "run_id": db_run_id,
                "profile": state_data.get("profile_draft", {}),
                "snapshot_id": state_data.get("profile_snapshot_id"),
                "schema_id": schema.schema_id,
                "schema_version": schema.version,
                "retrieval_profile": retrieval_profile,
                "freshness": [
                    a.model_dump() if hasattr(a, 'model_dump') else a
                    for a in state_data.get("freshness_assessments", [])
                ],
                "metrics": state_data.get("metrics", {}),
                "status": state_data.get("current_stage", "completed"),
                "errors": state_data.get("errors", []),
            }

        except Exception as e:
            logger.error("profile_build_failed", error=str(e), run_id=db_run_id)
            from ...domain.run import RunStatus
            await run_repo.update_status(db_run_id, RunStatus.FAILED, error_summary=str(e))
            raise
