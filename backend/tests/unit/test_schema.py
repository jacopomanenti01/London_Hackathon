from src.schemas.profile import (
    load_schema,
    load_schema_from_dict,
    build_profile_model,
    get_section_prompts,
    ProfileSchema,
)


def test_load_default_schema():
    schema = load_schema()
    assert schema.name == "Supply Chain Due Diligence Profile"
    assert schema.version == "1.0"
    assert len(schema.sections) > 0


def test_schema_has_expected_sections():
    schema = load_schema()
    expected = {"company_overview", "key_personnel", "financials", "esg",
                "legal_compliance", "supply_chain_risks", "certifications"}
    assert expected == set(schema.sections.keys())


def test_section_has_fields():
    schema = load_schema()
    overview = schema.sections["company_overview"]
    field_names = [f.name for f in overview.fields]
    assert "legal_name" in field_names
    assert "website" in field_names


def test_section_has_data_sources():
    schema = load_schema()
    overview = schema.sections["company_overview"]
    assert "tavily" in overview.data_sources


def test_load_schema_from_dict():
    data = {
        "version": "2.0",
        "name": "Custom Schema",
        "sections": {
            "basics": {
                "description": "Basic info",
                "fields": [{"name": "company_name", "type": "string", "required": True}],
                "data_sources": ["tavily"],
            }
        },
    }
    schema = load_schema_from_dict(data)
    assert schema.version == "2.0"
    assert "basics" in schema.sections


def test_build_profile_model():
    schema = load_schema()
    model = build_profile_model(schema)
    assert model is not None
    instance = model()
    assert hasattr(instance, "company_overview")
    assert hasattr(instance, "financials")


def test_get_section_prompts():
    schema = load_schema()
    prompts = get_section_prompts(schema)
    assert "company_overview" in prompts
    assert "legal_name" in prompts["company_overview"]
