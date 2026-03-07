"""Company identity domain models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CompanyStatus(str, Enum):
    """Company record status."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    PENDING = "pending"


class CompanyRef(BaseModel):
    """Canonical company reference derived from URL normalization."""

    canonical_id: str = Field(description="Canonical ID, e.g. company:www.example.com")
    canonical_host: str = Field(description="Normalized host, e.g. www.example.com")
    canonical_url: str = Field(description="Normalized URL with scheme")
    root_domain: str = Field(description="Root domain, e.g. example.com")
    display_name: str | None = Field(default=None, description="Human-friendly display name")


class Company(BaseModel):
    """Full company record as persisted in SurrealDB."""

    id: str = Field(description="SurrealDB record ID: company:<host>")
    canonical_url: str
    canonical_host: str
    root_domain: str
    display_name: str | None = None
    latest_profile_snapshot_id: str | None = None
    active_schema_version: int | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    status: CompanyStatus = CompanyStatus.ACTIVE
    metadata: dict[str, Any] = Field(default_factory=dict)


class DomainAlias(BaseModel):
    """Alternative domain/host alias for a company."""

    id: str | None = None
    company_id: str
    alias_host: str
    alias_url: str | None = None
    reason: str = "redirect"
    created_at: datetime = Field(default_factory=datetime.utcnow)
