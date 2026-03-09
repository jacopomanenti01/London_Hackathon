"""Unit tests for retrieval domain models."""

from __future__ import annotations

from dd_platform.domain.retrieval import (
    RetrievalContext,
    RetrievalProfileName,
    RetrievalResult,
)


class TestRetrievalProfileName:
    """Tests for RetrievalProfileName enum."""

    def test_profile_names(self) -> None:
        assert RetrievalProfileName.KEYWORD_ONLY == "keyword_only"
        assert RetrievalProfileName.GRAPH_HYBRID_EXPANDED == "graph_hybrid_expanded"
        assert RetrievalProfileName.SCHEMA_AWARE_GRAPH_HYBRID == "schema_aware_graph_hybrid"


class TestRetrievalResult:
    """Tests for RetrievalResult model."""

    def test_creation(self, sample_retrieval_result: RetrievalResult) -> None:
        assert sample_retrieval_result.result_type == "evidence"
        assert sample_retrieval_result.score == 0.85
        assert sample_retrieval_result.section_id == "company_identity"

    def test_default_values(self) -> None:
        result = RetrievalResult(
            result_type="claim",
            score=0.5,
            text_snippet="Some text",
        )
        assert result.contradiction_flag is False
        assert result.provenance_path == []
        assert result.metadata == {}


class TestRetrievalContext:
    """Tests for RetrievalContext model."""

    def test_creation(self, sample_retrieval_context: RetrievalContext) -> None:
        assert sample_retrieval_context.company_id == "company:www_example_com"
        assert sample_retrieval_context.selected_count == 3
        assert "company_identity" in sample_retrieval_context.sections_covered
        assert sample_retrieval_context.has_contradictions is False

    def test_empty_context(self) -> None:
        ctx = RetrievalContext(
            company_id="company:test_com",
            retrieval_profile="keyword_only",
        )
        assert ctx.results == []
        assert ctx.total_candidates == 0
