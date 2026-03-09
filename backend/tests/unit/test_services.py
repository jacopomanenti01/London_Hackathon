from src.utils.url import normalize_url


def test_normalize_url_adds_scheme():
    assert normalize_url("www.acme.com") == "https://www.acme.com"


def test_normalize_url_preserves_https():
    assert normalize_url("https://acme.com") == "https://acme.com"


def test_normalize_url_preserves_http():
    assert normalize_url("http://acme.com") == "http://acme.com"


def test_normalize_url_strips_trailing_slash():
    assert normalize_url("https://acme.com/") == "https://acme.com"


def test_normalize_url_lowercases():
    assert normalize_url("https://ACME.COM") == "https://acme.com"


def test_normalize_url_strips_path():
    result = normalize_url("https://acme.com/about")
    assert result == "https://acme.com"
