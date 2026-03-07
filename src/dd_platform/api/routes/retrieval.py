"""Retrieval search endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/retrieval", tags=["retrieval"])


class SearchRequest(BaseModel):
    """Request body for POST /api/v1/retrieval/search."""

    company_id: str
    query: str
    retrieval_profile: str = "hybrid_basic"
    section_ids: list[str] = Field(default_factory=list)
    top_k: int = 20


class SearchResponse(BaseModel):
    """Response for retrieval search."""

    company_id: str
    query: str
    retrieval_profile: str
    results: list[dict[str, Any]] = Field(default_factory=list)
    total_candidates: int = 0
    selected_count: int = 0
    sections_covered: list[str] = Field(default_factory=list)
    has_contradictions: bool = False


@router.post("/search", response_model=SearchResponse)
async def retrieval_search(body: SearchRequest, request: Request) -> dict:
    """Search the knowledge graph with configurable retrieval strategies.

    Returns ranked results with provenance and scoring metadata.
    """
    deps = request.app.state.deps
    result = await deps.retrieval_service.search(
        company_id=body.company_id,
        query=body.query,
        retrieval_profile=body.retrieval_profile,
        section_ids=body.section_ids or None,
        top_k=body.top_k,
    )
    return result
