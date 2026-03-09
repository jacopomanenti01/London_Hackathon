"""Node: Assess evidence freshness by schema section and field."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ...domain.schema import ProfileSchema
from ...logging import get_logger
from ...persistence.surreal.queries.freshness import FreshnessQueries
from ...utils.time import is_stale
from ..state import BuildProfileState, FreshnessAssessment, WorkflowStage

logger = get_logger(__name__)


async def assess_freshness(
    state: BuildProfileState,
    freshness_queries: FreshnessQueries,
    schema: ProfileSchema,
) -> dict:
    """Evaluate freshness per section based on schema TTLs.

    Compares existing evidence timestamps against section-level TTLs
    to determine which sections need refresh.
    """
    logger.info("node_assess_freshness", company_id=state.company_id)

    if not state.company_in_db_at_start:
        assessments: list[FreshnessAssessment] = []
        sections_needing_refresh: list[str] = []
        for section in schema.sections:
            if state.target_sections and section.id not in state.target_sections:
                continue
            assessments.append(
                FreshnessAssessment(
                    section_id=section.id,
                    status="missing",
                    last_evidence_at=None,
                    evidence_count=0,
                    ttl_days=section.freshness_days,
                    needs_refresh=True,
                )
            )
            sections_needing_refresh.append(section.id)

        logger.info(
            "freshness_assessed_new_company",
            company_id=state.company_id,
            total_sections=len(assessments),
            needing_refresh=len(sections_needing_refresh),
        )

        return {
            "freshness_assessments": assessments,
            "sections_needing_refresh": sections_needing_refresh,
            "skip_external_research": False,
            "current_stage": WorkflowStage.FRESHNESS_EVALUATED,
        }

    section_freshness = await freshness_queries.get_section_freshness(state.company_id)
    freshness_map: dict[str, dict[str, Any]] = {
        f["section_id"]: f for f in section_freshness if f.get("section_id")
    }

    assessments: list[FreshnessAssessment] = []
    sections_needing_refresh: list[str] = []

    for section in schema.sections:
        # Skip sections not in target scope (if specified)
        if state.target_sections and section.id not in state.target_sections:
            continue

        fresh_data = freshness_map.get(section.id)
        evidence_count = fresh_data.get("evidence_count", 0) if fresh_data else 0
        latest_at_raw = fresh_data.get("latest_evidence_at") if fresh_data else None

        # Parse timestamp
        latest_at: datetime | None = None
        if latest_at_raw:
            if isinstance(latest_at_raw, str):
                try:
                    latest_at = datetime.fromisoformat(latest_at_raw)
                except ValueError:
                    latest_at = None
            elif isinstance(latest_at_raw, datetime):
                latest_at = latest_at_raw

        needs_refresh = state.force_refresh or evidence_count == 0 or is_stale(latest_at, section.freshness_days)

        if evidence_count == 0:
            status = "missing"
        elif needs_refresh:
            status = "stale"
        else:
            status = "fresh"

        assessment = FreshnessAssessment(
            section_id=section.id,
            status=status,
            last_evidence_at=latest_at,
            evidence_count=evidence_count,
            ttl_days=section.freshness_days,
            needs_refresh=needs_refresh,
        )
        assessments.append(assessment)

        if needs_refresh:
            sections_needing_refresh.append(section.id)

    skip_external = len(sections_needing_refresh) == 0

    logger.info(
        "freshness_assessed",
        company_id=state.company_id,
        total_sections=len(assessments),
        needing_refresh=len(sections_needing_refresh),
        skip_external=skip_external,
    )

    return {
        "freshness_assessments": assessments,
        "sections_needing_refresh": sections_needing_refresh,
        "skip_external_research": skip_external,
        "current_stage": WorkflowStage.FRESHNESS_EVALUATED,
    }
