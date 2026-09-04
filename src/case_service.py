"""Case orchestration: retrieval and Gemini drafting are bounded by deterministic policy."""
from src.schemas import AnalyzeRequest, AssistantResult, Citation, Handover
from src.repositories import customer_context, get_messages, add_message
from src.retrieval import retriever
from src.routing import decide
from src.gemini_client import draft_with_gemini
from src.guardrails import validate_model_result

MAX_FOLLOW_UPS_PER_CASE = 2


def _retrieval_query(message: str, conversation: list[dict], context: dict) -> str:
    """Use support-relevant context only; exclude contact details and addresses."""
    service = context["service"]
    billing = context["billing"]
    recent = " ".join(item["content"] for item in conversation[-6:])
    state = " ".join(filter(None, [
        service.get("service_type"), service.get("service_status"), service.get("plan_name"),
        billing.get("payment_status"), billing.get("recent_charge_summary"),
    ]))
    return f"Customer request: {message}\nRecent conversation: {recent}\nService and account state: {state}"


def _verified_facts(context: dict) -> dict:
    """The Gemini boundary: only verified, minimally necessary support facts."""
    service = context["service"]
    billing = context["billing"]
    return {
        "service_type": service.get("service_type"), "plan_name": service.get("plan_name"),
        "service_status": service.get("service_status"), "contract_end_date": service.get("contract_end_date"),
        "usage_summary": service.get("usage_summary"), "payment_status": billing.get("payment_status"),
        "current_balance": billing.get("current_balance"), "last_invoice_date": billing.get("last_invoice_date"),
        "last_invoice_amount": billing.get("last_invoice_amount"), "recent_charge_summary": billing.get("recent_charge_summary"),
        "recent_ticket_actions": [ticket.get("actions_taken") for ticket in context["tickets"] if ticket.get("actions_taken")],
    }


def _routing_context(context: dict, conversation: list[dict]) -> dict:
    """Include previously stated troubleshooting in deterministic routing, not the LLM."""
    prior_actions = " ".join(
        message["content"] for message in conversation
        if message["role"] in {"customer", "agent"}
    )
    routed = dict(context)
    routed["tickets"] = [*context["tickets"], {"actions_taken": prior_actions}]
    return routed


def _follow_up_count(conversation: list[dict]) -> int:
    return sum(
        1 for message in conversation
        if message["role"] == "assistant" and message["content"].strip().endswith("?")
    )


def _citations(evidence: list[dict]) -> list[Citation]:
    unique=[]; seen=set()
    for e in evidence:
        if e["article_id"] not in seen:
            seen.add(e["article_id"]);unique.append(Citation(article_id=e["article_id"],title=e["title"],section=e["section"],excerpt=e["text"][:220]))
    return unique


def _handover(message: str, context: dict, reason: str) -> Handover:
    tried=[]
    for ticket in context["tickets"]:
        if ticket.get("actions_taken"):
            tried.append(ticket["actions_taken"])
    return Handover(issue_summary=message,established=[f"Service: {context['service'].get('service_status')}",f"Plan: {context['service'].get('plan_name')}",f"Billing status: {context['billing'].get('payment_status')}"],tried=tried,reason_for_transfer=reason)


def _fallback(message: str, context: dict, evidence: list[dict], decision) -> AssistantResult:
    preferred_ids = {
        "Known local outage": {"KB-CONN-003"},
        "Possible unknown charge or account-security issue": {"KB-SEC-001"},
        "Recorded troubleshooting has already been exhausted": {"KB-ESC-001", "KB-CONN-001"},
        "Customer payment claim conflicts with unrecorded overdue account": {"KB-BILL-002"},
    }.get(decision.reason, set())
    selected = [item for item in evidence if not preferred_ids or item["article_id"] in preferred_ids]
    citations=_citations(selected or evidence)
    if decision.outcome=="follow_up":
        return AssistantResult(outcome="follow_up",follow_up_question=decision.follow_up,status_note="Targeted question selected by local case policy.")
    if decision.outcome=="escalate":
        return AssistantResult(outcome="escalate",draft_response="I’m transferring this to a human support specialist so it can be reviewed safely.",citations=citations,handover=_handover(message,context,decision.reason),status_note="Escalation selected by local case policy.")
    service=context["service"]; billing=context["billing"]
    lower=message.lower()
    if service.get("service_status")=="outage-affected":
        text="Your broadband service is affected by a known area network outage. Our network operations team is working on restoration. I don’t have a restoration time in the account record."
    elif any(x in lower for x in ("bill","invoice","charge","higher","expensive")):
        text=f"I reviewed the latest account record: {billing.get('recent_charge_summary','No charge summary is available.')}"
    elif any(x in lower for x in ("data","allowance","gb","usage")):
        text=f"Your current plan is {service.get('plan_name')}. The account record says: {service.get('usage_summary')}"
    else:
        text="Based on the matching support guidance, please review the evidence shown. A human agent should approve this response before sending."
    if not citations:
        return AssistantResult(outcome="escalate",draft_response="I’m transferring this to a human support specialist because I could not find matching internal guidance.",handover=_handover(message,context,"No matching support article was found."),status_note="Safe local fallback: no evidence available.")
    return AssistantResult(outcome="resolution",draft_response=text,citations=citations,status_note="Drafted using local evidence fallback; Gemini was unavailable or its response could not be validated.")


def analyze(payload: AnalyzeRequest) -> AssistantResult | None:
    context=customer_context(payload.customer_id)
    if not context: return None
    add_message(payload.customer_id,payload.session_id,"customer",payload.message)
    conversation=get_messages(payload.customer_id,payload.session_id)
    evidence=retriever.search(_retrieval_query(payload.message, conversation, context),context["service"].get("service_type",""))
    routing_context=_routing_context(context, conversation)
    decision=decide(payload.message,routing_context)
    if decision.outcome == "follow_up" and _follow_up_count(conversation) >= MAX_FOLLOW_UPS_PER_CASE:
        from src.routing import RouteDecision
        decision=RouteDecision("escalate", "Required clarification was not obtained after two targeted follow-ups")
    # Deterministic follow-up/escalation rules take precedence over generated prose.
    if decision.outcome in {"follow_up","escalate"}:
        result=_fallback(payload.message,routing_context,evidence,decision)
    else:
        raw=draft_with_gemini(_verified_facts(context),conversation,evidence,decision.reason)
        # Gemini may safely choose follow-up or escalation when retrieved evidence shows it is needed.
        result=validate_model_result(raw,evidence) or _fallback(payload.message,routing_context,evidence,decision)
    add_message(payload.customer_id,payload.session_id,"assistant",result.draft_response or result.follow_up_question)
    return result
