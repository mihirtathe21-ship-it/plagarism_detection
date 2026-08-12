from core import web_search


def test_search_web_traverses_multiple_search_providers(monkeypatch):
    monkeypatch.setattr(web_search, "search_wikipedia", lambda query, num, log=None: [
        {"url": "https://wiki.example/article-a", "snippet": "wiki snippet"}
    ])
    monkeypatch.setattr(web_search, "search_duckduckgo", lambda query, num, log=None: [
        {"url": "https://ddg.example/article-b", "snippet": "ddg snippet"}
    ])
    monkeypatch.setattr(web_search, "search_brave", lambda query, num, log=None: [
        {"url": "https://brave.example/article-c", "snippet": "brave snippet"}
    ])
    monkeypatch.setattr(web_search, "search_google", lambda query, num, log=None: [
        {"url": "https://google.example/article-d", "snippet": "google snippet"}
    ])
    monkeypatch.setattr(web_search, "search_bing", lambda query, num, log=None: [
        {"url": "https://bing.example/article-e", "snippet": "bing snippet"}
    ])

    results = web_search.search_web("machine learning", num=6)
    urls = {item["url"] for item in results}

    assert "https://wiki.example/article-a" in urls
    assert "https://ddg.example/article-b" in urls
    assert "https://brave.example/article-c" in urls
    assert "https://google.example/article-d" in urls
