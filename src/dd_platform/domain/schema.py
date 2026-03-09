"""Profile schema domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class FieldDefinition(BaseModel):
    """A single field within a profile schema section."""

    id: str
    title: str | None = None
    description: str | None = None
    data_type: str = "string"  # string, integer, float, list[string], object, enum, datetime
    required: bool = False
    ttl_days: int = 90
    evidence_requirements: str | None = None
    confidence_threshold: float = 0.5
    contradiction_policy: str = "flag"  # flag, block, merge
    preferred_source_types: list[str] = Field(default_factory=list)
    retrieval_hints: dict[str, Any] = Field(default_factory=dict)
    synthesis_hints: dict[str, Any] = Field(default_factory=dict)
    validation_rules: list[str] = Field(default_factory=list)


class SectionDefinition(BaseModel):
    """A section in the profile schema containing multiple fields."""

    id: str
    title: str
    required: bool = False
    freshness_days: int = 90
    retrieval_hints: dict[str, Any] = Field(default_factory=dict)
    fields: list[FieldDefinition] = Field(default_factory=list)


class ProfileSchema(BaseModel):
    """The full profile schema definition, runtime-configurable."""

    schema_id: str
    version: int = 1
    is_active: bool = True
    sections: list[SectionDefinition] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notes: str | None = None

    def get_section(self, section_id: str) -> SectionDefinition | None:
        """Get a section by ID."""
        for section in self.sections:
            if section.id == section_id:
                return section
        return None

    def get_field(self, section_id: str, field_id: str) -> FieldDefinition | None:
        """Get a field within a section."""
        section = self.get_section(section_id)
        if section:
            for field in section.fields:
                if field.id == field_id:
                    return field
        return None

    @property
    def all_section_ids(self) -> list[str]:
        """Return all section IDs."""
        return [s.id for s in self.sections]

    @property
    def required_field_ids(self) -> list[tuple[str, str]]:
        """Return (section_id, field_id) for all required fields."""
        result: list[tuple[str, str]] = []
        for section in self.sections:
            for field in section.fields:
                if field.required:
                    result.append((section.id, field.id))
        return result


class SchemaConfig(BaseModel):
    """Schema configuration record persisted in SurrealDB."""

    id: str | None = None
    schema_id: str
    version: int
    is_active: bool = True
    schema_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    notes: str | None = None
