"""Agent run and research task domain models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class RunType(str, Enum):
    """Type of agent run."""

    BUILD = "build"
    CONTINUATION = "continuation"
    CHAT = "chat"
    EVALUATION = "evaluation"


class RunStatus(str, Enum):
    """Run lifecycle status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class AgentRun(BaseModel):
    """Metadata for a single orchestration run."""

    id: str | None = None
    company_id: str
    run_type: RunType
    status: RunStatus = RunStatus.PENDING
    retrieval_profile: str | None = None
    experiment_tags: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: datetime | None = None
    active_schema_version: int | None = None
    input_payload: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    trace_id: str | None = None
    error_summary: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class ResearchTask(BaseModel):
    """A targeted research task created by chat or continuation."""

    id: str | None = None
    company_id: str
    instruction: str
    scope: list[str] = Field(default_factory=list)  # section IDs or field IDs
    priority: str = "normal"  # low, normal, high, urgent
    status: str = "pending"  # pending, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_from_message_id: str | None = None
    completed_at: datetime | None = None
