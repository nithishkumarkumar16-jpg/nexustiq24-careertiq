from src.database import initialize_database
from src.case_service import analyze
from src.schemas import AnalyzeRequest


def setup_module():
    initialize_database()


def run(customer_id, message):
    return analyze(AnalyzeRequest(customer_id=customer_id,session_id="test-suite",message=message))


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
