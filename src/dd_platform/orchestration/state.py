"""LangGraph state model for the profile build workflow.

The state object is explicit and typed. It carries all intermediate
artifacts through the workflow nodes and supports serialization
for checkpointing and resumability.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowStage(str, Enum):
    """Tracks the current stage of the build workflow."""

    INPUT_RECEIVED = "input_received"
    COMPANY_RESOLVED = "company_resolved"
    SCHEMA_LOADED = "schema_loaded"
    DB_CHECKED = "db_checked"
    FRESHNESS_EVALUATED = "freshness_evaluated"
    RETRIEVAL_PROFILE_SELECTED = "retrieval_profile_selected"
    RESEARCH_PLAN_BUILT = "research_plan_built"
    TOOL_RESEARCH_RUNNING = "tool_research_running"
    EVIDENCE_NORMALIZED = "evidence_normalized"
    CLAIMS_EXTRACTED = "claims_extracted"
    CLAIMS_RECONCILED = "claims_reconciled"
    PROFILE_SYNTHESIZED = "profile_synthesized"
    PROFILE_VALIDATED = "profile_validated"
    PROFILE_PERSISTED = "profile_persisted"
    CHAT_CONTEXT_READY = "chat_context_ready"
    EVALUATION_LOGGED = "evaluation_logged"
    COMPLETED = "completed"
    FAILED = "failed"


class FreshnessAssessment(BaseModel):
    """Freshness evaluation result per section."""

    section_id: str
    status: str  # fresh, stale, missing, contradictory, refresh_recommended
    last_evidence_at: datetime | None = None
    evidence_count: int = 0
    ttl_days: int = 90
    needs_refresh: bool = False


class ResearchPlanItem(BaseModel):
    """A single item in the research plan."""

    section_id: str
    field_ids: list[str] = Field(default_factory=list)
    reason: str = ""
    recommended_tools: list[str] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    priority: str = "normal"


class BuildProfileState(BaseModel):
    """Complete state for the profile build workflow.

    This is the typed state passed between LangGraph nodes.
    All intermediate and final artifacts are carried here.
    """

    # --- Request metadata ---
    request_id: str = ""
    run_id: str = ""
    company_url: str = ""
    force_refresh: bool = False
    target_sections: list[str] = Field(default_factory=list)
    retrieval_profile: str = "graph_hybrid_expanded"
    experiment_tags: list[str] = Field(default_factory=list)
    publish_snapshot: bool = True

    # --- Resolved identity ---
    company_id: str = ""
    canonical_host: str = ""
    canonical_url: str = ""
    root_domain: str = ""
    company_in_db_at_start: bool = False

    # --- Schema ---
    schema_id: str = ""
    schema_version: int = 1
    schema_sections: list[str] = Field(default_factory=list)

    # --- Existing data ---
    existing_snapshot_id: str | None = None
    existing_profile: dict[str, Any] = Field(default_factory=dict)
    existing_claims_count: int = 0
    existing_evidence_count: int = 0

    # --- Freshness ---
    freshness_assessments: list[FreshnessAssessment] = Field(default_factory=list)
    sections_needing_refresh: list[str] = Field(default_factory=list)

    # --- Research plan ---
    research_plan: list[ResearchPlanItem] = Field(default_factory=list)
    skip_external_research: bool = False

    # --- Retrieved evidence ---
    new_sources: list[dict[str, Any]] = Field(default_factory=list)
    new_evidence: list[dict[str, Any]] = Field(default_factory=list)

    # --- Claims ---
    extracted_claims: list[dict[str, Any]] = Field(default_factory=list)
    reconciled_claims: list[dict[str, Any]] = Field(default_factory=list)
    contradictions: list[dict[str, Any]] = Field(default_factory=list)

    # --- Profile ---
    profile_draft: dict[str, Any] = Field(default_factory=dict)
    validation_results: dict[str, Any] = Field(default_factory=dict)
    profile_snapshot_id: str | None = None

    # --- Workflow ---
    current_stage: WorkflowStage = WorkflowStage.INPUT_RECEIVED
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
