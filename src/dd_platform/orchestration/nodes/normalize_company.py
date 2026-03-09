"""Node: Normalize company URL into canonical identity."""

from __future__ import annotations

from ...logging import get_logger
from ...utils.url_normalization import resolve_company_identity
from ..state import BuildProfileState, WorkflowStage

logger = get_logger(__name__)


async def normalize_company(state: BuildProfileState) -> dict:
    """Normalize the company URL into canonical identity.

    Resolves the raw company URL into canonical ID, host, and root domain.
    """
    logger.info("node_normalize_company", url=state.company_url)

    try:
        ref = resolve_company_identity(state.company_url)
        return {
            "company_id": ref.canonical_id,
            "canonical_host": ref.canonical_host,
            "canonical_url": ref.canonical_url,
            "root_domain": ref.root_domain,
            "current_stage": WorkflowStage.COMPANY_RESOLVED,
        }
    except Exception as e:
        logger.error("normalize_company_failed", error=str(e))
        return {
            "current_stage": WorkflowStage.FAILED,
            "errors": state.errors + [f"URL normalization failed: {e}"],
        }
