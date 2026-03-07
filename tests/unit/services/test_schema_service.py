"""Unit tests for the schema service."""

from __future__ import annotations

import pytest

from dd_platform.application.services.schema_service import SchemaNotFoundError, SchemaService
from dd_platform.domain.schema import ProfileSchema


class TestSchemaService:
    """Tests for the SchemaService class."""

    def test_load_all_from_configs(self) -> None:
        service = SchemaService("configs/schemas")
        service.load_all()
        assert "due_diligence_v1" in service.available_schemas

    def test_get_schema(self) -> None:
        service = SchemaService("configs/schemas")
        service.load_all()
        schema = service.get_schema("due_diligence_v1")
        assert schema.schema_id == "due_diligence_v1"
        assert len(schema.sections) > 0

    def test_get_schema_not_found(self) -> None:
        service = SchemaService("configs/schemas")
        service.load_all()
        with pytest.raises(SchemaNotFoundError):
            service.get_schema("nonexistent_schema")

    def test_get_active_schema(self) -> None:
        service = SchemaService("configs/schemas")
        service.load_all()
        schema = service.get_active_schema()
        assert schema.is_active is True

    def test_activate_schema(self) -> None:
        service = SchemaService("configs/schemas")
        service.load_all()
        activated = service.activate_schema("due_diligence_v1")
        assert activated.is_active is True
        assert activated.schema_id == "due_diligence_v1"

    def test_register_schema(self, sample_schema: ProfileSchema) -> None:
        service = SchemaService("configs/schemas")
        sample_schema.schema_id = "test_custom_v1"
        service.register_schema(sample_schema)
        assert "test_custom_v1" in service.available_schemas

    def test_schema_sections_loaded(self) -> None:
        service = SchemaService("configs/schemas")
        service.load_all()
        schema = service.get_schema("due_diligence_v1")
        section = schema.get_section("company_identity")
        assert section is not None
        assert section.title == "Company Identity"

    def test_schema_fields_loaded(self) -> None:
        service = SchemaService("configs/schemas")
        service.load_all()
        schema = service.get_schema("due_diligence_v1")
        field = schema.get_field("company_identity", "legal_name")
        assert field is not None
        assert field.required is True

    def test_missing_dir_does_not_crash(self) -> None:
        service = SchemaService("/nonexistent/path")
        service.load_all()
        assert service.available_schemas == []
