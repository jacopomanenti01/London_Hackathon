"""Unit tests for the context assembler."""

from __future__ import annotations

from dd_platform.domain.retrieval import RetrievalResult
from dd_platform.retrieval.assembler import ContextAssembler


class TestContextAssembler:
    """Tests for the ContextAssembler class."""

    def setup_method(self) -> None:
        self.assembler = ContextAssembler(max_context_tokens=2000)

    def test_assemble_empty(self) -> None:
        ctx = self.assembler.assemble(
            company_id="company:test_com",
            retrieval_profile="keyword_only",
            results=[],
        )
        assert ctx.selected_count == 0
        assert ctx.results == []

    def test_assemble_basic(
        self, sample_retrieval_results: list[RetrievalResult]
    ) -> None:
        ctx = self.assembler.assemble(
            company_id="company:www_example_com",
            retrieval_profile="graph_hybrid_expanded",
            results=sample_retrieval_results,
        )
        assert ctx.selected_count > 0
        assert ctx.total_candidates == len(sample_retrieval_results)
        assert "company_identity" in ctx.sections_covered

    def test_deduplication(self) -> None:
        # Two results with the same text prefix
        results = [
            RetrievalResult(
                result_type="evidence",
                score=0.9,
                text_snippet="Example Corp is a global leader in widgets.",
                section_id="company_identity",
            ),
            RetrievalResult(
                result_type="evidence",
                score=0.7,
                text_snippet="Example Corp is a global leader in widgets.",
                section_id="company_identity",
            ),
        ]
        ctx = self.assembler.assemble(
            company_id="company:test_com",
            retrieval_profile="keyword_only",
            results=results,
        )
        # Should deduplicate
        assert ctx.selected_count == 1

    def test_contradiction_detection(self) -> None:
        results = [
            RetrievalResult(
                result_type="claim",
                score=0.8,
                text_snippet="Founded in 2010",
                contradiction_flag=True,
            ),
        ]
        ctx = self.assembler.assemble(
            company_id="company:test_com",
            retrieval_profile="hybrid_basic",
            results=results,
        )
        assert ctx.has_contradictions is True

    def test_format_for_llm(
        self, sample_retrieval_results: list[RetrievalResult]
    ) -> None:
        ctx = self.assembler.assemble(
            company_id="company:www_example_com",
            retrieval_profile="graph_hybrid_expanded",
            results=sample_retrieval_results,
        )
        formatted = self.assembler.format_for_llm(ctx)
        assert "company:www_example_com" in formatted
        assert "graph_hybrid_expanded" in formatted

    def test_token_budget_enforcement(self) -> None:
        # Create many large results
        results = [
            RetrievalResult(
                result_type="evidence",
                score=0.9 - i * 0.01,
                text_snippet="A" * 5000,  # ~1250 tokens each
                section_id=f"section_{i}",
            )
            for i in range(10)
        ]
        small_assembler = ContextAssembler(max_context_tokens=500)
        ctx = small_assembler.assemble(
            company_id="company:test_com",
            retrieval_profile="keyword_only",
            results=results,
        )
        # Should fit fewer than all 10
        assert ctx.selected_count < 10
