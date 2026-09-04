from src.article_loader import load_articles
from src.retrieval import LocalRetriever


def test_article_chunks_keep_required_provenance_metadata():
    articles=load_articles()
    assert articles
    for article in articles:
        for chunk in article["chunks"]:
            assert chunk["article_id"] == article["id"]
            assert chunk["title"] == article["title"]
            assert chunk["section"]
            assert chunk["source_text"]


def test_keyword_fallback_returns_local_result_metadata(monkeypatch):
    retriever=LocalRetriever()
    retriever.embedding_ready=False
    result=retriever.search("higher invoice charge", "broadband")
    assert result
    assert result[0]["retrieval_method"] == "keyword"
    for item in result:
        assert {"article_id", "title", "section", "text", "source_text"} <= item.keys()


def test_embedding_failure_falls_back_to_keyword(monkeypatch):
    retriever=LocalRetriever()
    retriever.embedding_ready=True
    retriever.vectors=[[1.0] for _ in retriever.chunks]
    monkeypatch.setattr("src.retrieval.GEMINI_API_KEY", "test-key")
    from google import genai
    monkeypatch.setattr(genai, "Client", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("embedding unavailable")))
    result=retriever.search("higher invoice charge", "broadband")
    assert result
    assert result[0]["retrieval_method"] == "keyword"
