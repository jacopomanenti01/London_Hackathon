"""Node: Build a research plan based on freshness assessment and schema."""

from __future__ import annotations

from ...domain.schema import ProfileSchema
from ...logging import get_logger
from ..state import BuildProfileState, ResearchPlanItem, WorkflowStage

logger = get_logger(__name__)


async def plan_research(
    state: BuildProfileState,
    schema: ProfileSchema,
) -> dict:
    """Build a research plan targeting stale/missing sections.

    Uses the active schema to determine which tools are recommended
    for each section and generates search queries.
    """
    logger.info(
        "node_plan_research",
        company_id=state.company_id,
        sections_to_refresh=state.sections_needing_refresh,
    )

    if state.skip_external_research:
        return {
            "research_plan": [],
            "current_stage": WorkflowStage.RESEARCH_PLAN_BUILT,
        }

    plan: list[ResearchPlanItem] = []

    for section_id in state.sections_needing_refresh:
        section = schema.get_section(section_id)
        if not section:
            continue

        # Determine recommended tools from schema hints
        hints = section.retrieval_hints
        preferred_sources = hints.get("preferred_sources", ["tavily", "serpapi"])
        recommended_tools = [s for s in preferred_sources if s in ("tavily", "serpapi", "apify")]

        if not recommended_tools:
            recommended_tools = ["tavily", "serpapi"]

        # Generate search queries based on section and fields
        queries = _generate_queries(state.canonical_host, section_id, section.title, section.fields)

        field_ids = [f.id for f in section.fields if not f.required or True]

        plan.append(
            ResearchPlanItem(
                section_id=section_id,
                field_ids=field_ids,
                reason=f"Section '{section.title}' needs refresh",
                recommended_tools=recommended_tools,
                queries=queries,
                priority="high" if section.required else "normal",
            )
        )

    logger.info(
        "research_plan_built",
        company_id=state.company_id,
        plan_items=len(plan),
        total_queries=sum(len(p.queries) for p in plan),
    )

    return {
        "research_plan": plan,
        "current_stage": WorkflowStage.RESEARCH_PLAN_BUILT,
    }


def _generate_queries(host: str, section_id: str, section_title: str, fields: list) -> list[str]:
    """Generate search queries for a section based on fields."""
    queries = []
    base = host.replace("www.", "")

    query_templates = {
        "company_identity": [
            f'"{base}" company overview headquarters',
            f'"{base}" founded employees about',
        ],
        "ownership_and_structure": [
            f'"{base}" parent company subsidiaries ownership',
            f'"{base}" corporate structure investors',
        ],
        "operations_and_supply_chain": [
            f'"{base}" products services operations countries',
            f'"{base}" supply chain manufacturing facilities',
        ],
        "compliance_and_risk": [
            f'"{base}" sanctions compliance regulatory',
            f'"{base}" litigation lawsuit legal issues',
            f'"{base}" adverse media controversy',
        ],
        "esg_and_certifications": [
            f'"{base}" ESG sustainability certifications',
            f'"{base}" environmental policy human rights',
        ],
        "financial_health": [
            f'"{base}" revenue funding financial results',
            f'"{base}" insolvency bankruptcy financial distress',
        ],
    }

    if section_id in query_templates:
        queries = query_templates[section_id]
    else:
        # Generic fallback
        queries = [f'"{base}" {section_title.lower()}']

    return queries
