"""Unit tests for claim domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dd_platform.domain.claim import Claim, ClaimContradiction, ClaimStatus


class TestClaim:
    """Tests for Claim model."""

    def test_creation(self, sample_claim: Claim) -> None:
        assert sample_claim.section_id == "company_identity"
        assert sample_claim.field_id == "legal_name"
        assert sample_claim.confidence == 0.9
        assert sample_claim.status == ClaimStatus.ACTIVE

    def test_default_status(self) -> None:
        claim = Claim(
            company_id="company:test_com",
            section_id="operations",
            field_id="industry",
            value="Technology",
        )
        assert claim.status == ClaimStatus.ACTIVE

    def test_confidence_validation_too_high(self) -> None:
        with pytest.raises(ValidationError):
            Claim(
                company_id="company:test_com",
                section_id="operations",
                field_id="industry",
                value="Tech",
                confidence=1.5,
            )

    def test_confidence_validation_too_low(self) -> None:
        with pytest.raises(ValidationError):
            Claim(
                company_id="company:test_com",
                section_id="operations",
                field_id="industry",
                value="Tech",
                confidence=-0.1,
            )


class TestClaimStatus:
    """Tests for ClaimStatus enum."""

    def test_all_statuses(self) -> None:
        assert ClaimStatus.ACTIVE == "active"
        assert ClaimStatus.SUPERSEDED == "superseded"
        assert ClaimStatus.CONTRADICTED == "contradicted"
        assert ClaimStatus.RETRACTED == "retracted"
        assert ClaimStatus.UNVERIFIED == "unverified"


class TestClaimContradiction:
    """Tests for ClaimContradiction model."""

    def test_creation(self) -> None:
        contradiction = ClaimContradiction(
            claim_a_id="claim:cl_001",
            claim_b_id="claim:cl_002",
            field_id="legal_name",
            description="Conflicting legal names found",
            severity="high",
        )
        assert contradiction.severity == "high"
        assert contradiction.claim_a_id == "claim:cl_001"
