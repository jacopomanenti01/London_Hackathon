"""Contract tests — validate domain model schemas and serialization contracts.

These tests ensure that domain models serialize/deserialize correctly and
that the JSON shapes meet the API contract expectations.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from dd_platform.domain.claim import Claim, ClaimStatus
from dd_platform.domain.company import Company, CompanyRef, CompanyStatus
from dd_platform.domain.evidence import Evidence, SourceDocument, SourceProvider, SourceType
from dd_platform.domain.profile import ProfileSection, ProfileSnapshot
from dd_platform.domain.retrieval import RetrievalContext, RetrievalResult
from dd_platform.domain.schema import FieldDefinition, ProfileSchema, SectionDefinition


@pytest.mark.contract
class TestCompanyContract:
    """Validate Company model serialization contract."""

    def test_company_json_keys(self, sample_company: Company) -> None:
        data = sample_company.model_dump(mode="json")
        required_keys = {"id", "canonical_url", "canonical_host", "root_domain", "status"}
        assert required_keys.issubset(data.keys())

    def test_company_status_serializes_as_string(self, sample_company: Company) -> None:
        data = sample_company.model_dump(mode="json")
        assert isinstance(data["status"], str)
        assert data["status"] == "active"

    def test_company_ref_required_fields(self) -> None:
        """CompanyRef requires canonical_id, canonical_host, canonical_url, root_domain."""
        with pytest.raises(Exception):  # ValidationError
            CompanyRef()  # type: ignore[call-arg]


@pytest.mark.contract
class TestClaimContract:
    """Validate Claim model serialization contract."""

    def test_claim_json_keys(self, sample_claim: Claim) -> None:
        data = sample_claim.model_dump(mode="json")
        required_keys = {
            "company_id", "section_id", "field_id",
            "value", "confidence", "status",
        }
        assert required_keys.issubset(data.keys())

    def test_claim_status_serializes(self, sample_claim: Claim) -> None:
        data = sample_claim.model_dump(mode="json")
        assert data["status"] in [s.value for s in ClaimStatus]

    def test_claim_confidence_range(self, sample_claim: Claim) -> None:
        data = sample_claim.model_dump(mode="json")
        assert 0.0 <= data["confidence"] <= 1.0


@pytest.mark.contract
class TestEvidenceContract:
    """Validate Evidence model serialization contract."""

    def test_evidence_json_keys(self, sample_evidence: Evidence) -> None:
        data = sample_evidence.model_dump(mode="json")
        required_keys = {"company_id", "source_document_id", "excerpt", "confidence"}
        assert required_keys.issubset(data.keys())

    def test_source_document_json_keys(self, sample_source_document: SourceDocument) -> None:
        data = sample_source_document.model_dump(mode="json")
        required_keys = {"company_id", "url", "provider"}
        assert required_keys.issubset(data.keys())

    def test_provider_serializes_as_string(self, sample_source_document: SourceDocument) -> None:
        data = sample_source_document.model_dump(mode="json")
        assert isinstance(data["provider"], str)
        assert data["provider"] in [p.value for p in SourceProvider]


@pytest.mark.contract
class TestProfileSnapshotContract:
    """Validate ProfileSnapshot serialization contract."""

    def test_snapshot_json_keys(self, sample_profile_snapshot: ProfileSnapshot) -> None:
        data = sample_profile_snapshot.model_dump(mode="json")
        required_keys = {
            "company_id", "schema_id", "schema_version",
            "profile_json", "is_latest",
        }
        assert required_keys.issubset(data.keys())

    def test_profile_json_is_dict(self, sample_profile_snapshot: ProfileSnapshot) -> None:
        data = sample_profile_snapshot.model_dump(mode="json")
        assert isinstance(data["profile_json"], dict)


@pytest.mark.contract
class TestRetrievalResultContract:
    """Validate RetrievalResult serialization contract."""

    def test_result_json_keys(self, sample_retrieval_result: RetrievalResult) -> None:
        data = sample_retrieval_result.model_dump(mode="json")
        required_keys = {"result_type", "score", "text_snippet"}
        assert required_keys.issubset(data.keys())


@pytest.mark.contract
class TestSchemaContract:
    """Validate ProfileSchema serialization contract."""

    def test_schema_json_roundtrip(self, sample_schema: ProfileSchema) -> None:
        data = sample_schema.model_dump(mode="json")
        restored = ProfileSchema(**data)
        assert restored.schema_id == sample_schema.schema_id
        assert len(restored.sections) == len(sample_schema.sections)

    def test_field_definition_roundtrip(self, sample_field_definition: FieldDefinition) -> None:
        data = sample_field_definition.model_dump(mode="json")
        restored = FieldDefinition(**data)
        assert restored.id == sample_field_definition.id
        assert restored.required == sample_field_definition.required
