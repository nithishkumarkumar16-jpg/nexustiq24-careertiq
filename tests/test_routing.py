from src.routing import decide


def context(service_status="active", payment_status="paid", actions=""):
    return {"service":{"service_type":"broadband","service_status":service_status,"plan_name":"Fibre"},"billing":{"payment_status":payment_status,"recent_charge_summary":"Invoice detail"},"tickets":[{"actions_taken":actions}]}


def test_unknown_charge_escalates():
    assert decide("This is an unknown charge", context()).outcome == "escalate"


def test_outage_resolves():
    assert decide("My internet is down", context("outage-affected")).outcome == "resolution"


def test_missing_device_scope_follows_up():
    decision=decide("My broadband is down", context())
    assert decision.outcome == "follow_up"
    assert decision.follow_up.count("?") == 1


def test_payment_conflict_escalates():
    assert decide("I paid already", context(payment_status="overdue")).outcome == "escalate"


def test_repeated_fault_escalates():
    assert decide("All devices are down", context(actions="Router reboot; cable check; router reset.")).outcome == "escalate"


def test_missing_billing_detail_gets_one_targeted_question():
    data = context()
    data["billing"]["recent_charge_summary"] = ""
    result = decide("Why is my bill higher?", data)
    assert result.outcome == "follow_up"
    assert result.follow_up == "Could you share the date and amount of the charge you’re querying?"
