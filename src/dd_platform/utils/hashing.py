"""Hashing utilities for content deduplication."""

from __future__ import annotations

import hashlib


def content_hash(text: str) -> str:
    """Generate a SHA-256 hash of text content."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def short_hash(text: str, length: int = 12) -> str:
    """Generate a short hash for display or ID purposes."""
    return content_hash(text)[:length]
