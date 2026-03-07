"""ID generation utilities."""

from __future__ import annotations

import uuid
from datetime import datetime


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    uid = uuid.uuid4().hex[:16]
    if prefix:
        return f"{prefix}:{uid}"
    return uid


def generate_run_id() -> str:
    """Generate a run ID with timestamp."""
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    uid = uuid.uuid4().hex[:8]
    return f"run:{ts}_{uid}"


def generate_snapshot_id(company_id: str) -> str:
    """Generate a snapshot ID tied to a company."""
    uid = uuid.uuid4().hex[:12]
    return f"snapshot:{uid}"
