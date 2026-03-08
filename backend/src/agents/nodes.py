import asyncio
import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from ..models.chat import llm
from ..tools.base import SearchResult
from ..services.research_service import ResearchService
from ..schemas.profile import ProfileSchema, get_section_prompts

logger = logging.getLogger(__name__)

_research_service: ResearchService | None = None


def _get_research_service() -> ResearchService:
    global _research_service
    if _research_service is None:
        _research_service = ResearchService()
    return _research_service


async def plan_research(state: dict[str, Any]) -> dict[str, Any]:
    schema = ProfileSchema(**state["profile_schema"])
    prompts = get_section_prompts(schema)

    gaps = state.get("research_gaps", [])
    if gaps:
        prompts = {k: v for k, v in prompts.items() if k in gaps}

    return {"research_plan": prompts}


async def web_research(state: dict[str, Any]) -> dict[str, Any]:
    logger.info("web_research state keys: %s", list(state.keys()))
    company_url = state["company_url"]
    research_plan = state["research_plan"]

    service = _get_research_service()
    section_results: dict[str, list[dict]] = {}

    async def _search_section(section_name: str, query: str) -> tuple[str, list[dict]]:
        full_query = f"{company_url} {query}"
        sources = ["linkedin_people"] if section_name == "key_personnel" else None
        results = await service.search(full_query, sources=sources)
        return section_name, [r.model_dump() for r in results]

    tasks = [_search_section(name, q) for name, q in research_plan.items()]
    for name, data in await asyncio.gather(*tasks):
        section_results[name] = data

    return {"raw_research": section_results}


async def extract_entities(state: dict[str, Any]) -> dict[str, Any]:
    raw_research = state["raw_research"]
    all_content = ""
    for section, results in raw_research.items():
        for r in results:
            all_content += f"\n[{section}] {r.get('title', '')}: {r.get('content', '')}\n"

    if not all_content.strip():
        return {"extracted_entities": []}

    response = await llm.ainvoke([
        SystemMessage(content=(
            "Extract structured entities from the following research data. "
            "Return a JSON array of objects, each with: "
            '{"type": "company|person|risk|certification", "name": "...", '
            '"attributes": {...}}. Return ONLY the JSON array.'
        )),
        HumanMessage(content=all_content[:15000]),
    ])

    try:
        text = response.content
        start = text.find("[")
        end = text.rfind("]") + 1
        entities = json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        entities = []

    return {"extracted_entities": entities}


async def build_profile(state: dict[str, Any]) -> dict[str, Any]:
    schema = ProfileSchema(**state["profile_schema"])
    raw_research = state["raw_research"]
    company_url = state["company_url"]

    async def _build_section(section_name: str, section_def: Any) -> tuple[str, dict]:
        section_data = raw_research.get(section_name, [])
        logger.info("[build_profile] Section '%s' has %d research items", section_name, len(section_data))
        context = "\n".join(
            f"- {r.get('title', '')}: {r.get('content', '')}"
            for r in section_data
        )
        logger.info("[build_profile] Section '%s' context (first 500 chars): %s", section_name, context[:500])

        field_names = [f.name for f in section_def.fields]
        response = await llm.ainvoke([
            SystemMessage(content=(
                f"Based on the research data below, fill in the following fields "
                f"for the company {company_url}.\n"
                f"Fields: {', '.join(field_names)}\n"
                f"Section: {section_def.description}\n"
                f"Return a JSON object with these field names as keys. "
                f"Use null for fields you cannot determine. Return ONLY JSON."
            )),
            HumanMessage(content=context if context.strip() else "No data available."),
        ])

        try:
            text = response.content
            logger.info("[build_profile] Section '%s' LLM response (first 500 chars): %s", section_name, text[:500])
            start = text.find("{")
            end = text.rfind("}") + 1
            section_result = json.loads(text[start:end])
        except (json.JSONDecodeError, ValueError):
            logger.warning("[build_profile] Section '%s' failed to parse LLM response", section_name)
            section_result = {f: None for f in field_names}

        return section_name, section_result

    tasks = [
        _build_section(name, defn)
        for name, defn in schema.sections.items()
    ]
    results = await asyncio.gather(*tasks)
    profile_sections = dict(results)

    # Identify gaps
    gaps = []
    for section_name, section_data in profile_sections.items():
        section_def = schema.sections[section_name]
        required_fields = [f.name for f in section_def.fields if f.required]
        for field_name in required_fields:
            if not section_data.get(field_name):
                gaps.append(section_name)
                break

    return {
        "current_profile": profile_sections,
        "research_gaps": gaps,
        "iteration": state.get("iteration", 0) + 1,
    }


async def store_results(state: dict[str, Any]) -> dict[str, Any]:
    # Storage is handled by the API layer after the graph completes.
    # This node is a passthrough that signals completion.
    return {}


def should_continue(state: dict[str, Any]) -> str:
    gaps = state.get("research_gaps", [])
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 3)

    if gaps and iteration < max_iterations:
        return "plan_research"
    return "store_results"


async def chat_node(state: dict[str, Any]) -> dict[str, Any]:
    messages = state.get("messages", [])
    profile = state.get("current_profile", {})
    graph_context = state.get("graph_context", "")

    profile_context = json.dumps(profile, indent=2, default=str)

    system_prompt = (
        "You are a due diligence analyst with access to a company knowledge graph. "
        "You have TWO sources of information:\n\n"
        "### 1. Company Profile (structured data)\n"
        f"{profile_context}\n\n"
    )
    if graph_context:
        system_prompt += (
            "### 2. Knowledge Graph Context (graph-retrieved relationships, risks, connected entities)\n"
            f"{graph_context}\n\n"
        )
    system_prompt += (
        "Use BOTH sources to answer questions. When information comes from the "
        "knowledge graph (connected entities, risk scores, supplier relationships), "
        "explicitly mention it — e.g. 'According to the knowledge graph...' or "
        "'Graph analysis shows...'. This helps the user understand how graph-based "
        "retrieval enhances the analysis beyond flat document search.\n\n"
        "If they ask you to investigate further, respond with a JSON object: "
        '{"action": "research", "topics": ["topic1", "topic2"]}. '
        "Otherwise respond normally."
    )

    system_msg = SystemMessage(content=system_prompt)
    response = await llm.ainvoke([system_msg] + messages)
    return {"messages": messages + [response]}
