"""Profile build and retrieval endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])


class BuildProfileRequest(BaseModel):
    """Request body for POST /api/v1/profiles/build."""

    company_url: str
    force_refresh: bool = False
    schema_id: str | None = None
    publish_snapshot: bool = True
    research_scope: list[str] = Field(default_factory=lambda: ["all"])
    retrieval_profile: str = "graph_hybrid_expanded"
    experiment_tags: list[str] = Field(default_factory=list)


class BuildProfileResponse(BaseModel):
    """Response for profile build."""

    company_id: str
    run_id: str
    profile: dict[str, Any]
    snapshot_id: str | None = None
    schema_id: str
    schema_version: int
    retrieval_profile: str
    freshness: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    status: str
    errors: list[str] = Field(default_factory=list)


@router.post("/build", response_model=BuildProfileResponse)
async def build_profile(body: BuildProfileRequest, request: Request) -> dict:
    """Build a due diligence profile for a company.

    The system will:
    1. Normalize the company URL into a canonical ID
    2. Check SurrealDB for existing data
    3. Evaluate freshness per schema section
    4. Fetch only missing/stale evidence from web tools
    5. Extract claims using LLM
    6. Synthesize a schema-valid profile
    7. Persist all artifacts to SurrealDB
    """
    deps = request.app.state.deps

    target_sections = None
    if body.research_scope and body.research_scope != ["all"]:
        target_sections = body.research_scope

    result = await deps.profile_service.build_profile(
        company_url=body.company_url,
        schema_id=body.schema_id,
        force_refresh=body.force_refresh,
        retrieval_profile=body.retrieval_profile,
        target_sections=target_sections,
        experiment_tags=body.experiment_tags,
        publish_snapshot=body.publish_snapshot,
    )
    return result


@router.get("/{company_id}")
async def get_profile(company_id: str, request: Request) -> dict:
    """Get the latest profile snapshot for a company.

    Args:
        company_id: The canonical company ID (e.g., company:www_example_com).
    """
    deps = request.app.state.deps
    snapshot = await deps.profile_repo.get_latest(company_id)
    if not snapshot:
        return {"company_id": company_id, "profile": None, "message": "No profile found"}

    return {
        "company_id": company_id,
        "snapshot_id": snapshot.id,
        "schema_id": snapshot.schema_id,
        "schema_version": snapshot.schema_version,
        "profile": snapshot.profile_json,
        "coverage_summary": snapshot.coverage_summary,
        "retrieval_profile": snapshot.retrieval_profile,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        "is_latest": snapshot.is_latest,
    }


@router.get("/{company_id}/evidence")
async def get_evidence(
    company_id: str,
    request: Request,
    section_id: str | None = None,
    field_id: str | None = None,
    limit: int = 50,
) -> dict:
    """Get evidence for a company with optional filters.

    Supports filtering by section_id, field_id, and limit.
    """
    deps = request.app.state.deps
    evidence = await deps.evidence_repo.find_by_company(
        company_id=company_id,
        section_id=section_id,
        field_id=field_id,
        limit=limit,
    )
    return {
        "company_id": company_id,
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "count": len(evidence),
    }
