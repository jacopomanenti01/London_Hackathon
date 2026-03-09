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
from ..state import BuildProfileState, FreshnessAssessment, WorkflowStage

logger = get_logger(__name__)


def _url_key(url: str | None) -> str:
    """Normalize URL for stable matching between sources and evidence."""
    return (url or "").strip().lower().rstrip("/")


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

    # 1. Persist sources
    persisted_sources = 0
    persisted_evidence = 0
    persisted_claims = 0
    persist_errors = 0
    existing_sources = await evidence_repo.find_sources_by_company(state.company_id, limit=5000)
    source_id_by_url = {_url_key(s.url): s.id for s in existing_sources if s.id and s.url}

    for source_data in state.new_sources:
        try:
            normalized_source_url = _url_key(source_data.get("url"))
            if normalized_source_url in source_id_by_url:
                continue

            source = SourceDocument(
                company_id=source_data["company_id"],
                url=source_data["url"],
                title=source_data.get("title"),
                provider=SourceProvider(source_data.get("provider", "internal")),
                content_text=source_data.get("content_text"),
                content_hash=source_data.get("content_hash"),
            )
            source_id = await evidence_repo.create_source(source)
            source_id_by_url[normalized_source_url] = source_id
            persisted_sources += 1

        except Exception as e:
            persist_errors += 1
            logger.warning("persist_source_failed", error=str(e), url=source_data.get("url"))

    # 2. Persist evidence (including fragments from existing sources)
    for ev_data in state.new_evidence:
        try:
            source_id = source_id_by_url.get(_url_key(ev_data.get("source_url")))
            if not source_id:
                persist_errors += 1
                logger.warning(
                    "persist_evidence_missing_source",
                    source_url=ev_data.get("source_url"),
                    section_id=ev_data.get("section_id"),
                )
                continue

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
            logger.warning("persist_evidence_failed", error=str(e))

    # 3. Persist extracted claims
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

    # 4. Create profile snapshot
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

    # 5. Update run status
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
    refreshed_assessments = _refresh_freshness_assessments(state)

    return {
        "profile_snapshot_id": snapshot_id,
        "freshness_assessments": refreshed_assessments,
        "metrics": metrics,
        "current_stage": WorkflowStage.PROFILE_PERSISTED,
        "completed_at": datetime.utcnow(),
    }


def _refresh_freshness_assessments(state: BuildProfileState) -> list[FreshnessAssessment]:
    """Recompute section freshness in-state after persisting new evidence."""
    if not state.freshness_assessments:
        return []

    now = datetime.utcnow()
    new_counts: dict[str, int] = {}
    for ev in state.new_evidence:
        section_id = ev.get("section_id")
        if section_id:
            sid = str(section_id)
            new_counts[sid] = new_counts.get(sid, 0) + 1

    refreshed: list[FreshnessAssessment] = []
    for assessment in state.freshness_assessments:
        added = new_counts.get(assessment.section_id, 0)
        if added > 0:
            refreshed.append(
                FreshnessAssessment(
                    section_id=assessment.section_id,
                    status="fresh",
                    last_evidence_at=now,
                    evidence_count=max(assessment.evidence_count, 0) + added,
                    ttl_days=assessment.ttl_days,
                    needs_refresh=False,
                )
            )
        else:
            refreshed.append(assessment)

    return refreshed
