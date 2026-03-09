"""Evaluation and experiment domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EvaluationResult(BaseModel):
    """A single evaluation metric result."""

    id: str | None = None
    run_id: str
    company_id: str
    metric_name: str  # e.g., field_coverage, evidence_coverage_rate, grounded_answer_rate
    metric_value: float
    metric_group: str = "quality"  # quality, performance, cost
    notes: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExperimentReport(BaseModel):
    """Comparison report across retrieval profiles."""

    experiment_id: str
    company_ids: list[str]
    retrieval_profiles_compared: list[str]
    metrics: dict[str, list[EvaluationResult]] = Field(default_factory=dict)
    summary: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)
