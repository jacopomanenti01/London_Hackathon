"""Node: Finalize the run — mark completed and emit metrics."""

from __future__ import annotations

from datetime import datetime

from ...logging import get_logger
from ..state import BuildProfileState, WorkflowStage

logger = get_logger(__name__)


async def finalize_run(state: BuildProfileState) -> dict:
    """Finalize the build workflow run.

    Calculates final metrics and marks the run as complete.
    """
    elapsed = (datetime.utcnow() - state.started_at).total_seconds()

    metrics = {
        **state.metrics,
        "total_duration_seconds": elapsed,
        "new_sources_count": len(state.new_sources),
        "new_evidence_count": len(state.new_evidence),
        "extracted_claims_count": len(state.extracted_claims),
        "sections_refreshed": len(state.sections_needing_refresh),
        "skipped_external_research": state.skip_external_research,
    }

    logger.info(
        "run_finalized",
        company_id=state.company_id,
        run_id=state.run_id,
        duration_seconds=round(elapsed, 1),
        snapshot_id=state.profile_snapshot_id,
    )

    return {
        "metrics": metrics,
        "current_stage": WorkflowStage.COMPLETED,
        "completed_at": datetime.utcnow(),
    }
