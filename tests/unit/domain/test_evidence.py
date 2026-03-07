"""Unit tests for evidence domain models."""

from __future__ import annotations

from dd_platform.domain.evidence import (
    Evidence,
    FreshnessStatus,
    SourceDocument,
    SourceProvider,
    SourceType,
)


class TestSourceDocument:
    """Tests for SourceDocument model."""

    def test_creation(self, sample_source_document: SourceDocument) -> None:
        assert sample_source_document.provider == SourceProvider.TAVILY
        assert sample_source_document.source_type == SourceType.OFFICIAL_SITE
        assert sample_source_document.url == "https://www.example.com/about"

    def test_default_source_type(self) -> None:
        doc = SourceDocument(
            company_id="company:test_com",
            url="https://test.com",
            provider=SourceProvider.SERPAPI,
        )
        assert doc.source_type == SourceType.OTHER

    def test_optional_content(self) -> None:
        doc = SourceDocument(
            company_id="company:test_com",
            url="https://test.com",
            provider=SourceProvider.MANUAL,
        )
        assert doc.content_text is None
        assert doc.content_hash is None


class TestEvidence:
    """Tests for Evidence model."""

    def test_creation(self, sample_evidence: Evidence) -> None:
        assert sample_evidence.section_id == "company_identity"
        assert sample_evidence.confidence == 0.85

    def test_confidence_bounds(self) -> None:
        ev = Evidence(
            company_id="company:test_com",
            source_document_id="source_document:sd_001",
            excerpt="Test excerpt",
            confidence=0.0,
        )
        assert ev.confidence == 0.0

        ev_high = Evidence(
            company_id="company:test_com",
            source_document_id="source_document:sd_001",
            excerpt="Test excerpt",
            confidence=1.0,
        )
        assert ev_high.confidence == 1.0

    def test_default_confidence(self) -> None:
        ev = Evidence(
            company_id="company:test_com",
            source_document_id="source_document:sd_001",
            excerpt="Test excerpt",
        )
        assert ev.confidence == 0.5


class TestFreshnessStatus:
    """Tests for FreshnessStatus enum."""

    def test_all_values(self) -> None:
        assert FreshnessStatus.FRESH == "fresh"
        assert FreshnessStatus.STALE == "stale"
        assert FreshnessStatus.MISSING == "missing"
        assert FreshnessStatus.CONTRADICTORY == "contradictory"
        assert FreshnessStatus.REFRESH_RECOMMENDED == "refresh_recommended"
