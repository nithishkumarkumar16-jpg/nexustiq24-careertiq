"""Validates LLM suggestions against retrieved local evidence and deterministic safety policy."""
from src.schemas import AssistantResult, Citation, Handover


def valid_citations(citations: list[dict], evidence: list[dict]) -> list[Citation]:
    if not isinstance(citations, list):
        return []
    available={(e["article_id"], e["section"]):e for e in evidence}
    result=[]
    for citation in citations or []:
        if not isinstance(citation, dict):
            continue
        article_id=citation.get("article_id","")
        section=citation.get("section", "")
        item=available.get((article_id, section))
        if item:
            result.append(Citation(article_id=article_id,title=item["title"],section=section,excerpt=item["text"][:220]))
    return result


def validate_model_result(raw: dict | None, evidence: list[dict], forced_outcome: str | None=None) -> AssistantResult | None:
    required_fields={"outcome", "draft_response", "follow_up_question", "citations", "confidence", "unsupported_claims", "handover"}
    if not isinstance(raw, dict) or not required_fields.issubset(raw):
        return None
    if not isinstance(raw.get("unsupported_claims"), list) or raw.get("unsupported_claims"):
        return None
    outcome=forced_outcome or raw.get("outcome")
    if outcome not in {"resolution","follow_up","escalate"}: return None
    confidence=raw.get("confidence")
    if confidence not in {"high", "medium", "low"}:
        return None
    citations=valid_citations(raw.get("citations",[]),evidence)
    raw_citations=raw.get("citations", [])
    if not isinstance(raw_citations, list):
        return None
    # A mixed valid/fabricated citation list is unsafe; reject the entire model response.
    if len(citations) != len(raw_citations):
        return None
    if outcome=="resolution":
        draft=str(raw.get("draft_response", "")).strip()
        if not citations or not draft or len(draft) > 1500 or confidence == "low":
            return None
    if outcome=="follow_up":
        question=str(raw.get("follow_up_question","")).strip()
        if not question or len(question) > 500 or question.count("?") != 1: return None
        return AssistantResult(outcome="follow_up",follow_up_question=question,citations=citations,confidence=confidence)
    if outcome=="escalate":
        handover=raw.get("handover") or {}
        required=("issue_summary","established","tried","reason_for_transfer")
        if not isinstance(handover, dict) or not all(k in handover for k in required): return None
        if not isinstance(handover["issue_summary"], str) or not isinstance(handover["reason_for_transfer"], str): return None
        if not isinstance(handover["established"], list) or not isinstance(handover["tried"], list): return None
        return AssistantResult(outcome="escalate",draft_response=str(raw.get("draft_response","")).strip(),citations=citations,handover=Handover(**handover),confidence=confidence)
    return AssistantResult(outcome="resolution",draft_response=str(raw["draft_response"]).strip(),citations=citations,confidence=confidence)
