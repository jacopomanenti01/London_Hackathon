"""Continuation research endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/research", tags=["research"])


class ContinuationRequest(BaseModel):
    """Request body for POST /api/v1/research/continue."""

    company_id: str
    instruction: str
    target_sections: list[str] = Field(default_factory=list)
    publish_snapshot: bool = True
    retrieval_profile: str = "graph_hybrid_expanded"


class ContinuationResponse(BaseModel):
    """Response for continuation research."""

    company_id: str
    run_id: str
    instruction: str
    delta: dict[str, Any] = Field(default_factory=dict)
    new_evidence_count: int = 0
    new_claims_count: int = 0
    snapshot_id: str | None = None
    retrieval_profile: str


@router.post("/continue", response_model=ContinuationResponse)
async def continue_research(body: ContinuationRequest, request: Request) -> dict:
    """Direct agents to continue research into specific areas.

    The system will:
    1. Map the instruction to schema sections/fields
    2. Reuse existing evidence before new tool calls
    3. Execute targeted research
    4. Merge new evidence and claims into the graph
    5. Optionally publish a new profile snapshot
    """
    deps = request.app.state.deps
    result = await deps.continuation_service.continue_research(
        company_id=body.company_id,
        instruction=body.instruction,
        target_sections=body.target_sections or None,
        retrieval_profile=body.retrieval_profile,
        publish_snapshot=body.publish_snapshot,
    )
    return result
