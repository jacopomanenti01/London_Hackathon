from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, create_model


SCHEMA_DIR = Path(__file__).parent
DEFAULT_SCHEMA_PATH = SCHEMA_DIR / "default.yaml"


class FieldDef(BaseModel):
    name: str
    type: str = "string"
    required: bool = False


class SectionDef(BaseModel):
    description: str = ""
    fields: list[FieldDef] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)


class ProfileSchema(BaseModel):
    version: str = "1.0"
    name: str = ""
    description: str = ""
    sections: dict[str, SectionDef] = Field(default_factory=dict)


def load_schema(path: Path | None = None) -> ProfileSchema:
    path = path or DEFAULT_SCHEMA_PATH
    with open(path) as f:
        raw = yaml.safe_load(f)
    return ProfileSchema(**raw)


def load_schema_from_dict(data: dict[str, Any]) -> ProfileSchema:
    return ProfileSchema(**data)


_FIELD_TYPE_MAP = {
    "string": (str | None, None),
    "list": (list[str] | None, None),
    "int": (int | None, None),
    "float": (float | None, None),
    "bool": (bool | None, None),
}


def build_profile_model(schema: ProfileSchema) -> type[BaseModel]:
    section_models: dict[str, Any] = {}

    for section_name, section_def in schema.sections.items():
        field_definitions: dict[str, Any] = {}
        for field_def in section_def.fields:
            field_type = _FIELD_TYPE_MAP.get(field_def.type, (str | None, None))
            if field_def.required:
                field_definitions[field_def.name] = (field_type[0], ...)
            else:
                field_definitions[field_def.name] = field_type

        section_model = create_model(
            f"Section_{section_name}",
            **field_definitions,
        )
        section_models[section_name] = (section_model | None, None)

    return create_model("DueDiligenceProfile", **section_models)


def get_section_prompts(schema: ProfileSchema) -> dict[str, str]:
    prompts = {}
    for section_name, section_def in schema.sections.items():
        field_list = ", ".join(f.name for f in section_def.fields)
        prompts[section_name] = (
            f"Research the following about the company: {section_def.description}. "
            f"Provide information for these fields: {field_list}."
        )
    return prompts
