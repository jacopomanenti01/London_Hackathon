from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from ..utils.url import normalize_url
from ..services.profile_service import ProfileService
from ..services.graph_service import GraphService
from ..services.orchestration_service import OrchestrationService
from ..tools.mock import advance_wave
from .dependencies import get_profile_service, get_graph_service, get_orchestration_service

router = APIRouter()


class CompanyRequest(BaseModel):
    url: str
    schema_override: dict | None = None


class ChatRequest(BaseModel):
    url: str
    message: str
    session_id: str | None = None


class SchemaUpdateRequest(BaseModel):
    profile_schema: dict


@router.post("/company")
async def create_profile(
    request: CompanyRequest,
    svc: OrchestrationService = Depends(get_orchestration_service),
) -> dict[str, Any]:
    return await svc.run_research(request.url, request.schema_override)


@router.get("/profile/{company_url:path}")
async def get_profile(
    company_url: str,
    svc: ProfileService = Depends(get_profile_service),
) -> dict[str, Any]:
    profile = await svc.get_profile(normalize_url(company_url))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.post("/chat")
async def chat(
    request: ChatRequest,
    svc: OrchestrationService = Depends(get_orchestration_service),
) -> dict[str, Any]:
    return await svc.chat(request.url, request.message)


@router.put("/schema")
async def update_schema(
    request: SchemaUpdateRequest,
    svc: ProfileService = Depends(get_profile_service),
) -> dict[str, Any]:
    schema = svc.set_schema(request.profile_schema)
    return {"message": "Schema updated", "schema": schema.model_dump()}


class AdvanceWaveRequest(BaseModel):
    url: str


@router.post("/advance-wave")
async def advance_wave_endpoint(request: AdvanceWaveRequest) -> dict[str, Any]:
    """Advance mock data to the next wave for a company (simulates new data arriving)."""
    new_wave = advance_wave(request.url)
    return {"url": request.url, "new_wave": new_wave}


@router.get("/risk-score/{company_url:path}")
async def get_risk_score(
    company_url: str,
    svc: GraphService = Depends(get_graph_service),
) -> dict[str, Any]:
    """Get the risk score and risk breakdown for a company from the knowledge graph."""
    url = normalize_url(company_url)
    return await svc.compute_risk_score(url)


@router.get("/graph/{company_url:path}")
async def get_graph(
    company_url: str,
    svc: GraphService = Depends(get_graph_service),
) -> dict[str, Any]:
    """Get the knowledge graph context for a company (GraphRAG retrieval)."""
    url = normalize_url(company_url)
    context = await svc.graph_rag_retrieve(url, "")
    return {"company_url": url, "graph_context": context}


@router.get("/graph-data/{company_url:path}")
async def get_graph_data(
    company_url: str,
    svc: GraphService = Depends(get_graph_service),
) -> dict[str, Any]:
    """Get knowledge graph nodes and edges in vis-network format."""
    url = normalize_url(company_url)
    return await svc.get_graph_data(url)


@router.get("/similar/{company_url:path}")
async def find_similar(
    company_url: str,
    svc: GraphService = Depends(get_graph_service),
) -> dict[str, Any]:
    """Find companies similar to the given one using graph embedding similarity."""
    url = normalize_url(company_url)
    similar = await svc.find_similar_companies(url)
    return {"company_url": url, "similar_companies": similar}


class BlacklistRequest(BaseModel):
    url: str


@router.post("/blacklist")
async def mark_blacklisted(
    request: BlacklistRequest,
    svc: GraphService = Depends(get_graph_service),
) -> dict[str, Any]:
    """Mark a company as blacklisted in the knowledge graph."""
    url = normalize_url(request.url)
    await svc.mark_blacklisted(url)
    return {"url": url, "blacklisted": True}


@router.get("/blacklist-check/{company_url:path}")
async def check_blacklist(
    company_url: str,
    threshold: float = 0.75,
    svc: GraphService = Depends(get_graph_service),
) -> dict[str, Any]:
    """Check if a company is similar to any blacklisted entity using graph embeddings."""
    url = normalize_url(company_url)
    return await svc.blacklist_check(url, threshold=threshold)
