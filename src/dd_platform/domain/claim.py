"""Claim domain models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ClaimStatus(str, Enum):
    """Status of a claim in its lifecycle."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    CONTRADICTED = "contradicted"
    RETRACTED = "retracted"
    UNVERIFIED = "unverified"


class Claim(BaseModel):
    """A normalized statement derived from one or more pieces of evidence."""

    id: str | None = None
    company_id: str
    section_id: str
    field_id: str
    value: str
    value_type: str = "string"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    status: ClaimStatus = ClaimStatus.ACTIVE
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_verified_at: datetime = Field(default_factory=datetime.utcnow)
    derived_from_evidence_count: int = 0
    schema_version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)


class ClaimContradiction(BaseModel):
    """A detected contradiction between two claims."""

    claim_a_id: str
    claim_b_id: str
    field_id: str
    description: str
    severity: str = "medium"  # low, medium, high
    detected_at: datetime = Field(default_factory=datetime.utcnow)
