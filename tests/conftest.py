"""Shared test fixtures for the DD Platform test suite."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest

from dd_platform.domain.claim import Claim, ClaimStatus
from dd_platform.domain.company import Company, CompanyRef, CompanyStatus, DomainAlias
from dd_platform.domain.evidence import Evidence, FreshnessStatus, SourceDocument, SourceProvider, SourceType
from dd_platform.domain.profile import ProfileSection, ProfileSnapshot
from dd_platform.domain.retrieval import RetrievalContext, RetrievalResult
from dd_platform.domain.schema import FieldDefinition, ProfileSchema, SectionDefinition


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------

NOW = datetime(2026, 3, 7, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Company fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_company_ref() -> CompanyRef:
    return CompanyRef(
        canonical_id="company:www_example_com",
        canonical_host="www.example.com",
        canonical_url="https://www.example.com",
        root_domain="example.com",
        display_name="Example Corp",
    )


@pytest.fixture()
def sample_company() -> Company:
    return Company(
        id="company:www_example_com",
        canonical_url="https://www.example.com",
        canonical_host="www.example.com",
        root_domain="example.com",
        display_name="Example Corp",
        status=CompanyStatus.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )


@pytest.fixture()
def sample_domain_alias() -> DomainAlias:
    return DomainAlias(
        id="domain_alias:abc123",
        company_id="company:www_example_com",
        alias_host="example.co.uk",
        alias_url="https://example.co.uk",
        reason="redirect",
        created_at=NOW,
    )


# ---------------------------------------------------------------------------
# Schema fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_field_definition() -> FieldDefinition:
    return FieldDefinition(
        id="legal_name",
        title="Legal Name",
        data_type="string",
        required=True,
        ttl_days=180,
        confidence_threshold=0.7,
    )


@pytest.fixture()
def sample_section_definition(sample_field_definition: FieldDefinition) -> SectionDefinition:
    return SectionDefinition(
        id="company_identity",
        title="Company Identity",
        required=True,
        freshness_days=180,
        fields=[
            sample_field_definition,
            FieldDefinition(id="headquarters", data_type="object", required=False, ttl_days=180),
            FieldDefinition(id="employee_estimate", data_type="string", required=False, ttl_days=90),
        ],
    )


@pytest.fixture()
def sample_schema(sample_section_definition: SectionDefinition) -> ProfileSchema:
    return ProfileSchema(
        schema_id="due_diligence_v1",
        version=1,
        is_active=True,
        sections=[
            sample_section_definition,
            SectionDefinition(
                id="compliance_and_risk",
                title="Compliance and Risk",
                required=True,
                freshness_days=30,
                fields=[
                    FieldDefinition(id="sanctions_exposure", data_type="string", ttl_days=30),
                    FieldDefinition(id="adverse_media_summary", data_type="string", ttl_days=30),
                ],
            ),
        ],
        notes="Test schema",
    )


# ---------------------------------------------------------------------------
# Evidence fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_source_document() -> SourceDocument:
    return SourceDocument(
        id="source_document:sd_001",
        company_id="company:www_example_com",
        url="https://www.example.com/about",
        title="About Example Corp",
        provider=SourceProvider.TAVILY,
        source_type=SourceType.OFFICIAL_SITE,
        retrieved_at=NOW,
        content_text="Example Corp is a global leader in widgets.",
    )


@pytest.fixture()
def sample_evidence() -> Evidence:
    return Evidence(
        id="evidence:ev_001",
        company_id="company:www_example_com",
        source_document_id="source_document:sd_001",
        section_id="company_identity",
        field_id="legal_name",
        excerpt="Example Corp, legally registered as Example Corporation Ltd.",
        normalized_fact_candidate="Example Corporation Ltd.",
        confidence=0.85,
        retrieved_at=NOW,
    )


@pytest.fixture()
def sample_evidence_list(sample_evidence: Evidence) -> list[Evidence]:
    return [
        sample_evidence,
        Evidence(
            id="evidence:ev_002",
            company_id="company:www_example_com",
            source_document_id="source_document:sd_001",
            section_id="company_identity",
            field_id="headquarters",
            excerpt="Headquartered in London, United Kingdom.",
            normalized_fact_candidate="London, United Kingdom",
            confidence=0.80,
            retrieved_at=NOW,
        ),
        Evidence(
            id="evidence:ev_003",
            company_id="company:www_example_com",
            source_document_id="source_document:sd_002",
            section_id="compliance_and_risk",
            field_id="sanctions_exposure",
            excerpt="No known sanctions exposure as of 2026.",
            confidence=0.70,
            retrieved_at=NOW,
        ),
    ]


# ---------------------------------------------------------------------------
# Claim fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_claim() -> Claim:
    return Claim(
        id="claim:cl_001",
        company_id="company:www_example_com",
        section_id="company_identity",
        field_id="legal_name",
        value="Example Corporation Ltd.",
        value_type="string",
        confidence=0.9,
        status=ClaimStatus.ACTIVE,
        first_seen_at=NOW,
        last_verified_at=NOW,
        derived_from_evidence_count=2,
        schema_version=1,
    )


@pytest.fixture()
def sample_claims(sample_claim: Claim) -> list[Claim]:
    return [
        sample_claim,
        Claim(
            id="claim:cl_002",
            company_id="company:www_example_com",
            section_id="company_identity",
            field_id="headquarters",
            value="London, United Kingdom",
            value_type="string",
            confidence=0.8,
            status=ClaimStatus.ACTIVE,
            first_seen_at=NOW,
            last_verified_at=NOW,
        ),
    ]


# ---------------------------------------------------------------------------
# Retrieval fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_retrieval_result() -> RetrievalResult:
    return RetrievalResult(
        result_type="evidence",
        score=0.85,
        score_breakdown={"keyword": 0.5, "graph_proximity": 0.35},
        text_snippet="Example Corp is a global leader in widgets, headquartered in London.",
        section_id="company_identity",
        field_id="legal_name",
        freshness_status="fresh",
        contradiction_flag=False,
        provenance_path=["evidence:ev_001", "source_document:sd_001"],
        source_url="https://www.example.com/about",
        retrieval_profile="graph_hybrid_expanded",
    )


@pytest.fixture()
def sample_retrieval_results(sample_retrieval_result: RetrievalResult) -> list[RetrievalResult]:
    return [
        sample_retrieval_result,
        RetrievalResult(
            result_type="claim",
            score=0.75,
            text_snippet="Example Corporation Ltd.",
            section_id="company_identity",
            field_id="legal_name",
            retrieval_profile="graph_hybrid_expanded",
        ),
        RetrievalResult(
            result_type="evidence",
            score=0.65,
            text_snippet="No sanctions found for Example Corp.",
            section_id="compliance_and_risk",
            field_id="sanctions_exposure",
            retrieval_profile="graph_hybrid_expanded",
        ),
    ]


@pytest.fixture()
def sample_retrieval_context(
    sample_retrieval_results: list[RetrievalResult],
) -> RetrievalContext:
    return RetrievalContext(
        company_id="company:www_example_com",
        retrieval_profile="graph_hybrid_expanded",
        results=sample_retrieval_results,
        total_candidates=10,
        selected_count=3,
        sections_covered=["company_identity", "compliance_and_risk"],
        has_contradictions=False,
    )


# ---------------------------------------------------------------------------
# Profile fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_profile_snapshot() -> ProfileSnapshot:
    return ProfileSnapshot(
        id="profile_snapshot:ps_001",
        company_id="company:www_example_com",
        schema_id="due_diligence_v1",
        schema_version=1,
        profile_json={
            "company_identity": {
                "legal_name": {"value": "Example Corporation Ltd.", "confidence": 0.9},
                "headquarters": {"value": "London, United Kingdom", "confidence": 0.8},
            },
            "compliance_and_risk": {
                "sanctions_exposure": {"value": "No known exposure", "confidence": 0.7},
            },
        },
        coverage_summary={"total_fields": 10, "populated_fields": 3},
        retrieval_profile="graph_hybrid_expanded",
        created_at=NOW,
        created_by_run_id="agent_run:run_001",
        is_latest=True,
    )
