from typing import Any

from fastapi import HTTPException
from langchain_core.messages import HumanMessage

import logging

from ..agents.graph import build_research_graph, build_chat_graph
from ..utils.url import normalize_url
from .company_service import CompanyService
from .profile_service import ProfileService
from .graph_service import GraphService

logger = logging.getLogger(__name__)


class OrchestrationService:
    def __init__(self, company_svc: CompanyService, profile_svc: ProfileService, graph_svc: GraphService):
        self.company_svc = company_svc
        self.profile_svc = profile_svc
        self.graph_svc = graph_svc

    async def run_research(self, url: str, schema_override: dict | None = None) -> dict[str, Any]:
        url = normalize_url(url)
        await self.company_svc.get_or_create_company(url)

        schema = self.profile_svc.schema
        if schema_override:
            schema = self.profile_svc.set_schema(schema_override)

        result = await build_research_graph().ainvoke(_build_research_state(url, schema))

        profile = result.get("current_profile", {})
        entities = result.get("extracted_entities", [])

        # Store profile
        await self.profile_svc.store_profile(url, profile)
        await self.company_svc.update_company(url, _extract_company_metadata(profile))

        # Store entities in graph DB with embeddings
        entity_counts = {}
        if entities:
            entity_counts = await self.graph_svc.store_entities(url, entities)

        # Embed the profile on the company node
        await self.graph_svc.embed_profile(url, profile)

        # Compute graph embeddings (after entities are stored)
        await self.graph_svc.compute_graph_embeddings(url)

        # Compute risk score
        risk_data = await self.graph_svc.compute_risk_score(url)

        return {
            "company_url": url,
            "profile": profile,
            "entities_extracted": len(entities),
            "entity_counts": entity_counts,
            "risk_score": risk_data["risk_score"],
            "research_gaps": result.get("research_gaps", []),
        }

    async def chat(self, url: str, message: str) -> dict[str, Any]:
        url = normalize_url(url)
        profile = await self.profile_svc.get_profile(url)
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found. Run /company first.")

        # Use GraphRAG to get enriched context
        graph_context = await self.graph_svc.graph_rag_retrieve(url, message)

        profile_data = profile.get("sections", profile) if isinstance(profile, dict) else {}
        result = await build_chat_graph().ainvoke({
            "current_profile": profile_data,
            "graph_context": graph_context,
            "messages": [HumanMessage(content=message)],
        })

        messages = result.get("messages", [])
        response = messages[-1].content if messages else "No response generated."

        return {"company_url": url, "response": response}


def _build_research_state(url: str, schema: Any) -> dict[str, Any]:
    return {
        "company_url": url,
        "profile_schema": schema.model_dump(),
        "research_plan": {},
        "raw_research": {},
        "extracted_entities": [],
        "current_profile": {},
        "research_gaps": [],
        "iteration": 0,
        "max_iterations": 3,
        "messages": [],
        "error": None,
    }


def _extract_company_metadata(profile: dict) -> dict[str, Any]:
    overview = profile.get("company_overview", {})
    return {
        "name": overview.get("legal_name"),
        "description": overview.get("description"),
        "industry": overview.get("industry"),
    }
