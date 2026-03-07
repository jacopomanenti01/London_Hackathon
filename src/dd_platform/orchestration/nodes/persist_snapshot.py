"""Node: Persist profile snapshot and run metadata to SurrealDB."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ...domain.evidence import Evidence, SourceDocument, SourceProvider
from ...domain.profile import ProfileSection, ProfileSnapshot
from ...logging import get_logger
from ...persistence.surreal.repositories.claim_repo import ClaimRepository
from ...persistence.surreal.repositories.evidence_repo import EvidenceRepository
from ...persistence.surreal.repositories.profile_repo import ProfileRepository
from ...persistence.surreal.repositories.run_repo import RunRepository
from ...domain.claim import Claim
from ...domain.run import RunStatus
from ..state import BuildProfileState, WorkflowStage

logger = get_logger(__name__)


async def persist_snapshot(
    state: BuildProfileState,
    profile_repo: ProfileRepository,
    evidence_repo: EvidenceRepository,
    claim_repo: ClaimRepository,
    run_repo: RunRepository,
) -> dict:
    """Persist evidence, claims, and profile snapshot to SurrealDB.

    Creates source documents, evidence records, claims with graph edges,
    and the immutable profile snapshot.
    """
    logger.info("node_persist_snapshot", company_id=state.company_id)

    # 1. Persist new sources and evidence
    persisted_sources = 0
    persisted_evidence = 0
    persisted_claims = 0
    persist_errors = 0
    for source_data in state.new_sources:
        try:
            source = SourceDocument(
                company_id=source_data["company_id"],
                url=source_data["url"],
                title=source_data.get("title"),
                provider=SourceProvider(source_data.get("provider", "internal")),
                content_text=source_data.get("content_text"),
                content_hash=source_data.get("content_hash"),
            )
            source_id = await evidence_repo.create_source(source)
            persisted_sources += 1

            # Persist associated evidence
            for ev_data in state.new_evidence:
                if ev_data.get("source_url") == source_data["url"]:
                    evidence = Evidence(
                        company_id=ev_data["company_id"],
                        source_document_id=source_id,
                        section_id=ev_data.get("section_id"),
                        excerpt=ev_data.get("excerpt", ""),
                        confidence=ev_data.get("confidence", 0.5),
                    )
                    await evidence_repo.create_evidence(evidence, source_id)
                    persisted_evidence += 1

        except Exception as e:
            persist_errors += 1
            logger.warning("persist_source_failed", error=str(e), url=source_data.get("url"))

    # 2. Persist extracted claims
    for claim_data in state.extracted_claims:
        try:
            claim = Claim(
                company_id=state.company_id,
                section_id=claim_data.get("section_id", "unknown"),
                field_id=claim_data.get("field_id", "unknown"),
                value=str(claim_data.get("value", "")),
                value_type=claim_data.get("value_type", "string"),
                confidence=float(claim_data.get("confidence", 0.5)),
                schema_version=state.schema_version,
            )
            await claim_repo.create(claim)
            persisted_claims += 1
        except Exception as e:
            persist_errors += 1
            logger.warning("persist_claim_failed", error=str(e))

    # 3. Create profile snapshot
    snapshot_id = None
    if state.publish_snapshot and state.profile_draft:
        sections = []
        profile_sections = state.profile_draft.get("sections", {})
        for section_id, section_data in profile_sections.items():
            sections.append(
                ProfileSection(
                    section_id=section_id,
                    section_json=section_data if isinstance(section_data, dict) else {},
                    freshness_status="fresh",
                )
            )

        snapshot = ProfileSnapshot(
            company_id=state.company_id,
            schema_id=state.schema_id,
            schema_version=state.schema_version,
            profile_json=state.profile_draft,
            sections=sections,
            retrieval_profile=state.retrieval_profile,
            coverage_summary=state.profile_draft.get("profile_meta", {}),
        )

        snapshot_id = await profile_repo.create_snapshot(snapshot, state.run_id)

    # 4. Update run status
    if state.run_id:
        await run_repo.update_status(
            state.run_id,
            RunStatus.COMPLETED,
            output_summary={
                "snapshot_id": snapshot_id,
                "sources_persisted": persisted_sources,
                "evidence_persisted": persisted_evidence,
                "claims_persisted": persisted_claims,
                "persist_errors": persist_errors,
            },
            metrics=state.metrics,
        )

    logger.info(
        "snapshot_persisted",
        company_id=state.company_id,
        snapshot_id=snapshot_id,
        sources=persisted_sources,
        evidence=persisted_evidence,
        claims=persisted_claims,
        persist_errors=persist_errors,
    )

    metrics = dict(state.metrics)
    metrics["sources_persisted"] = persisted_sources
    metrics["evidence_persisted"] = persisted_evidence
    metrics["claims_persisted"] = persisted_claims
    metrics["persist_errors"] = persist_errors

    return {
        "profile_snapshot_id": snapshot_id,
        "metrics": metrics,
        "current_stage": WorkflowStage.PROFILE_PERSISTED,
        "completed_at": datetime.utcnow(),
    }
