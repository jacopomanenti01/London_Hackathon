"""Time utilities for freshness evaluation."""

from __future__ import annotations

from datetime import datetime, timedelta


def utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.utcnow()


def is_stale(last_updated: datetime | None, ttl_days: int) -> bool:
    """Check if a timestamp is stale based on TTL."""
    if last_updated is None:
        return True
    cutoff = utc_now() - timedelta(days=ttl_days)
    return last_updated < cutoff


def days_since(dt: datetime | None) -> int | None:
    """Return number of days since a datetime."""
    if dt is None:
        return None
    delta = utc_now() - dt
    return delta.days
