"""Node: Execute external research using web tools."""

from __future__ import annotations

from typing import Any

from ...logging import get_logger
from ...persistence.surreal.repositories.evidence_repo import EvidenceRepository
from ...providers.search.aggregator import SearchAggregator
from ...providers.search.base import ToolInput
from ...utils.hashing import content_hash
from ..state import BuildProfileState, WorkflowStage

logger = get_logger(__name__)


async def retrieve_external_evidence(
    state: BuildProfileState,
    search_aggregator: SearchAggregator,
    evidence_repo: EvidenceRepository,
) -> dict:
    """Execute the research plan using web tools.

    Runs search queries through the configured tool aggregator
    and collects raw results for evidence normalization.
    """
    logger.info(
        "node_retrieve_external_evidence",
        company_id=state.company_id,
        plan_items=len(state.research_plan),
    )

    all_sources: list[dict[str, Any]] = []
    all_evidence: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    skipped_existing = 0
    tool_failures: list[dict[str, str]] = []
    warnings = list(state.warnings)
    available_tools = set(search_aggregator.available_tools)
    existing_sources = await evidence_repo.find_sources_by_company(state.company_id, limit=5000)
    known_urls = {s.url.lower().rstrip("/") for s in existing_sources if s.url}

    for plan_item in state.research_plan:
        requested_providers = plan_item.recommended_tools or []
        providers = [p for p in requested_providers if p in available_tools]
        if requested_providers and not providers:
            warnings.append(
                f"Requested providers {requested_providers} unavailable; using available tools {sorted(available_tools)}."
            )
            providers = None

        # When only Apify is available, run one crawl per section instead of
        # launching one actor run per generated query.
        queries = plan_item.queries
        if providers == ["apify"] or providers == ["apify",]:
            queries = [plan_item.queries[0] if plan_item.queries else state.canonical_host]

        for query in queries:
            # For crawl-first runs (Apify only), avoid calling the crawler if
            # the canonical resource is already in DB.
            if providers == ["apify"] or providers == ["apify",]:
                target_url = f"https://{state.canonical_host}".lower().rstrip("/")
                if target_url in known_urls:
                    skipped_existing += 1
                    continue

            tool_input = ToolInput(
                query=query,
                company_host=state.canonical_host,
                max_results=10,
                include_domains=[state.canonical_host] if plan_item.section_id == "company_identity" else [],
            )

            try:
                output = await search_aggregator.search(
                    tool_input,
                    providers=providers,
                )

                for result in output.results:
                    url_key = result.url.lower().rstrip("/")
                    if url_key in seen_urls or url_key in known_urls:
                        skipped_existing += 1
                        continue
                    seen_urls.add(url_key)
                    known_urls.add(url_key)

                    source = {
                        "company_id": state.company_id,
                        "url": result.url,
                        "title": result.title,
                        "provider": result.provider,
                        "source_type": result.source_type,
                        "content_text": result.content_text or result.snippet,
                        "content_hash": content_hash(result.snippet),
                        "retrieved_at": result.retrieved_at.isoformat(),
                    }
                    all_sources.append(source)

                    # Create evidence fragments
                    evidence = {
                        "company_id": state.company_id,
                        "source_url": result.url,
                        "section_id": plan_item.section_id,
                        "excerpt": result.snippet,
                        "content_text": result.content_text,
                        "provider": result.provider,
                        "confidence": 0.5,
                    }
                    all_evidence.append(evidence)

            except Exception as e:
                tool_failures.append(
                    {
                        "section_id": plan_item.section_id,
                        "query": query,
                        "error": str(e),
                    }
                )
                warnings.append(
                    f"Tool acquisition failed for section '{plan_item.section_id}' and query '{query}': {e}"
                )
                logger.warning(
                    "research_query_failed",
                    query=query,
                    error=str(e),
                    section_id=plan_item.section_id,
                )

    logger.info(
        "external_evidence_retrieved",
        company_id=state.company_id,
        sources=len(all_sources),
        evidence=len(all_evidence),
    )

    metrics = dict(state.metrics)
    metrics["acquisition_query_failures"] = len(tool_failures)
    metrics["acquisition_skipped_existing_resources"] = skipped_existing
    if tool_failures:
        metrics["acquisition_failed_sections"] = sorted(
            {failure["section_id"] for failure in tool_failures}
        )

    return {
        "new_sources": all_sources,
        "new_evidence": all_evidence,
        "warnings": warnings,
        "metrics": metrics,
        "current_stage": WorkflowStage.EVIDENCE_NORMALIZED,
    }
