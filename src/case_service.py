"""Case orchestration: retrieval and Gemini drafting are bounded by deterministic policy."""
from src.schemas import AnalyzeRequest, AssistantResult, Citation, Handover
from src.repositories import customer_context, get_messages, add_message
from src.retrieval import retriever
from src.routing import decide
from src.gemini_client import draft_with_gemini
from src.guardrails import validate_model_result


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
    # The customer message drives relevance; service type filters eligible articles.
    evidence=retriever.search(payload.message,context["service"].get("service_type",""))
    decision=decide(payload.message,context)
    # Deterministic follow-up/escalation rules take precedence over generated prose.
    if decision.outcome in {"follow_up","escalate"}:
        result=_fallback(payload.message,context,evidence,decision)
    else:
        raw=draft_with_gemini(context,conversation,evidence,decision.reason)
        result=validate_model_result(raw,evidence,forced_outcome="resolution") or _fallback(payload.message,context,evidence,decision)
    add_message(payload.customer_id,payload.session_id,"assistant",result.draft_response or result.follow_up_question)
    return result
