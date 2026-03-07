"""Chat endpoint — evidence-backed conversation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1", tags=["chat"])


class ChatRequest(BaseModel):
    """Request body for POST /api/v1/chat."""

    company_id: str
    conversation_id: str | None = None
    message: str
    retrieval_profile: str = "schema_aware_graph_hybrid"


class ChatResponse(BaseModel):
    """Response for chat endpoint."""

    conversation_id: str
    answer: str
    citations: list[dict[str, Any]] = Field(default_factory=list)
    follow_up_research_suggested: bool = False
    retrieval_profile: str
    context_metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> dict:
    """Chat with a company's due diligence profile.

    Questions are answered using evidence from the knowledge graph.
    Responses include citations to claims and evidence.
    """
    deps = request.app.state.deps
    result = await deps.chat_service.chat(
        company_id=body.company_id,
        message=body.message,
        conversation_id=body.conversation_id,
        retrieval_profile=body.retrieval_profile,
    )
    return result
