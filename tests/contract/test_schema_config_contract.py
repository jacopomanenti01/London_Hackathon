"""Contract tests for schema YAML configuration files.

Validates that the YAML configs in configs/schemas/ can be loaded
and produce valid ProfileSchema objects with all expected sections.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dd_platform.application.services.schema_service import SchemaService


@pytest.mark.contract
class TestSchemaConfigContract:
    """Ensure schema YAML files satisfy the expected contract."""

    def test_due_diligence_v1_exists(self) -> None:
        path = Path("configs/schemas/due_diligence_v1.yaml")
        assert path.exists(), "due_diligence_v1.yaml must exist"

    def test_due_diligence_v1_valid_yaml(self) -> None:
        with open("configs/schemas/due_diligence_v1.yaml") as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert "schema_id" in data
        assert "sections" in data

    def test_due_diligence_v1_loads_via_service(self) -> None:
        service = SchemaService("configs/schemas")
        service.load_all()
        schema = service.get_schema("due_diligence_v1")
        assert schema.version >= 1

    def test_required_sections_present(self) -> None:
        service = SchemaService("configs/schemas")
        service.load_all()
        schema = service.get_schema("due_diligence_v1")
        expected_sections = {
            "company_identity",
            "compliance_and_risk",
            "profile_meta",
        }
        actual_ids = set(schema.all_section_ids)
        assert expected_sections.issubset(actual_ids), (
            f"Missing sections: {expected_sections - actual_ids}"
        )

    def test_all_sections_have_fields(self) -> None:
        service = SchemaService("configs/schemas")
        service.load_all()
        schema = service.get_schema("due_diligence_v1")
        for section in schema.sections:
            assert len(section.fields) > 0, (
                f"Section '{section.id}' has no fields"
            )

    def test_field_ttl_days_positive(self) -> None:
        service = SchemaService("configs/schemas")
        service.load_all()
        schema = service.get_schema("due_diligence_v1")
        for section in schema.sections:
            for field in section.fields:
                assert field.ttl_days > 0, (
                    f"Field '{field.id}' in section '{section.id}' has invalid ttl_days"
                )
