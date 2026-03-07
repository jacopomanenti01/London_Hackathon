"""Unit tests for URL normalization and company identity resolution."""

from __future__ import annotations

import pytest

from dd_platform.utils.url_normalization import (
    InvalidCompanyUrlError,
    extract_host,
    extract_root_domain,
    make_canonical_id,
    normalize_url,
    resolve_company_identity,
)


# ---------------------------------------------------------------------------
# normalize_url
# ---------------------------------------------------------------------------


class TestNormalizeUrl:
    """Tests for the normalize_url function."""

    def test_basic_url(self) -> None:
        result = normalize_url("https://www.example.com")
        assert result == "https://www.example.com/"

    def test_adds_https_scheme(self) -> None:
        result = normalize_url("www.example.com")
        assert result.startswith("https://")

    def test_strips_trailing_slash(self) -> None:
        result = normalize_url("https://www.example.com/about/")
        assert result.endswith("/about")

    def test_preserves_root_slash(self) -> None:
        result = normalize_url("https://www.example.com/")
        assert result == "https://www.example.com/"

    def test_lowercases_host(self) -> None:
        result = normalize_url("https://WWW.EXAMPLE.COM/About")
        host = extract_host(result)
        assert host == "www.example.com"

    def test_strips_fragment(self) -> None:
        result = normalize_url("https://example.com/about#section")
        assert "#" not in result

    def test_strips_tracking_params(self) -> None:
        result = normalize_url("https://example.com?utm_source=google&real_param=1")
        assert "utm_source" not in result
        assert "real_param=1" in result

    def test_strips_all_tracking_params(self) -> None:
        result = normalize_url("https://example.com?utm_source=a&utm_medium=b&fbclid=123")
        assert "utm_source" not in result
        assert "fbclid" not in result

    def test_preserves_non_default_port(self) -> None:
        result = normalize_url("https://example.com:8443/api")
        assert ":8443" in result

    def test_strips_default_http_port(self) -> None:
        result = normalize_url("http://example.com:80/page")
        assert ":80" not in result

    def test_raises_on_empty_host(self) -> None:
        with pytest.raises(InvalidCompanyUrlError):
            normalize_url("https://")


# ---------------------------------------------------------------------------
# extract_host
# ---------------------------------------------------------------------------


class TestExtractHost:
    """Tests for the extract_host function."""

    def test_simple(self) -> None:
        assert extract_host("https://www.example.com/page") == "www.example.com"

    def test_strips_trailing_dot(self) -> None:
        assert extract_host("https://example.com.") == "example.com"

    def test_lowercases(self) -> None:
        assert extract_host("https://EXAMPLE.COM") == "example.com"


# ---------------------------------------------------------------------------
# extract_root_domain
# ---------------------------------------------------------------------------


class TestExtractRootDomain:
    """Tests for the extract_root_domain function."""

    def test_simple(self) -> None:
        assert extract_root_domain("https://www.example.com") == "example.com"

    def test_subdomain(self) -> None:
        assert extract_root_domain("https://shop.example.co.uk") == "example.co.uk"

    def test_raises_on_invalid(self) -> None:
        with pytest.raises(InvalidCompanyUrlError):
            extract_root_domain("https://localhost")


# ---------------------------------------------------------------------------
# make_canonical_id
# ---------------------------------------------------------------------------


class TestMakeCanonicalId:
    """Tests for the make_canonical_id function."""

    def test_dots_replaced(self) -> None:
        result = make_canonical_id("www.example.com")
        assert result == "company:www_example_com"

    def test_no_dots(self) -> None:
        result = make_canonical_id("localhost")
        assert result == "company:localhost"


# ---------------------------------------------------------------------------
# resolve_company_identity
# ---------------------------------------------------------------------------


class TestResolveCompanyIdentity:
    """Tests for the full identity resolution pipeline."""

    def test_full_resolution(self) -> None:
        ref = resolve_company_identity("https://www.example.com/about?utm_source=test")
        assert ref.canonical_id == "company:www_example_com"
        assert ref.canonical_host == "www.example.com"
        assert ref.root_domain == "example.com"
        assert "utm_source" not in ref.canonical_url

    def test_bare_domain(self) -> None:
        ref = resolve_company_identity("example.com")
        assert ref.canonical_host == "example.com"
        assert ref.root_domain == "example.com"

    def test_rejects_empty(self) -> None:
        with pytest.raises(InvalidCompanyUrlError, match="Empty URL"):
            resolve_company_identity("")

    def test_rejects_whitespace_only(self) -> None:
        with pytest.raises(InvalidCompanyUrlError, match="Empty URL"):
            resolve_company_identity("   ")

    def test_rejects_localhost(self) -> None:
        with pytest.raises(InvalidCompanyUrlError, match="Non-company"):
            resolve_company_identity("http://localhost:3000")

    def test_rejects_private_ip(self) -> None:
        with pytest.raises(InvalidCompanyUrlError, match="Non-company"):
            resolve_company_identity("http://192.168.1.1")

    def test_rejects_loopback(self) -> None:
        with pytest.raises(InvalidCompanyUrlError, match="Non-company"):
            resolve_company_identity("http://127.0.0.1:8080")
