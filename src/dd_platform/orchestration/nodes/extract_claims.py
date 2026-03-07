"""Node: Extract claims from evidence using LLM."""

from __future__ import annotations

import json
from typing import Any

from ...logging import get_logger
from ...providers.llm.base import LLMAdapter
from ...providers.llm.models import LLMMessage, LLMRequest
from ..state import BuildProfileState, WorkflowStage

logger = get_logger(__name__)


async def extract_claims(
    state: BuildProfileState,
    llm: LLMAdapter,
) -> dict:
    """Extract structured claims from evidence using LLM.

    Processes collected evidence through the LLM to extract
    normalized claims mapped to schema sections and fields.
    """
    logger.info(
        "node_extract_claims",
        company_id=state.company_id,
        evidence_count=len(state.new_evidence),
    )

    if not state.new_evidence:
        return {
            "extracted_claims": [],
            "current_stage": WorkflowStage.CLAIMS_EXTRACTED,
        }

    # Batch evidence for extraction
    claims: list[dict[str, Any]] = []

    # Process in batches
    batch_size = 5
    for i in range(0, len(state.new_evidence), batch_size):
        batch = state.new_evidence[i : i + batch_size]
        batch_claims = await _extract_batch(
            batch, state.company_id, state.canonical_host, state.schema_sections, llm
        )
        claims.extend(batch_claims)

    logger.info(
        "claims_extracted",
        company_id=state.company_id,
        total_claims=len(claims),
    )

    return {
        "extracted_claims": claims,
        "current_stage": WorkflowStage.CLAIMS_EXTRACTED,
    }


async def _extract_batch(
    evidence_batch: list[dict[str, Any]],
    company_id: str,
    company_host: str,
    schema_sections: list[str],
    llm: LLMAdapter,
) -> list[dict[str, Any]]:
    """Extract claims from a batch of evidence records."""
    evidence_text = "\n\n".join(
        f"Source ({e.get('provider', 'unknown')}): {e.get('excerpt', '')}"
        for e in evidence_batch
    )

    sections_str = ", ".join(schema_sections)

    prompt = f"""You are extracting structured due diligence claims about the company at {company_host}.

Given the following evidence fragments, extract specific factual claims. For each claim:
1. Identify which profile section it belongs to (from: {sections_str})
2. Identify the specific field (e.g., legal_name, headquarters, sanctions_exposure)
3. Extract the claim value
4. Rate your confidence (0.0-1.0) based on source quality

Evidence:
{evidence_text}

Return a JSON array of claims:
[
  {{
    "section_id": "section_name",
    "field_id": "field_name",
    "value": "the factual claim",
    "confidence": 0.8,
    "value_type": "string"
  }}
]

Return ONLY the JSON array. Extract as many relevant claims as possible."""

    try:
        response = await llm.generate(
            LLMRequest(
                messages=[LLMMessage(role="user", content=prompt)],
                temperature=0.1,
                max_tokens=2000,
                task_type="extraction",
            )
        )

        # Parse claims from response
        content = response.content.strip()
        # Find JSON array in response
        start = content.find("[")
        end = content.rfind("]") + 1
        if start >= 0 and end > start:
            raw_claims = json.loads(content[start:end])
            # Add company_id to each claim
            for claim in raw_claims:
                claim["company_id"] = company_id
            return raw_claims

    except Exception as e:
        logger.warning("claim_extraction_failed", error=str(e))

    return []
