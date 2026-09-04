from src.guardrails import validate_model_result

EVIDENCE=[{"article_id":"KB-1","title":"Test", "section":"Scope","text":"Grounded evidence."}]


def test_resolution_needs_valid_citation():
    assert validate_model_result({"outcome":"resolution","draft_response":"Answer","citations":[]},EVIDENCE) is None


def test_invalid_citation_is_rejected():
    result=validate_model_result({"outcome":"resolution","draft_response":"Answer","citations":[{"article_id":"not-real"}]},EVIDENCE)
    assert result is None


def test_follow_up_has_exactly_one_question():
    result=validate_model_result({"outcome":"follow_up","follow_up_question":"Which device?","citations":[]},EVIDENCE)
    assert result and result.outcome == "follow_up"
    assert validate_model_result({"outcome":"follow_up","follow_up_question":"Which device? And when?","citations":[]},EVIDENCE) is None
