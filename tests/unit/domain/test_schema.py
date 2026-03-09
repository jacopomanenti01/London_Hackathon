"""Unit tests for profile schema domain models."""

from __future__ import annotations

from dd_platform.domain.schema import FieldDefinition, ProfileSchema, SectionDefinition


class TestFieldDefinition:
    """Tests for FieldDefinition model."""

    def test_creation(self, sample_field_definition: FieldDefinition) -> None:
        assert sample_field_definition.id == "legal_name"
        assert sample_field_definition.required is True
        assert sample_field_definition.ttl_days == 180

    def test_defaults(self) -> None:
        field = FieldDefinition(id="test_field")
        assert field.data_type == "string"
        assert field.required is False
        assert field.ttl_days == 90
        assert field.confidence_threshold == 0.5
        assert field.contradiction_policy == "flag"


class TestSectionDefinition:
    """Tests for SectionDefinition model."""

    def test_creation(self, sample_section_definition: SectionDefinition) -> None:
        assert sample_section_definition.id == "company_identity"
        assert len(sample_section_definition.fields) == 3

    def test_empty_fields(self) -> None:
        section = SectionDefinition(id="empty_section", title="Empty Section")
        assert section.fields == []


class TestProfileSchema:
    """Tests for ProfileSchema model."""

    def test_creation(self, sample_schema: ProfileSchema) -> None:
        assert sample_schema.schema_id == "due_diligence_v1"
        assert sample_schema.version == 1
        assert sample_schema.is_active is True
        assert len(sample_schema.sections) == 2

    def test_get_section(self, sample_schema: ProfileSchema) -> None:
        section = sample_schema.get_section("company_identity")
        assert section is not None
        assert section.title == "Company Identity"

    def test_get_section_not_found(self, sample_schema: ProfileSchema) -> None:
        assert sample_schema.get_section("nonexistent") is None

    def test_get_field(self, sample_schema: ProfileSchema) -> None:
        field = sample_schema.get_field("company_identity", "legal_name")
        assert field is not None
        assert field.required is True

    def test_get_field_not_found(self, sample_schema: ProfileSchema) -> None:
        assert sample_schema.get_field("company_identity", "nonexistent") is None

    def test_all_section_ids(self, sample_schema: ProfileSchema) -> None:
        ids = sample_schema.all_section_ids
        assert "company_identity" in ids
        assert "compliance_and_risk" in ids

    def test_required_field_ids(self, sample_schema: ProfileSchema) -> None:
        required = sample_schema.required_field_ids
        assert ("company_identity", "legal_name") in required
