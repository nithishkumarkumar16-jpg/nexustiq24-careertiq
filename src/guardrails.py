"""Validates LLM suggestions against retrieved local evidence and deterministic safety policy."""
from src.schemas import AssistantResult, Citation, Handover


def valid_citations(citations: list[dict], evidence: list[dict]) -> list[Citation]:
    available={e["article_id"]:e for e in evidence}
    result=[]
    for citation in citations or []:
        article_id=citation.get("article_id","")
        if article_id in available:
            item=available[article_id]
            result.append(Citation(article_id=article_id,title=item["title"],section=citation.get("section") or item["section"],excerpt=item["text"][:220]))
    return result


def validate_model_result(raw: dict | None, evidence: list[dict], forced_outcome: str | None=None) -> AssistantResult | None:
    if not raw: return None
    outcome=forced_outcome or raw.get("outcome")
    if outcome not in {"resolution","follow_up","escalate"}: return None
    citations=valid_citations(raw.get("citations",[]),evidence)
    if outcome=="resolution" and (not citations or not str(raw.get("draft_response","")).strip()): return None
    if outcome=="follow_up":
        question=str(raw.get("follow_up_question","")).strip()
        if not question or question.count("?") != 1: return None
        return AssistantResult(outcome="follow_up",follow_up_question=question,citations=citations)
    if outcome=="escalate":
        handover=raw.get("handover") or {}
        required=("issue_summary","established","tried","reason_for_transfer")
        if not all(k in handover for k in required): return None
        return AssistantResult(outcome="escalate",draft_response=str(raw.get("draft_response","")).strip(),citations=citations,handover=Handover(**handover))
    return AssistantResult(outcome="resolution",draft_response=str(raw["draft_response"]).strip(),citations=citations)
