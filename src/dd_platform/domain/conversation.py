"""Conversation and message domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Conversation(BaseModel):
    """A chat conversation about a company profile."""

    id: str | None = None
    company_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Citation(BaseModel):
    """A citation reference in a chat response."""

    claim_id: str | None = None
    evidence_id: str | None = None
    url: str | None = None
    excerpt: str | None = None


class Message(BaseModel):
    """A single message in a conversation."""

    id: str | None = None
    conversation_id: str
    role: str  # user, assistant, system
    content: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    retrieval_refs: list[dict[str, Any]] = Field(default_factory=list)
    research_task_id: str | None = None
    citations: list[Citation] | None = None
