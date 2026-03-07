"""Profile snapshot and section domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .evidence import FreshnessStatus


class ProfileSection(BaseModel):
    """A single section within a profile snapshot."""

    id: str | None = None
    profile_snapshot_id: str | None = None
    section_id: str
    section_json: dict[str, Any] = Field(default_factory=dict)
    freshness_status: FreshnessStatus = FreshnessStatus.FRESH
    evidence_count: int = 0
    claim_count: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProfileSnapshot(BaseModel):
    """Immutable, time-stamped profile representation published by a run."""

    id: str | None = None
    company_id: str
    schema_id: str
    schema_version: int
    profile_json: dict[str, Any] = Field(default_factory=dict)
    sections: list[ProfileSection] = Field(default_factory=list)
    coverage_summary: dict[str, Any] = Field(default_factory=dict)
    quality_summary: dict[str, Any] = Field(default_factory=dict)
    retrieval_profile: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by_run_id: str | None = None
    is_latest: bool = True


class RiskSignal(BaseModel):
    """A detected risk signal for a company."""

    id: str | None = None
    company_id: str
    category: str  # sanctions, litigation, environmental, corruption, etc.
    severity: str = "medium"  # low, medium, high, critical
    summary: str
    status: str = "active"  # active, resolved, monitoring
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    source_claim_ids: list[str] = Field(default_factory=list)
