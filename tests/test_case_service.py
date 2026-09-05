from src.database import initialize_database
from src.case_service import analyze
from src.schemas import AnalyzeRequest
import src.case_service as case_service
from src.repositories import add_message
from uuid import uuid4


def setup_module():
    initialize_database()


def run(customer_id, message):
    return analyze(AnalyzeRequest(customer_id=customer_id,session_id=f"test-{uuid4()}",message=message))


def test_known_outage_resolution():
    result=run("C002","My internet is down")
    assert result.outcome == "resolution"
    assert result.citations


def test_normal_billing_resolution():
    result=run("C001","Why is my bill higher this month?")
    assert result.outcome == "resolution"
    assert result.citations


def test_missing_information_follow_up():
    result=run("C001","My broadband connection is down")
    assert result.outcome == "follow_up"
    assert result.follow_up_question.count("?") == 1


def test_fraud_like_charge_escalates():
    result=run("C004","There is an unknown charge on my bill")
    assert result.outcome == "escalate" and result.handover


def test_contradictory_payment_escalates():
    result=run("C005","I paid already yesterday")
    assert result.outcome == "escalate"


def test_repeated_troubleshooting_escalates():
    result=run("C006","All devices are still down after trying everything")
    assert result.outcome == "escalate"


def test_unsupported_request_escalates():
    result=run("C003","Can you repair my refrigerator?")
    assert result.outcome == "escalate"


def test_valid_gemini_grounded_resolution_is_used(monkeypatch):
    evidence=[{"article_id":"KB-BILL-001","title":"Understanding a higher-than-expected bill","section":"Approved resolution","text":"Explain only the charge listed in the account record."}]
    monkeypatch.setattr(case_service.retriever, "search", lambda *args, **kwargs: evidence)
    monkeypatch.setattr(case_service, "draft_with_gemini", lambda *args, **kwargs: {
        "outcome":"resolution", "draft_response":"Your invoice record includes a router delivery charge.",
        "follow_up_question":"", "citations":[{"article_id":"KB-BILL-001","section":"Approved resolution"}],
        "confidence":"high", "unsupported_claims":[], "handover":None,
    })
    result=run("C001","Why is my bill higher this month?")
    assert result.outcome == "resolution"
    assert result.confidence == "high"
    assert result.citations[0].article_id == "KB-BILL-001"


def test_prior_conversation_troubleshooting_prevents_repeating_steps():
    session_id=f"test-repeated-{uuid4()}"
    add_message("C001",session_id,"customer","I rebooted the router, checked the cable, and reset it already.")
    result=analyze(AnalyzeRequest(customer_id="C001",session_id=session_id,message="All devices are still down."))
    assert result.outcome == "escalate"
    assert "troubleshooting" in result.handover.reason_for_transfer.lower()
    assert any("rebooted" in step.lower() for step in result.handover.tried)


def test_follow_up_is_bounded_and_escalates_after_two_questions():
    session_id=f"test-bounded-{uuid4()}"
    add_message("C001",session_id,"assistant","Are all devices affected, or only one device?")
    add_message("C001",session_id,"assistant","Are all devices affected, or only one device?")
    result=analyze(AnalyzeRequest(customer_id="C001",session_id=session_id,message="My broadband is still down."))
    assert result.outcome == "escalate"
    assert "two targeted follow-ups" in result.handover.reason_for_transfer


def test_handover_excludes_current_customer_message_from_troubleshooting_attempted():
    """Verify that 'Troubleshooting Attempted' contains only prior actions, not the current message."""
    session_id=f"test-handover-data-{uuid4()}"
    # Add prior conversation about troubleshooting
    add_message("C006",session_id,"customer","I rebooted the router and checked cables.")
    # Current message that triggers escalation (should NOT appear in tried field)
    current_message = "All devices are still down after trying everything"
    result=analyze(AnalyzeRequest(customer_id="C006",session_id=session_id,message=current_message))
    assert result.outcome == "escalate"
    # Verify prior troubleshooting is preserved
    assert any("rebooted" in step.lower() for step in result.handover.tried)
    # Verify current message does NOT appear in handover.tried
    concatenated_tried = " ".join(result.handover.tried).lower()
    assert "trying everything" not in concatenated_tried
    # Verify current message only appears in issue_summary (Case Summary)
    assert current_message in result.handover.issue_summary
