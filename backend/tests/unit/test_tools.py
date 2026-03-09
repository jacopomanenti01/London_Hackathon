from src.tools.base import SearchResult, BaseSearchTool


def test_search_result_model():
    r = SearchResult(title="Test", url="https://example.com", content="Hello", source="tavily")
    assert r.title == "Test"
    assert r.source == "tavily"


def test_search_result_defaults():
    r = SearchResult()
    assert r.title == ""
    assert r.url == ""


def test_base_search_tool_is_abstract():
    try:
        BaseSearchTool()
        assert False, "Should not be instantiable"
    except TypeError:
        pass
