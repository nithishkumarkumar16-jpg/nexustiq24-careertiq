from src.gemini_client import draft_with_gemini


def test_gemini_unavailable_returns_none(monkeypatch):
    monkeypatch.setattr("src.gemini_client.GEMINI_API_KEY", "")
    assert draft_with_gemini({}, [], [], "routine") is None
