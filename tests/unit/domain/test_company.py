"""Unit tests for company domain models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dd_platform.domain.company import Company, CompanyRef, CompanyStatus, DomainAlias


class TestCompanyRef:
    """Tests for CompanyRef model."""

    def test_creation(self, sample_company_ref: CompanyRef) -> None:
        assert sample_company_ref.canonical_id == "company:www_example_com"
        assert sample_company_ref.canonical_host == "www.example.com"
        assert sample_company_ref.root_domain == "example.com"

    def test_optional_display_name(self) -> None:
        ref = CompanyRef(
            canonical_id="company:test_com",
            canonical_host="test.com",
            canonical_url="https://test.com",
            root_domain="test.com",
        )
        assert ref.display_name is None


class TestCompany:
    """Tests for Company model."""

    def test_creation(self, sample_company: Company) -> None:
        assert sample_company.id == "company:www_example_com"
        assert sample_company.status == CompanyStatus.ACTIVE

    def test_default_status(self) -> None:
        company = Company(
            id="company:test_com",
            canonical_url="https://test.com",
            canonical_host="test.com",
            root_domain="test.com",
        )
        assert company.status == CompanyStatus.ACTIVE

    def test_serialization_roundtrip(self, sample_company: Company) -> None:
        data = sample_company.model_dump(mode="json")
        restored = Company(**data)
        assert restored.id == sample_company.id
        assert restored.canonical_host == sample_company.canonical_host


class TestDomainAlias:
    """Tests for DomainAlias model."""

    def test_creation(self, sample_domain_alias: DomainAlias) -> None:
        assert sample_domain_alias.alias_host == "example.co.uk"
        assert sample_domain_alias.company_id == "company:www_example_com"
