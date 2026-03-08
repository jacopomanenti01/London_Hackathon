from urllib.parse import urlparse


def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/").lower()


def url_to_id(url: str) -> str:
    return url.replace("://", "_").replace("/", "_").replace(".", "_").replace("-", "_").strip("_")


def name_to_id(name: str) -> str:
    """Convert an entity name to a valid SurrealDB record ID."""
    import re
    result = re.sub(r"[^a-zA-Z0-9]", "_", name).strip("_").lower()
    return re.sub(r"_+", "_", result)
