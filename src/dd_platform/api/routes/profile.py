"""Profile build and retrieval endpoints."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

from ...logging import get_logger
from ...providers.llm.models import LLMMessage, LLMRequest, StructuredLLMRequest
from ...utils.url_normalization import normalize_company_id

router = APIRouter(prefix="/api/v1/profiles", tags=["profiles"])
logger = get_logger(__name__)


def _company_id_aliases(company_id: str) -> list[str]:
    """Return company ID aliases across underscore/dot and www/non-www forms."""
    raw = company_id.strip().strip("'\"").lower()
    if not raw:
        return []

    if raw.startswith("company:"):
        host_raw = raw.split(":", 1)[1].strip()
    else:
        host_raw = raw

    host_underscore = host_raw.replace(".", "_")
    host_dot = host_raw.replace("_", ".")

    variants = {
        host_underscore,
        host_dot,
    }
    if host_underscore.startswith("www_"):
        variants.add(host_underscore[4:])
    else:
        variants.add(f"www_{host_underscore}")
    if host_dot.startswith("www."):
        variants.add(host_dot[4:])
    else:
        variants.add(f"www.{host_dot}")

    aliases = [f"company:{v}" for v in variants if v]
    aliases.append(normalize_company_id(company_id))
    return list(dict.fromkeys(aliases))


async def _resolve_company_id(company_id: str, deps: Any) -> str:
    """Resolve to an existing company ID when possible."""
    for candidate in _company_id_aliases(company_id):
        company = await deps.company_repo.find_by_id(candidate)
        if company:
            return company.id
    return normalize_company_id(company_id)


class BuildProfileRequest(BaseModel):
    """Request body for POST /api/v1/profiles/build."""

    company_url: str
    force_refresh: bool = False
    schema_id: str | None = None
    publish_snapshot: bool = True
    research_scope: list[str] = Field(default_factory=lambda: ["all"])
    retrieval_profile: str = "graph_hybrid_expanded"
    experiment_tags: list[str] = Field(default_factory=list)


class BuildProfileResponse(BaseModel):
    """Response for profile build."""

    company_id: str
    run_id: str
    profile: dict[str, Any]
    snapshot_id: str | None = None
    schema_id: str
    schema_version: int
    retrieval_profile: str
    freshness: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    status: str
    errors: list[str] = Field(default_factory=list)


@router.post("/build", response_model=BuildProfileResponse)
async def build_profile(body: BuildProfileRequest, request: Request) -> dict:
    """Build a due diligence profile for a company.

    The system will:
    1. Normalize the company URL into a canonical ID
    2. Check SurrealDB for existing data
    3. Evaluate freshness per schema section
    4. Fetch only missing/stale evidence from web tools
    5. Extract claims using LLM
    6. Synthesize a schema-valid profile
    7. Persist all artifacts to SurrealDB
    """
    deps = request.app.state.deps

    target_sections = None
    if body.research_scope and body.research_scope != ["all"]:
        target_sections = body.research_scope

    result = await deps.profile_service.build_profile(
        company_url=body.company_url,
        schema_id=body.schema_id,
        force_refresh=body.force_refresh,
        retrieval_profile=body.retrieval_profile,
        target_sections=target_sections,
        experiment_tags=body.experiment_tags,
        publish_snapshot=body.publish_snapshot,
    )
    return result


def _extract_profile_sections(profile_json: dict[str, Any]) -> dict[str, Any]:
    """Normalize profile JSON into a section map."""
    if not isinstance(profile_json, dict):
        return {}

    if isinstance(profile_json.get("sections"), dict):
        return profile_json["sections"]

    return {
        key: value
        for key, value in profile_json.items()
        if key not in {"profile_meta"}
    }


async def _build_profile_report(
    company_id: str,
    snapshot: Any,
    deps: Any,
) -> dict[str, Any]:
    """Build an LLM-formatted profile report with section references."""
    sections = _extract_profile_sections(snapshot.profile_json or {})

    evidence_rows = await deps.evidence_repo.find_by_company(company_id=company_id, limit=300)
    source_rows = await deps.evidence_repo.find_sources_by_company(company_id=company_id, limit=500)

    source_map: dict[str, dict[str, Any]] = {}
    for source in source_rows:
        if source.id:
            source_map[source.id] = {
                "url": source.url,
                "title": source.title,
                "provider": source.provider,
            }

    section_references: dict[str, list[dict[str, Any]]] = {}
    for ev in evidence_rows:
        sid = ev.section_id or "general"
        refs = section_references.setdefault(sid, [])
        source = source_map.get(ev.source_document_id, {})
        refs.append(
            {
                "evidence_id": ev.id,
                "source_document_id": ev.source_document_id,
                "url": source.get("url"),
                "title": source.get("title"),
                "provider": source.get("provider"),
                "excerpt": (ev.excerpt or "")[:300],
                "confidence": ev.confidence,
            }
        )

    for sid, refs in section_references.items():
        section_references[sid] = refs[:8]

    report_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "company_id": {"type": "string"},
            "executive_summary": {"type": "string"},
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "section_id": {"type": "string"},
                        "section_title": {"type": "string"},
                        "description": {"type": "string"},
                        "fields": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "field": {"type": "string"},
                                    "value": {},
                                    "description": {"type": "string"},
                                    "references": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "url": {"type": "string"},
                                                "title": {"type": "string"},
                                                "source_document_id": {"type": "string"},
                                                "evidence_excerpt": {"type": "string"},
                                            },
                                            "required": ["url"],
                                            "additionalProperties": True,
                                        },
                                    },
                                },
                                "required": ["field", "description", "references"],
                                "additionalProperties": True,
                            },
                        },
                    },
                    "required": ["section_id", "description", "fields"],
                    "additionalProperties": True,
                },
            },
            "references": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "title": {"type": "string"},
                        "section_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["url"],
                    "additionalProperties": True,
                },
            },
        },
        "required": ["title", "company_id", "executive_summary", "sections"],
        "additionalProperties": True,
    }

    llm_input = {
        "company_id": company_id,
        "snapshot_id": snapshot.id,
        "schema_id": snapshot.schema_id,
        "schema_version": snapshot.schema_version,
        "profile_sections": sections,
        "profile_meta": (snapshot.profile_json or {}).get("profile_meta", {}),
        "section_references": section_references,
    }

    try:
        response = await deps.llm.generate_structured(
            StructuredLLMRequest(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "Transform the profile data into a concise JSON report. "
                            "Make it read like a document, but keep strict JSON output. "
                            "Each field must include a plain-language description and references."
                        ),
                    ),
                    LLMMessage(
                        role="user",
                        content=(
                            "Convert this profile snapshot into the requested report schema:\n"
                            f"{json.dumps(llm_input, default=str)}"
                        ),
                    ),
                ],
                response_schema=report_schema,
                temperature=0.1,
                max_tokens=3500,
                task_type="synthesis",
            )
        )
        if isinstance(response.structured_output, dict):
            return response.structured_output
    except Exception as e:
        logger.warning("profile_report_generation_failed", company_id=company_id, error=str(e))

    # Deterministic fallback if LLM response is unavailable.
    fallback_sections = []
    for section_id, section_payload in sections.items():
        fields = []
        if isinstance(section_payload, dict):
            for field_name, field_value in section_payload.items():
                fields.append(
                    {
                        "field": field_name,
                        "value": field_value,
                        "description": f"Reported value for '{field_name}'.",
                        "references": [
                            {
                                "url": ref.get("url"),
                                "title": ref.get("title"),
                                "source_document_id": ref.get("source_document_id"),
                                "evidence_excerpt": ref.get("excerpt"),
                            }
                            for ref in section_references.get(section_id, [])[:3]
                            if ref.get("url")
                        ],
                    }
                )
        fallback_sections.append(
            {
                "section_id": section_id,
                "section_title": section_id.replace("_", " ").title(),
                "description": f"Summary for section '{section_id}'.",
                "fields": fields,
            }
        )

    return {
        "title": "Company Due Diligence Report",
        "company_id": company_id,
        "executive_summary": "Structured report generated from latest stored profile snapshot.",
        "sections": fallback_sections,
        "references": [],
    }


async def _build_profile_report_text(company_id: str, snapshot: Any, deps: Any) -> str:
    """Build a plain-text due diligence report."""
    report_json = await _build_profile_report(company_id, snapshot, deps)
    try:
        response = await deps.llm.generate(
            LLMRequest(
                messages=[
                    LLMMessage(
                        role="system",
                        content=(
                            "Write a professional due diligence report as plain text. "
                            "Use clear headings, concise paragraphs, bullet points for key findings, "
                            "and an explicit References section. Do not output JSON."
                        ),
                    ),
                    LLMMessage(
                        role="user",
                        content=(
                            "Convert this report JSON into a readable text document:\n"
                            f"{json.dumps(report_json, default=str)}"
                        ),
                    ),
                ],
                temperature=0.2,
                max_tokens=3500,
                task_type="synthesis",
            )
        )
        text = (response.content or "").strip()
        if text:
            return text
    except Exception as e:
        logger.warning("profile_report_text_generation_failed", company_id=company_id, error=str(e))

    # Deterministic fallback text document.
    lines: list[str] = [
        report_json.get("title", "Company Due Diligence Report"),
        f"Company ID: {company_id}",
        "",
        "Executive Summary",
        report_json.get("executive_summary", "No summary available."),
        "",
    ]

    for section in report_json.get("sections", []):
        lines.append(section.get("section_title") or section.get("section_id", "Section"))
        lines.append(section.get("description", ""))
        for field in section.get("fields", []):
            lines.append(f"- {field.get('field', 'field')}: {field.get('description', '')}")
            value = field.get("value")
            if value is not None:
                lines.append(f"  Value: {value}")
        lines.append("")

    lines.append("References")
    for ref in report_json.get("references", []):
        url = ref.get("url")
        title = ref.get("title", "")
        if url:
            lines.append(f"- {title} {url}".strip())

    return "\n".join(lines).strip()


@router.get("/{company_id}")
async def get_profile(company_id: str, request: Request) -> dict:
    """Get the latest profile snapshot for a company.

    Args:
        company_id: The canonical company ID (e.g., company:www_example_com).
    """
    deps = request.app.state.deps
    normalized_company_id = await _resolve_company_id(company_id, deps)
    snapshot = await deps.profile_repo.get_latest(normalized_company_id)
    if not snapshot:
        return {
            "company_id": normalized_company_id,
            "profile": None,
            "message": "No profile found",
        }

    return {
        "company_id": normalized_company_id,
        "snapshot_id": snapshot.id,
        "schema_id": snapshot.schema_id,
        "schema_version": snapshot.schema_version,
        "profile": snapshot.profile_json,
        "coverage_summary": snapshot.coverage_summary,
        "retrieval_profile": snapshot.retrieval_profile,
        "created_at": snapshot.created_at.isoformat() if snapshot.created_at else None,
        "is_latest": snapshot.is_latest,
    }


@router.get("/{company_id}/report")
async def get_profile_report(company_id: str, request: Request) -> PlainTextResponse:
    """Get a plain-text due diligence report for the latest profile snapshot."""
    deps = request.app.state.deps
    normalized_company_id = await _resolve_company_id(company_id, deps)
    snapshot = await deps.profile_repo.get_latest(normalized_company_id)
    if not snapshot:
        return PlainTextResponse(
            content=f"No profile found for {normalized_company_id}",
            status_code=404,
        )

    report_text = await _build_profile_report_text(normalized_company_id, snapshot, deps)
    return PlainTextResponse(content=report_text, media_type="text/plain")


@router.get("/{company_id}/evidence")
async def get_evidence(
    company_id: str,
    request: Request,
    section_id: str | None = None,
    field_id: str | None = None,
    limit: int = 50,
) -> dict:
    """Get evidence for a company with optional filters.

    Supports filtering by section_id, field_id, and limit.
    """
    deps = request.app.state.deps
    normalized_company_id = normalize_company_id(company_id)
    candidate_ids = _company_id_aliases(normalized_company_id)
    logger.info(
        "evidence_route_start",
        input_company_id=company_id,
        normalized_company_id=normalized_company_id,
        candidate_ids=candidate_ids,
        section_id=section_id,
        field_id=field_id,
        limit=limit,
    )

    merged: list[Any] = []
    seen_ids: set[str] = set()
    for cid in candidate_ids:
        try:
            rows = await deps.evidence_repo.find_by_company(
                company_id=cid,
                section_id=section_id,
                field_id=field_id,
                limit=limit,
            )
            logger.info(
                "evidence_route_alias_result",
                candidate_company_id=cid,
                rows=len(rows),
            )
        except Exception as e:
            logger.error(
                "evidence_route_alias_failed",
                candidate_company_id=cid,
                error=str(e),
            )
            continue
        for row in rows:
            rid = row.id or ""
            if rid and rid in seen_ids:
                continue
            if rid:
                seen_ids.add(rid)
            merged.append(row)

    # Keep most recent first and respect limit after merge.
    merged.sort(key=lambda e: e.retrieved_at, reverse=True)
    evidence = merged[:limit]

    # Prefer alias that actually returned data, else normalized input.
    resolved_company_id = next(
        (cid for cid in candidate_ids if any(e.company_id == cid for e in evidence)),
        normalized_company_id,
    )
    logger.info(
        "evidence_route_done",
        resolved_company_id=resolved_company_id,
        merged_count=len(merged),
        returned_count=len(evidence),
    )
    return {
        "company_id": resolved_company_id,
        "evidence": [e.model_dump(mode="json") for e in evidence],
        "count": len(evidence),
    }
