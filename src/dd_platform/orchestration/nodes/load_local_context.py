"""Node: Load existing company context from SurrealDB."""

from __future__ import annotations

from typing import Any

from ...logging import get_logger
from ...persistence.surreal.repositories.claim_repo import ClaimRepository
from ...persistence.surreal.repositories.company_repo import CompanyRepository
from ...persistence.surreal.repositories.evidence_repo import EvidenceRepository
from ...persistence.surreal.repositories.profile_repo import ProfileRepository
from ..state import BuildProfileState, WorkflowStage

logger = get_logger(__name__)


async def load_local_context(
    state: BuildProfileState,
    company_repo: CompanyRepository,
    profile_repo: ProfileRepository,
    evidence_repo: EvidenceRepository,
    claim_repo: ClaimRepository,
) -> dict:
    """Load existing company data from SurrealDB.

    Checks for existing company record, latest profile snapshot,
    evidence, and claims. This implements the "check DB first" principle.
    """
    logger.info("node_load_local_context", company_id=state.company_id)

    updates: dict[str, Any] = {"current_stage": WorkflowStage.DB_CHECKED}

    # Check company existence in DB at this point for observability.
    existing_company = await company_repo.find_by_id(state.company_id)
    updates["company_in_db_at_start"] = state.company_in_db_at_start or (existing_company is not None)

    # Load latest snapshot
    snapshot = await profile_repo.get_latest(state.company_id)
    if snapshot:
        updates["existing_snapshot_id"] = snapshot.id
        updates["existing_profile"] = snapshot.profile_json

    # Count existing evidence and claims
    evidence = await evidence_repo.find_by_company(state.company_id, limit=1)
    claims = await claim_repo.find_by_company(state.company_id, limit=1)

    # Get rough counts via queries
    updates["existing_evidence_count"] = len(
        await evidence_repo.find_by_company(state.company_id, limit=500)
    )
    updates["existing_claims_count"] = len(
        await claim_repo.find_by_company(state.company_id, limit=500)
    )

    logger.info(
        "local_context_loaded",
        company_id=state.company_id,
        company_in_db_at_start=updates["company_in_db_at_start"],
        has_snapshot=snapshot is not None,
        evidence_count=updates["existing_evidence_count"],
        claims_count=updates["existing_claims_count"],
    )

    return updates
