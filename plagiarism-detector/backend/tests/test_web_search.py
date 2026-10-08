from core import web_search


def test_extract_document_title_prefers_pdf_metadata():
    title = web_search.extract_document_title(
        "A different first line\nwith body text",
        {"title": "A Research Paper Title"},
    )

    assert title == "A Research Paper Title"


def test_extract_arxiv_id_from_filename():
    assert web_search.extract_arxiv_id({"filename": "1706.03762v7.pdf"}) == "1706.03762v7"


def test_search_openalex_returns_paper_url(monkeypatch):
    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": [{
                    "title": "A Research Paper Title",
                    "doi": "https://doi.org/10.1234/example",
                    "best_oa_location": {"pdf_url": "https://example.org/paper.pdf"},
                    "authorships": [],
                }]
            }

    class Session:
        def get(self, *args, **kwargs):
            return Response()

    monkeypatch.setattr(web_search, "_get_session", lambda: Session())

    results = web_search.search_openalex("A Research Paper Title")

    assert results[0]["url"] == "https://example.org/paper.pdf"
    assert results[0]["source_type"] == "scholarly_paper"


def test_check_keeps_identified_paper_when_page_cannot_be_fetched(monkeypatch):
    from core import semantic_model

    monkeypatch.setattr(
        semantic_model,
        "get_model_status",
        lambda: {"transformers_available": False, "model_name": None},
    )
    monkeypatch.setattr(web_search, "extract_key_sentences", lambda text: [text])
    monkeypatch.setattr(web_search, "search_openalex", lambda query, num=3, log=None: [{
        "url": "https://example.org/paper.pdf",
        "title": "A Research Paper Title",
        "snippet": "A Research Paper Title. Authors: A. Author",
        "source_type": "scholarly_paper",
    }])
    monkeypatch.setattr(web_search, "search_web", lambda *args, **kwargs: [])
    monkeypatch.setattr(web_search, "_fetch_and_score", lambda *args: None)

    results = web_search.check_plagiarism_online(
        "A Research Paper Title with enough text for checking.",
        document_meta={"title": "A Research Paper Title"},
    )

    assert results[0]["url"] == "https://example.org/paper.pdf"
    assert results[0]["verification_status"] == "paper_identified_page_unavailable"


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

    results = web_search.search_web("machine learning", num=2)
    urls = {item["url"] for item in results}

    assert "https://wiki.example/article-a" in urls
    assert "https://ddg.example/article-b" in urls

