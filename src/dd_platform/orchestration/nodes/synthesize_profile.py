"""Node: Synthesize profile from claims and evidence using LLM."""

from __future__ import annotations

import json
from typing import Any

from ...domain.schema import ProfileSchema
from ...logging import get_logger
from ...providers.llm.base import LLMAdapter
from ...providers.llm.models import LLMMessage, StructuredLLMRequest
from ..state import BuildProfileState, WorkflowStage

logger = get_logger(__name__)


async def synthesize_profile(
    state: BuildProfileState,
    llm: LLMAdapter,
    schema: ProfileSchema,
) -> dict:
    """Synthesize a complete profile from extracted claims.

    Uses the active schema to structure the profile output.
    Evidence-backed population takes priority over narrative generation.
    """
    logger.info(
        "node_synthesize_profile",
        company_id=state.company_id,
        claims_count=len(state.extracted_claims),
    )

    # Build schema description for the LLM
    schema_desc = _build_schema_description(schema)

    # Build compacted claims context to keep synthesis prompt size bounded.
    compact_claims = _compact_claims_for_synthesis(state.extracted_claims)
    claims_text = json.dumps(compact_claims, indent=2, default=str)
    response_schema = _build_synthesis_response_schema(schema)

    # Include existing profile data for context
    existing_text = ""
    if state.existing_profile:
        existing_text = f"\n\nExisting profile data (use if still relevant):\n{json.dumps(state.existing_profile, indent=2, default=str)}"

    prompt = f"""You are synthesizing a due diligence profile for the company at {state.canonical_host}.

Profile Schema:
{schema_desc}

Extracted Claims:
{claims_text}
{existing_text}

Instructions:
1. Populate each schema section and field using the extracted claims
2. If no claim covers a field, set it to null or "unknown"
3. Include a confidence score (0.0-1.0) for each populated field
4. Flag any contradictions you detect
5. For the profile_meta section, calculate an overall evidence_coverage_score

Return a JSON object matching the schema structure:
{{
  "sections": {{
    "section_id": {{
      "field_id": {{
        "value": "...",
        "confidence": 0.8,
        "sources": ["claim references"],
        "contradictions": []
      }}
    }}
  }},
  "profile_meta": {{
    "confidence_summary": "...",
    "evidence_coverage_score": 0.75,
    "open_questions": ["..."]
  }}
}}

Return ONLY valid JSON."""

    empty_profile = _build_empty_profile(schema)

    try:
        response = await llm.generate_structured(
            StructuredLLMRequest(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=0.1,
                max_tokens=4000,
                task_type="synthesis",
                response_schema=response_schema,
            )
        )

        if isinstance(response.structured_output, dict):
            profile_draft = response.structured_output
        else:
            content = (response.content or "").strip()
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                profile_draft = json.loads(content[start:end])
                if not isinstance(profile_draft, dict):
                    profile_draft = empty_profile
            else:
                logger.warning(
                    "profile_synthesis_empty_or_unparseable",
                    company_id=state.company_id,
                    content_preview=content[:200],
                )
                profile_draft = empty_profile

    except Exception as e:
        logger.error("profile_synthesis_failed", error=str(e))
        profile_draft = empty_profile

    logger.info(
        "profile_synthesized",
        company_id=state.company_id,
        has_sections="sections" in profile_draft,
    )

    return {
        "profile_draft": profile_draft,
        "current_stage": WorkflowStage.PROFILE_SYNTHESIZED,
    }


def _build_schema_description(schema: ProfileSchema) -> str:
    """Build a human-readable schema description for the LLM."""
    parts: list[str] = []
    for section in schema.sections:
        parts.append(f"\nSection: {section.id} ({section.title})")
        for field in section.fields:
            req = "REQUIRED" if field.required else "optional"
            parts.append(f"  - {field.id}: {field.data_type} [{req}]")
    return "\n".join(parts)


def _build_empty_profile(schema: ProfileSchema) -> dict[str, Any]:
    """Return a schema-shaped empty profile when synthesis output is unusable."""
    return {
        "sections": {section.id: {} for section in schema.sections},
        "profile_meta": {
            "confidence_summary": "No synthesized profile content returned by model.",
            "evidence_coverage_score": 0.0,
            "open_questions": [],
        },
    }


def _compact_claims_for_synthesis(claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate and trim extracted claims for a bounded synthesis prompt."""
    if not claims:
        return []

    sorted_claims = sorted(
        claims,
        key=lambda c: float(c.get("confidence", 0.0)),
        reverse=True,
    )

    per_field_limit = 3
    global_limit = 120
    field_counts: dict[tuple[str, str], int] = {}
    seen: set[tuple[str, str, str]] = set()
    compacted: list[dict[str, Any]] = []

    for claim in sorted_claims:
        section_id = str(claim.get("section_id", "unknown"))
        field_id = str(claim.get("field_id", "unknown"))
        value = str(claim.get("value", "")).strip()
        if not value:
            continue

        # Cap each value to avoid oversized prompts from long text claims.
        value = value[:600]
        dedupe_key = (section_id, field_id, value.lower())
        if dedupe_key in seen:
            continue

        field_key = (section_id, field_id)
        if field_counts.get(field_key, 0) >= per_field_limit:
            continue

        seen.add(dedupe_key)
        field_counts[field_key] = field_counts.get(field_key, 0) + 1
        compacted.append(
            {
                "section_id": section_id,
                "field_id": field_id,
                "value": value,
                "confidence": float(claim.get("confidence", 0.0)),
                "value_type": str(claim.get("value_type", "string")),
            }
        )

        if len(compacted) >= global_limit:
            break

    return compacted


def _build_synthesis_response_schema(schema: ProfileSchema) -> dict[str, Any]:
    """Build a permissive JSON schema for profile synthesis output."""
    section_properties: dict[str, Any] = {}
    for section in schema.sections:
        section_properties[section.id] = {
            "type": "object",
            "additionalProperties": True,
        }

    return {
        "type": "object",
        "properties": {
            "sections": {
                "type": "object",
                "properties": section_properties,
                "additionalProperties": True,
            },
            "profile_meta": {
                "type": "object",
                "properties": {
                    "confidence_summary": {"type": "string"},
                    "evidence_coverage_score": {"type": "number"},
                    "open_questions": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "additionalProperties": True,
            },
        },
        "required": ["sections", "profile_meta"],
        "additionalProperties": True,
    }
