"""Schema service — load, validate, compile, and activate profile schemas.

The profile schema is runtime-configurable. Schemas are loaded from YAML
config files and mirrored in SurrealDB for versioning and activation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ...domain.schema import FieldDefinition, ProfileSchema, SectionDefinition
from ...logging import get_logger

logger = get_logger(__name__)


class SchemaNotFoundError(Exception):
    """Raised when a requested schema is not found."""

    def __init__(self, schema_id: str) -> None:
        self.schema_id = schema_id
        super().__init__(f"Schema not found: {schema_id}")


class SchemaService:
    """Manages profile schema lifecycle.

    Loads schemas from YAML configuration files, validates them,
    compiles field definitions, and manages activation. The active
    schema drives planning, extraction, synthesis, and validation.
    """

    def __init__(self, schemas_dir: str) -> None:
        self._schemas_dir = Path(schemas_dir)
        self._schemas: dict[str, ProfileSchema] = {}
        self._active_schema_id: str | None = None

    def load_all(self) -> None:
        """Load all schemas from the schemas directory."""
        if not self._schemas_dir.exists():
            logger.warning("schemas_dir_not_found", path=str(self._schemas_dir))
            return

        for schema_file in self._schemas_dir.glob("*.yaml"):
            try:
                schema = self._load_schema_file(schema_file)
                self._schemas[schema.schema_id] = schema
                logger.info(
                    "schema_loaded",
                    schema_id=schema.schema_id,
                    version=schema.version,
                    sections=len(schema.sections),
                )
            except Exception as e:
                logger.error("schema_load_error", file=str(schema_file), error=str(e))

    def _load_schema_file(self, path: Path) -> ProfileSchema:
        """Load and validate a single schema YAML file."""
        with open(path) as f:
            raw = yaml.safe_load(f)

        sections = []
        for raw_section in raw.get("sections", []):
            fields = []
            for raw_field in raw_section.get("fields", []):
                fields.append(
                    FieldDefinition(
                        id=raw_field["id"],
                        title=raw_field.get("title"),
                        description=raw_field.get("description"),
                        data_type=raw_field.get("type", "string"),
                        required=raw_field.get("required", False),
                        ttl_days=raw_field.get("ttl_days", 90),
                        evidence_requirements=raw_field.get("evidence_requirements"),
                        confidence_threshold=raw_field.get("confidence_threshold", 0.5),
                        contradiction_policy=raw_field.get("contradiction_policy", "flag"),
                        preferred_source_types=raw_field.get("preferred_source_types", []),
                        retrieval_hints=raw_field.get("retrieval_hints", {}),
                        synthesis_hints=raw_field.get("synthesis_hints", {}),
                        validation_rules=raw_field.get("validation_rules", []),
                    )
                )
            sections.append(
                SectionDefinition(
                    id=raw_section["id"],
                    title=raw_section.get("title", raw_section["id"]),
                    required=raw_section.get("required", False),
                    freshness_days=raw_section.get("freshness_days", 90),
                    retrieval_hints=raw_section.get("retrieval_hints", {}),
                    fields=fields,
                )
            )

        return ProfileSchema(
            schema_id=raw.get("schema_id", path.stem),
            version=raw.get("version", 1),
            is_active=raw.get("is_active", True),
            sections=sections,
            notes=raw.get("notes"),
        )

    def get_schema(self, schema_id: str) -> ProfileSchema:
        """Get a schema by ID.

        Args:
            schema_id: The schema identifier.

        Returns:
            The ProfileSchema.

        Raises:
            SchemaNotFoundError: If the schema doesn't exist.
        """
        if schema_id not in self._schemas:
            raise SchemaNotFoundError(schema_id)
        return self._schemas[schema_id]

    def get_active_schema(self) -> ProfileSchema:
        """Get the currently active schema.

        Returns:
            The active ProfileSchema.

        Raises:
            SchemaNotFoundError: If no active schema is set.
        """
        if self._active_schema_id and self._active_schema_id in self._schemas:
            return self._schemas[self._active_schema_id]
        # Fall back to first active schema
        for schema in self._schemas.values():
            if schema.is_active:
                self._active_schema_id = schema.schema_id
                return schema
        raise SchemaNotFoundError("no_active_schema")

    def activate_schema(self, schema_id: str) -> ProfileSchema:
        """Activate a specific schema version.

        Args:
            schema_id: The schema to activate.

        Returns:
            The activated ProfileSchema.
        """
        schema = self.get_schema(schema_id)
        # Deactivate all others
        for s in self._schemas.values():
            s.is_active = False
        schema.is_active = True
        self._active_schema_id = schema_id
        logger.info("schema_activated", schema_id=schema_id, version=schema.version)
        return schema

    def register_schema(self, schema: ProfileSchema) -> None:
        """Register a schema programmatically.

        Args:
            schema: The schema to register.
        """
        self._schemas[schema.schema_id] = schema
        logger.info("schema_registered", schema_id=schema.schema_id)

    @property
    def available_schemas(self) -> list[str]:
        """List all available schema IDs."""
        return list(self._schemas.keys())
