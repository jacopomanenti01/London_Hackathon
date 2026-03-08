from datetime import datetime, timezone


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)
from pydantic import BaseModel, Field
from typing import Any


class Company(BaseModel):
    url: str
    name: str | None = None
    description: str | None = None
    industry: str | None = None
    headquarters: str | None = None
    last_updated: datetime = Field(default_factory=_utcnow)


class Person(BaseModel):
    name: str
    role: str | None = None
    company_url: str | None = None
    last_updated: datetime = Field(default_factory=_utcnow)


class Risk(BaseModel):
    category: str
    severity: str | None = None
    description: str | None = None
    source: str | None = None
    company_url: str | None = None
    last_updated: datetime = Field(default_factory=_utcnow)


class Certification(BaseModel):
    name: str
    issuer: str | None = None
    valid_until: str | None = None
    company_url: str | None = None
    last_updated: datetime = Field(default_factory=_utcnow)


class Profile(BaseModel):
    company_url: str
    schema_version: str = "1.0"
    sections: dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=_utcnow)


# Edge/relation type constants
class Relations:
    WORKS_AT = "works_at"
    HAS_RISK = "has_risk"
    HAS_CERTIFICATION = "has_certification"
    SUPPLIES_TO = "supplies_to"
    SUBSIDIARY_OF = "subsidiary_of"
    PARTNERS_WITH = "partners_with"
