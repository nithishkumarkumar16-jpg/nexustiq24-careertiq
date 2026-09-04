from src.guardrails import validate_model_result

EVIDENCE=[{"article_id":"KB-1","title":"Test", "section":"Scope","text":"Grounded evidence."}]


def grounded_raw(**changes):
    result={"outcome":"resolution","draft_response":"Grounded answer.","citations":[{"article_id":"KB-1","section":"Scope"}],"confidence":"high","unsupported_claims":[]}
    result.update(changes)
    return result


def test_resolution_needs_valid_citation():
    assert validate_model_result(grounded_raw(citations=[]),EVIDENCE) is None


def test_invalid_citation_is_rejected():
    result=validate_model_result(grounded_raw(citations=[{"article_id":"not-real","section":"Scope"}]),EVIDENCE)
    assert result is None


def test_follow_up_has_exactly_one_question():
    result=validate_model_result({"outcome":"follow_up","follow_up_question":"Which device?","citations":[],"confidence":"medium","unsupported_claims":[]},EVIDENCE)
    assert result and result.outcome == "follow_up"
    assert validate_model_result({"outcome":"follow_up","follow_up_question":"Which device? And when?","citations":[],"confidence":"medium","unsupported_claims":[]},EVIDENCE) is None


def test_valid_grounded_resolution_requires_exact_retrieved_section():
    result=validate_model_result(grounded_raw(),EVIDENCE)
    assert result and result.citations[0].section == "Scope"
    assert validate_model_result(grounded_raw(citations=[{"article_id":"KB-1","section":"Not retrieved"}]),EVIDENCE) is None


def test_unsupported_claim_and_malformed_output_are_rejected():
    assert validate_model_result(grounded_raw(unsupported_claims=["invented charge"]),EVIDENCE) is None
    assert validate_model_result(None,EVIDENCE) is None
    assert validate_model_result({"outcome":"resolution"},EVIDENCE) is None
