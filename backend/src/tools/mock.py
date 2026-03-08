import json
import logging
from pathlib import Path
from typing import Any

from .base import BaseSearchTool, SearchResult

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"

# Maps normalized URL domains to fixture directory names
_URL_TO_FIXTURE = {
    "acme": "acme_corp",
    "globex": "globex_tech",
    "initech": "initech_consulting",
    "darkstar": "darkstar_industries",
}

# Track which wave has been served per company (simulates incremental updates)
_wave_tracker: dict[str, int] = {}


def _match_fixture(query: str) -> str | None:
    query_lower = query.lower()
    for keyword, fixture_name in _URL_TO_FIXTURE.items():
        if keyword in query_lower:
            return fixture_name
    return None


def _load_wave(fixture_name: str) -> dict[str, list[dict[str, Any]]]:
    wave_num = _wave_tracker.get(fixture_name, 1)
    wave_file = FIXTURES_DIR / fixture_name / f"wave_{wave_num}.json"

    if not wave_file.exists():
        logger.info("No wave_%d for %s, returning empty", wave_num, fixture_name)
        return {}

    with open(wave_file) as f:
        data = json.load(f)
    return data


class MockSearchTool(BaseSearchTool):
    name = "mock"

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        fixture_name = _match_fixture(query)
        if not fixture_name:
            logger.warning("No fixture match for query: %s", query)
            return []

        wave_data = _load_wave(fixture_name)

        # Find which section this query relates to by checking all sections
        results: list[SearchResult] = []
        for section_name, section_results in wave_data.items():
            # Include results from any section that has content
            for item in section_results:
                results.append(SearchResult(
                    title=item["title"],
                    url=item["url"],
                    content=item["content"],
                    source=item.get("source", "mock"),
                ))

        logger.info(
            "MockSearchTool: query=%s fixture=%s wave=%d results=%d",
            query[:60], fixture_name, _wave_tracker.get(fixture_name, 1), len(results),
        )
        return results[:max_results]


# Map section names from schema to fixture section keys, with keyword fallbacks
_SECTION_KEYWORDS: dict[str, list[str]] = {
    "company_overview": ["overview", "background", "basic", "company information", "founded", "headquarters"],
    "key_personnel": ["personnel", "executive", "board", "leadership", "people", "ceo", "cfo", "cto"],
    "financials": ["financial", "revenue", "profit", "funding", "earnings", "fiscal"],
    "esg": ["esg", "environmental", "social", "governance", "sustainability", "carbon"],
    "legal_compliance": ["legal", "compliance", "lawsuit", "regulatory", "sanction", "litigation"],
    "supply_chain_risks": ["supply chain", "supplier", "customer", "geographic risk", "concentration"],
    "certifications": ["certification", "standard", "iso", "accreditation"],
}


class MockSectionSearchTool(BaseSearchTool):
    """Returns section-specific mock results based on query content."""
    name = "mock_section"

    async def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        fixture_name = _match_fixture(query)
        if not fixture_name:
            return []

        wave_data = _load_wave(fixture_name)
        query_lower = query.lower()

        # Match query to section using keyword mapping
        best_section = None
        best_score = 0
        for section_name, keywords in _SECTION_KEYWORDS.items():
            if section_name not in wave_data:
                continue
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > best_score:
                best_score = score
                best_section = section_name

        if best_section and wave_data.get(best_section):
            items = wave_data[best_section]
        else:
            # Fallback: return all results
            items = []
            for section_results in wave_data.values():
                items.extend(section_results)

        results = [
            SearchResult(
                title=item["title"],
                url=item["url"],
                content=item["content"],
                source=item.get("source", "mock"),
            )
            for item in items
        ]
        return results[:max_results]


def advance_wave(company_url: str) -> int:
    """Advance to the next wave for a company. Returns the new wave number."""
    for keyword, fixture_name in _URL_TO_FIXTURE.items():
        if keyword in company_url.lower():
            current = _wave_tracker.get(fixture_name, 1)
            _wave_tracker[fixture_name] = current + 1
            logger.info("Advanced %s to wave %d", fixture_name, current + 1)
            return current + 1
    return 1


def reset_waves():
    """Reset all wave tracking."""
    _wave_tracker.clear()
