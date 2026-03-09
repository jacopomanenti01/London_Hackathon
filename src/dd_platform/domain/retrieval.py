"""Retrieval domain models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RetrievalProfileName(str, Enum):
    """Named retrieval strategy profiles."""

    KEYWORD_ONLY = "keyword_only"
    VECTOR_ONLY = "vector_only"
    GRAPH_ONLY = "graph_only"
    HYBRID_BASIC = "hybrid_basic"
    GRAPH_HYBRID_EXPANDED = "graph_hybrid_expanded"
    SCHEMA_AWARE_GRAPH_HYBRID = "schema_aware_graph_hybrid"
    CONTRADICTION_AWARE_GRAPH_HYBRID = "contradiction_aware_graph_hybrid"


class RetrievalResult(BaseModel):
    """A single result from the retrieval layer."""

    result_type: str  # evidence, claim, profile_section
    score: float
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    text_snippet: str
    section_id: str | None = None
    field_id: str | None = None
    freshness_status: str | None = None
    contradiction_flag: bool = False
    provenance_path: list[str] = Field(default_factory=list)
    source_url: str | None = None
    retrieval_profile: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalContext(BaseModel):
    """Assembled context for LLM consumption."""

    company_id: str
    retrieval_profile: str
    results: list[RetrievalResult] = Field(default_factory=list)
    total_candidates: int = 0
    selected_count: int = 0
    sections_covered: list[str] = Field(default_factory=list)
    has_contradictions: bool = False
    assembly_metadata: dict[str, Any] = Field(default_factory=dict)


class RetrievalExperiment(BaseModel):
    """Experiment record for retrieval profile evaluation."""

    id: str | None = None
    run_id: str
    company_id: str
    retrieval_profile: str
    candidate_count: int = 0
    selected_count: int = 0
    config_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
