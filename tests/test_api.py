from fastapi.testclient import TestClient
from src.database import initialize_database
from src.web import app
from uuid import uuid4


def setup_module(): initialize_database()


def test_health_and_customers():
    client=TestClient(app)
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/customers").status_code == 200


def analyze(client, customer_id, message, session_id, unique=True):
    response = client.post("/api/cases/analyze", json={
        "customer_id": customer_id,
        "message": message,
        "session_id": f"{session_id}-{uuid4()}" if unique else session_id,
    })
    assert response.status_code == 200
    return response.json()


def test_required_ps04_scenarios_through_api():
    client = TestClient(app)

    normal = analyze(client, "C001", "Why is my bill higher this month?", "audit-normal")
    assert normal["outcome"] == "resolution"
    assert normal["citations"]
    assert "router delivery charge" in normal["draft_response"].lower()

    missing = analyze(client, "C001", "My broadband connection is down", "audit-missing")
    assert missing["outcome"] == "follow_up"
    assert missing["follow_up_question"].count("?") == 1

    outage = analyze(client, "C002", "My internet is down", "audit-outage")
    assert outage["outcome"] == "resolution"
    assert any(item["article_id"] == "KB-CONN-003" for item in outage["citations"])

    unknown_charge = analyze(client, "C004", "I have an unrecognized charge", "audit-security")
    assert unknown_charge["outcome"] == "escalate"
    assert_handover(unknown_charge)

    repeated_fault = analyze(client, "C006", "All devices are still down after trying everything", "audit-fault")
    assert repeated_fault["outcome"] == "escalate"
    assert_handover(repeated_fault)
    assert any("router reboot" in item.lower() for item in repeated_fault["handover"]["tried"])

    unsupported = analyze(client, "C003", "Can you repair my refrigerator?", "audit-unsupported")
    assert unsupported["outcome"] == "escalate"
    assert_handover(unsupported)

    conflict = analyze(client, "C005", "I paid already yesterday", "audit-conflict")
    assert conflict["outcome"] == "escalate"
    assert_handover(conflict)


def assert_handover(response):
    handover = response["handover"]
    assert handover["issue_summary"]
    assert handover["established"]
    assert isinstance(handover["tried"], list)
    assert handover["reason_for_transfer"]


def test_conversation_is_preserved_through_api():
    client = TestClient(app)
    session_id = "audit-conversation"
    analyze(client, "C001", "My broadband connection is down", session_id, unique=False)
    messages = client.get(f"/api/customers/C001/conversation?session_id={session_id}").json()
    assert [message["role"] for message in messages][-2:] == ["customer", "assistant"]
