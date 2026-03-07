"""Node: Synthesize profile from claims and evidence using LLM."""

from __future__ import annotations

import json
from typing import Any

from ...domain.schema import ProfileSchema
from ...logging import get_logger
from ...providers.llm.base import LLMAdapter
from ...providers.llm.models import LLMMessage, LLMRequest
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

    # Build claims context
    claims_text = json.dumps(state.extracted_claims, indent=2, default=str)

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

    try:
        response = await llm.generate(
            LLMRequest(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=0.1,
                max_tokens=4000,
                task_type="synthesis",
            )
        )

        content = response.content.strip()
        start = content.find("{")
        end = content.rfind("}") + 1
        if start >= 0 and end > start:
            profile_draft = json.loads(content[start:end])
        else:
            profile_draft = {"error": "Failed to parse profile", "raw": content[:500]}

    except Exception as e:
        logger.error("profile_synthesis_failed", error=str(e))
        profile_draft = {"error": str(e)}

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
