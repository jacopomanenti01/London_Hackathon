"""Helpers for safe SurrealQL thing/record ID interpolation."""

from __future__ import annotations

from typing import Any


def thing(record_id: Any) -> str:
    """Format a record ID for SurrealQL interpolation.

    For thing IDs in the form `table:id`, wrap the `id` part in backticks so
    hosts like `www.google.com` are parsed as a single identifier.
    """
    # surrealdb-py may return RecordID objects with .table_name / .id.
    table_name = getattr(record_id, "table_name", None)
    rec_id = getattr(record_id, "id", None)
    if table_name is not None and rec_id is not None:
        return f"{table_name}:`{str(rec_id).replace('`', '')}`"

    value = str(record_id).strip()
    if ":" not in value:
        return value

    table, rid = value.split(":", 1)
    if (rid.startswith("`") and rid.endswith("`")) or (rid.startswith("⟨") and rid.endswith("⟩")):
        return f"{table}:{rid}"

    safe_rid = rid.replace("`", "")
    return f"{table}:`{safe_rid}`"
