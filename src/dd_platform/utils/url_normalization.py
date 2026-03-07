"""URL normalization and canonical company identity resolution.

The canonical company identifier is derived from the normalized main URL host.
Example: https://www.company.com/ -> company:www.company.com
"""

from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse

import tldextract

from ..domain.company import CompanyRef


_TRACKING_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "source", "mc_cid", "mc_eid",
})


class InvalidCompanyUrlError(ValueError):
    """Raised when a company URL is invalid or non-normalizable."""

    def __init__(self, url: str, reason: str = "Invalid URL") -> None:
        self.url = url
        self.reason = reason
        super().__init__(f"{reason}: {url}")


def normalize_url(raw_url: str) -> str:
    """Normalize a URL by lowercasing, stripping tracking params, fragments, etc."""
    url = raw_url.strip()

    # Add scheme if missing
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    parsed = urlparse(url)

    # Lowercase scheme and host
    scheme = "https"
    netloc = parsed.hostname or ""
    netloc = netloc.lower().rstrip(".")

    if not netloc:
        raise InvalidCompanyUrlError(raw_url, "No host found")

    # Strip default ports
    port = parsed.port
    if port and port not in (80, 443):
        netloc = f"{netloc}:{port}"

    # Strip tracking params from query
    if parsed.query:
        params = parsed.query.split("&")
        filtered = [p for p in params if p.split("=")[0] not in _TRACKING_PARAMS]
        query = "&".join(filtered)
    else:
        query = ""

    # Normalize path — strip trailing slash unless it's just "/"
    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    # Rebuild without fragment
    normalized = urlunparse((scheme, netloc, path, "", query, ""))
    return normalized


def extract_host(url: str) -> str:
    """Extract normalized hostname from URL."""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    return host.lower().rstrip(".")


def extract_root_domain(url: str) -> str:
    """Extract the root domain (e.g., example.com) from a URL."""
    extracted = tldextract.extract(url)
    if not extracted.domain or not extracted.suffix:
        raise InvalidCompanyUrlError(url, "Cannot extract root domain")
    return f"{extracted.domain}.{extracted.suffix}"


def make_canonical_id(host: str) -> str:
    """Create a SurrealDB-compatible canonical company ID."""
    # SurrealDB record IDs use the format table:id
    # We use backtick-wrapped ID for hosts with dots
    safe_host = host.replace(".", "_")
    return f"company:{safe_host}"


def resolve_company_identity(raw_url: str) -> CompanyRef:
    """Full URL normalization and company identity resolution.

    Args:
        raw_url: The raw company URL input.

    Returns:
        CompanyRef with canonical ID, host, URL, and root domain.

    Raises:
        InvalidCompanyUrlError: If the URL is not valid or normalizable.
    """
    # Basic validation
    if not raw_url or not raw_url.strip():
        raise InvalidCompanyUrlError(raw_url, "Empty URL")

    # Reject obviously non-company URLs
    _reject_non_company_url(raw_url)

    canonical_url = normalize_url(raw_url)
    canonical_host = extract_host(canonical_url)
    root_domain = extract_root_domain(canonical_url)
    canonical_id = make_canonical_id(canonical_host)

    return CompanyRef(
        canonical_id=canonical_id,
        canonical_host=canonical_host,
        canonical_url=canonical_url,
        root_domain=root_domain,
    )


def _reject_non_company_url(url: str) -> None:
    """Reject obviously non-company URLs."""
    url_lower = url.lower().strip()

    # Reject localhost, IP-only, common non-company patterns
    reject_patterns = [
        r"^(https?://)?localhost",
        r"^(https?://)?127\.",
        r"^(https?://)?0\.0\.0\.0",
        r"^(https?://)?192\.168\.",
        r"^(https?://)?10\.",
    ]
    for pattern in reject_patterns:
        if re.match(pattern, url_lower):
            raise InvalidCompanyUrlError(url, "Non-company URL (local/private)")
