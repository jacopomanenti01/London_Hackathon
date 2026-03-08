from src.db.models import Company, Person, Risk, Certification, Profile, Relations


def test_company_defaults():
    c = Company(url="https://acme.com")
    assert c.url == "https://acme.com"
    assert c.name is None
    assert c.last_updated is not None


def test_company_with_data():
    c = Company(url="https://acme.com", name="Acme Corp", industry="Tech")
    assert c.name == "Acme Corp"
    assert c.industry == "Tech"


def test_person_model():
    p = Person(name="John Doe", role="CEO", company_url="https://acme.com")
    assert p.name == "John Doe"
    assert p.role == "CEO"


def test_risk_model():
    r = Risk(category="Financial", severity="High", description="Revenue declining")
    assert r.category == "Financial"
    assert r.severity == "High"


def test_certification_model():
    c = Certification(name="ISO 9001", issuer="ISO")
    assert c.name == "ISO 9001"


def test_profile_model():
    p = Profile(company_url="https://acme.com", sections={"overview": {"name": "Acme"}})
    assert p.company_url == "https://acme.com"
    assert p.schema_version == "1.0"
    assert "overview" in p.sections


def test_relations_constants():
    assert Relations.WORKS_AT == "works_at"
    assert Relations.HAS_RISK == "has_risk"
    assert Relations.SUPPLIES_TO == "supplies_to"
