"""Deterministic case policy. This module makes safety decisions independently of LLM prose."""
from dataclasses import dataclass


@dataclass
class RouteDecision:
    outcome: str
    reason: str
    follow_up: str = ""


def decide(message: str, context: dict) -> RouteDecision:
    text=message.lower()
    service=context["service"]; billing=context["billing"]; tickets=context["tickets"]
    all_actions=" ".join(t.get("actions_taken","") for t in tickets).lower()
    security_terms=("unknown charge","unrecognized","fraud","scam","not my charge","suspicious activity","account hacked","account compromise")
    if any(term in text for term in security_terms):
        return RouteDecision("escalate","Possible unknown charge or account-security issue")
    payment_claim=("i paid","paid already","made a payment","payment made","payment was successful","payment succeeded")
    if any(term in text for term in payment_claim) and billing.get("payment_status")=="overdue":
        return RouteDecision("escalate","Customer payment claim conflicts with unrecorded overdue account")

    unsupported_terms = (
        "refrigerator", "fridge", "washing machine", "microwave",
        "television", "tv", "air conditioner", "ac",
        "laptop", "computer", "printer", "car", "bike"
    )
    if any(term in text for term in unsupported_terms):
        return RouteDecision("escalate","Request is outside telecom support scope")

    if service.get("service_status")=="outage-affected" and any(x in text for x in ("internet","broadband","connection","down","offline","outage")):
        return RouteDecision("resolution","Known local outage")
    connectivity=any(x in text for x in ("internet","broadband","connection","wifi","wi-fi","router","offline","down"))
    if connectivity and all(x in all_actions for x in ("reboot","cable","reset")):
        return RouteDecision("escalate","Recorded troubleshooting has already been exhausted")
    if connectivity and service.get("service_type")=="broadband" and not any(x in text for x in ("all devices","one device","only my","every device")):
        return RouteDecision("follow_up","Affected-device scope is missing","Are all devices affected, or only one device?")
    if any(x in text for x in ("bill","invoice","charge","expensive","higher")) and not billing.get("recent_charge_summary"):
        return RouteDecision("follow_up","Invoice detail is unavailable","Could you share the date and amount of the charge you’re querying?")
    if any(x in text for x in ("upgrade","downgrade","change plan")):
        return RouteDecision("escalate","Plan options and order completion require a plan specialist")
    return RouteDecision("resolution","Routine request")
