"""Unit tests for profile domain models."""

from __future__ import annotations

from dd_platform.domain.evidence import FreshnessStatus
from dd_platform.domain.profile import ProfileSection, ProfileSnapshot, RiskSignal


class TestProfileSection:
    """Tests for ProfileSection model."""

    def test_creation(self) -> None:
        section = ProfileSection(
            section_id="company_identity",
            section_json={"legal_name": {"value": "Test Corp", "confidence": 0.9}},
            freshness_status=FreshnessStatus.FRESH,
            evidence_count=3,
            claim_count=2,
        )
        assert section.section_id == "company_identity"
        assert section.freshness_status == FreshnessStatus.FRESH

    def test_defaults(self) -> None:
        section = ProfileSection(section_id="test_section")
        assert section.section_json == {}
        assert section.freshness_status == FreshnessStatus.FRESH
        assert section.evidence_count == 0


class TestProfileSnapshot:
    """Tests for ProfileSnapshot model."""

    def test_creation(self, sample_profile_snapshot: ProfileSnapshot) -> None:
        assert sample_profile_snapshot.company_id == "company:www_example_com"
        assert sample_profile_snapshot.schema_id == "due_diligence_v1"
        assert sample_profile_snapshot.is_latest is True

    def test_profile_json_structure(self, sample_profile_snapshot: ProfileSnapshot) -> None:
        pj = sample_profile_snapshot.profile_json
        assert "company_identity" in pj
        assert "compliance_and_risk" in pj

    def test_serialization_roundtrip(self, sample_profile_snapshot: ProfileSnapshot) -> None:
        data = sample_profile_snapshot.model_dump(mode="json")
        restored = ProfileSnapshot(**data)
        assert restored.id == sample_profile_snapshot.id
        assert restored.profile_json == sample_profile_snapshot.profile_json


class TestRiskSignal:
    """Tests for RiskSignal model."""

    def test_creation(self) -> None:
        signal = RiskSignal(
            company_id="company:www_example_com",
            category="sanctions",
            severity="high",
            summary="Potential sanctions exposure detected",
        )
        assert signal.category == "sanctions"
        assert signal.severity == "high"
        assert signal.status == "active"
