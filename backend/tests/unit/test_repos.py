from src.utils.url import url_to_id


def test_url_to_id_basic():
    result = url_to_id("https://acme.com")
    assert ":" not in result
    assert "/" not in result
    assert "." not in result


def test_url_to_id_consistency():
    assert url_to_id("https://acme.com") == url_to_id("https://acme.com")


def test_url_to_id_different_urls():
    assert url_to_id("https://acme.com") != url_to_id("https://other.com")
