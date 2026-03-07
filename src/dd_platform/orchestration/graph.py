"""LangGraph workflow definitions for profile build, chat, and continuation.

This module wires the orchestration nodes into LangGraph StateGraphs
with conditional branching, checkpointing, and resumability.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph

from ..logging import get_logger
from .state import BuildProfileState, WorkflowStage

logger = get_logger(__name__)


def create_build_profile_graph(dependencies: dict[str, Any]) -> StateGraph:
    """Create the main profile build workflow graph.

    The graph implements the following flow:
    1. normalize_company -> resolve canonical identity
    2. load_local_context -> check SurrealDB for existing data
    3. assess_freshness -> evaluate what needs refresh
    4. plan_research -> build research plan
    5. [conditional] retrieve_external_evidence -> fetch from web tools
    6. extract_claims -> use LLM to extract claims
    7. synthesize_profile -> use LLM to synthesize profile
    8. persist_snapshot -> save to SurrealDB
    9. finalize_run -> mark complete

    Args:
        dependencies: Dict containing all required service instances:
            - llm: LLMAdapter
            - search_aggregator: SearchAggregator
            - company_repo: CompanyRepository
            - profile_repo: ProfileRepository
            - evidence_repo: EvidenceRepository
            - claim_repo: ClaimRepository
            - run_repo: RunRepository
            - freshness_queries: FreshnessQueries
            - schema: ProfileSchema

    Returns:
        Compiled LangGraph StateGraph.
    """
    from .nodes.normalize_company import normalize_company
    from .nodes.load_local_context import load_local_context
    from .nodes.assess_freshness import assess_freshness
    from .nodes.plan_research import plan_research
    from .nodes.retrieve_external_evidence import retrieve_external_evidence
    from .nodes.extract_claims import extract_claims
    from .nodes.synthesize_profile import synthesize_profile
    from .nodes.persist_snapshot import persist_snapshot
    from .nodes.finalize_run import finalize_run

    # Extract dependencies
    llm = dependencies["llm"]
    search_aggregator = dependencies["search_aggregator"]
    company_repo = dependencies["company_repo"]
    profile_repo = dependencies["profile_repo"]
    evidence_repo = dependencies["evidence_repo"]
    claim_repo = dependencies["claim_repo"]
    run_repo = dependencies["run_repo"]
    freshness_queries = dependencies["freshness_queries"]
    schema = dependencies["schema"]

    # Create node wrapper functions that inject dependencies
    async def _normalize(state: BuildProfileState) -> dict:
        return await normalize_company(state)

    async def _load_context(state: BuildProfileState) -> dict:
        return await load_local_context(state, company_repo, profile_repo, evidence_repo, claim_repo)

    async def _assess_fresh(state: BuildProfileState) -> dict:
        return await assess_freshness(state, freshness_queries, schema)

    async def _plan(state: BuildProfileState) -> dict:
        return await plan_research(state, schema)

    async def _retrieve(state: BuildProfileState) -> dict:
        return await retrieve_external_evidence(state, search_aggregator, evidence_repo)

    async def _extract(state: BuildProfileState) -> dict:
        return await extract_claims(state, llm)

    async def _synthesize(state: BuildProfileState) -> dict:
        return await synthesize_profile(state, llm, schema)

    async def _persist(state: BuildProfileState) -> dict:
        return await persist_snapshot(state, profile_repo, evidence_repo, claim_repo, run_repo)

    async def _finalize(state: BuildProfileState) -> dict:
        return await finalize_run(state)

    # Build the graph
    workflow = StateGraph(BuildProfileState)

    # Add nodes
    workflow.add_node("normalize_company", _normalize)
    workflow.add_node("load_local_context", _load_context)
    workflow.add_node("assess_freshness", _assess_fresh)
    workflow.add_node("plan_research", _plan)
    workflow.add_node("retrieve_external_evidence", _retrieve)
    workflow.add_node("extract_claims", _extract)
    workflow.add_node("synthesize_profile", _synthesize)
    workflow.add_node("persist_snapshot", _persist)
    workflow.add_node("finalize_run", _finalize)

    # Set entry point
    workflow.set_entry_point("normalize_company")

    # Define edges
    workflow.add_edge("normalize_company", "load_local_context")
    workflow.add_edge("load_local_context", "assess_freshness")
    workflow.add_edge("assess_freshness", "plan_research")

    # Conditional: skip external research if everything is fresh
    def should_research(state: BuildProfileState) -> str:
        if state.skip_external_research:
            return "synthesize_profile"
        return "retrieve_external_evidence"

    workflow.add_conditional_edges(
        "plan_research",
        should_research,
        {
            "retrieve_external_evidence": "retrieve_external_evidence",
            "synthesize_profile": "synthesize_profile",
        },
    )

    workflow.add_edge("retrieve_external_evidence", "extract_claims")
    workflow.add_edge("extract_claims", "synthesize_profile")
    workflow.add_edge("synthesize_profile", "persist_snapshot")
    workflow.add_edge("persist_snapshot", "finalize_run")
    workflow.add_edge("finalize_run", END)

    return workflow.compile()
