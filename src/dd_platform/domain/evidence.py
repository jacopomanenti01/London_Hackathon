"""Evidence and source document domain models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    """Classification of the source origin."""

    OFFICIAL_SITE = "official_site"
    NEWS = "news"
    DIRECTORY = "directory"
    MARKETPLACE = "marketplace"
    REGISTRY = "registry"
    SOCIAL_MENTION = "social_mention"
    SEARCH_RESULT = "search_result"
    CRAWLED_PAGE = "crawled_page"
    OTHER = "other"


class SourceProvider(str, Enum):
    """Which tool/provider retrieved this source."""

    TAVILY = "tavily"
    SERPAPI = "serpapi"
    APIFY = "apify"
    MANUAL = "manual"
    INTERNAL = "internal"


class SourceDocument(BaseModel):
    """A raw source document retrieved by a research tool."""

    id: str | None = None
    company_id: str
    url: str
    title: str | None = None
    provider: SourceProvider
    source_type: SourceType = SourceType.OTHER
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload_ref: str | None = None
    content_hash: str | None = None
    content_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class FreshnessStatus(str, Enum):
    """Freshness state for evidence or profile sections."""

    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"
    CONTRADICTORY = "contradictory"
    REFRESH_RECOMMENDED = "refresh_recommended"


class Evidence(BaseModel):
    """A normalized evidence fragment extracted from a source document."""

    id: str | None = None
    company_id: str
    source_document_id: str
    section_id: str | None = None
    field_id: str | None = None
    excerpt: str
    normalized_fact_candidate: str | None = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    published_at: datetime | None = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    embedding: list[float] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
