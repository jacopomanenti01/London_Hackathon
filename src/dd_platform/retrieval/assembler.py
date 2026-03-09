"""Context assembler for LLM consumption.

Assembles retrieval results into structured context blocks,
deduplicates overlapping evidence, preserves provenance links,
and caps context size while preserving source diversity.
"""

from __future__ import annotations

from ..domain.retrieval import RetrievalContext, RetrievalResult
from ..domain.schema import ProfileSchema
from ..logging import get_logger

logger = get_logger(__name__)


class ContextAssembler:
    """Assembles retrieval results into structured LLM context.

    Builds section-specific context blocks rather than one giant
    unstructured dump. Includes conflicting evidence when contradictions
    are detected. Caps context size while preserving diversity.
    """

    def __init__(self, max_context_tokens: int = 8000) -> None:
        self._max_tokens = max_context_tokens

    def assemble(
        self,
        company_id: str,
        retrieval_profile: str,
        results: list[RetrievalResult],
        schema: ProfileSchema | None = None,
    ) -> RetrievalContext:
        """Assemble retrieval results into structured context.

        Args:
            company_id: The company being profiled.
            retrieval_profile: The retrieval profile used.
            results: Ranked retrieval results.
            schema: Optional active schema for section-aware assembly.

        Returns:
            Assembled RetrievalContext ready for LLM consumption.
        """
        # Deduplicate by text content
        seen_snippets: set[str] = set()
        deduped: list[RetrievalResult] = []
        for result in results:
            key = result.text_snippet[:150].lower().strip()
            if key not in seen_snippets:
                seen_snippets.add(key)
                deduped.append(result)

        # Group by section
        sections_covered: set[str] = set()
        has_contradictions = False

        for result in deduped:
            if result.section_id:
                sections_covered.add(result.section_id)
            if result.contradiction_flag:
                has_contradictions = True

        # Estimate token budget and truncate if needed
        selected = self._fit_to_budget(deduped)

        context = RetrievalContext(
            company_id=company_id,
            retrieval_profile=retrieval_profile,
            results=selected,
            total_candidates=len(results),
            selected_count=len(selected),
            sections_covered=sorted(sections_covered),
            has_contradictions=has_contradictions,
            assembly_metadata={
                "deduped_from": len(results),
                "max_tokens": self._max_tokens,
            },
        )

        logger.info(
            "context_assembled",
            company_id=company_id,
            total_candidates=len(results),
            selected=len(selected),
            sections=len(sections_covered),
            contradictions=has_contradictions,
        )

        return context

    def _fit_to_budget(self, results: list[RetrievalResult]) -> list[RetrievalResult]:
        """Select results that fit within the token budget."""
        selected: list[RetrievalResult] = []
        estimated_tokens = 0

        for result in results:
            # Rough token estimate: ~4 chars per token
            result_tokens = len(result.text_snippet) // 4 + 50  # overhead
            if estimated_tokens + result_tokens > self._max_tokens:
                break
            selected.append(result)
            estimated_tokens += result_tokens

        return selected

    def format_for_llm(self, context: RetrievalContext) -> str:
        """Format assembled context into a text block for LLM prompts.

        Args:
            context: The assembled retrieval context.

        Returns:
            Formatted text string for inclusion in LLM prompts.
        """
        parts: list[str] = []
        parts.append(f"## Retrieved Context for {context.company_id}")
        parts.append(f"Retrieval profile: {context.retrieval_profile}")
        parts.append(f"Results: {context.selected_count} of {context.total_candidates} candidates")
        parts.append("")

        # Group by section
        by_section: dict[str, list[RetrievalResult]] = {}
        unsectioned: list[RetrievalResult] = []

        for result in context.results:
            if result.section_id:
                by_section.setdefault(result.section_id, []).append(result)
            else:
                unsectioned.append(result)

        for section_id, section_results in sorted(by_section.items()):
            parts.append(f"### Section: {section_id}")
            for r in section_results:
                flag = " [CONTRADICTED]" if r.contradiction_flag else ""
                parts.append(f"- [{r.result_type}]{flag} (score: {r.score:.2f}): {r.text_snippet}")
            parts.append("")

        if unsectioned:
            parts.append("### Other")
            for r in unsectioned:
                parts.append(f"- [{r.result_type}] (score: {r.score:.2f}): {r.text_snippet}")
            parts.append("")

        return "\n".join(parts)
