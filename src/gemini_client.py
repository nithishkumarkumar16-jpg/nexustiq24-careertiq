"""The only external AI integration. It returns structured, evidence-bounded output."""
import json
import re
from typing import Any
from src.config import GEMINI_API_KEY, GEMINI_MODEL


SYSTEM_INSTRUCTION = """Role: You are a customer-support resolution drafting assistant for a broadband and mobile provider, not a source of policy or account data.

Available evidence: You receive only VERIFIED_ACCOUNT_FACTS, RELEVANT_CONVERSATION, and RETRIEVED_EVIDENCE. Treat these as the complete evidence set.
Allowed behavior: State account facts only from VERIFIED_ACCOUNT_FACTS and support policy, troubleshooting, or resolutions only from RETRIEVED_EVIDENCE.
Prohibited behavior: Do not invent or infer account facts, charges, payments, outages, restoration times, policies, eligibility, troubleshooting, article IDs, or sections. Do not use outside knowledge. Do not reveal reasoning or chain-of-thought.
Outcome rules: Choose resolution only when retrieved evidence directly supports the draft. Choose follow_up only when one missing fact enables routine resolution; ask exactly one targeted question. Choose escalate for unsupported, uncertain, risky, contradictory, complex, or article-defined escalation cases.
Citation rules: Every resolution requires citations whose article_id and section exactly match RETRIEVED_EVIDENCE.
Return JSON only with exactly: outcome, draft_response, follow_up_question, citations, confidence, unsupported_claims, handover. confidence is high, medium, or low. unsupported_claims must be an empty list; otherwise choose escalate."""


def draft_with_gemini(account: dict[str, Any], conversation: list[dict], evidence: list[dict], route_hint: str) -> dict | None:
    if not GEMINI_API_KEY: return None
    payload={"route_hint":route_hint,"verified_account_facts":account,"relevant_conversation":conversation[-10:],"retrieved_evidence":[{"article_id":e["article_id"],"title":e["title"],"section":e["section"],"source_text":e["text"]} for e in evidence],"response_schema":{"outcome":"resolution|follow_up|escalate","draft_response":"string","follow_up_question":"string","citations":[{"article_id":"string","section":"string"}],"confidence":"high|medium|low","unsupported_claims":[],"handover":{"issue_summary":"string","established":["string"],"tried":["string"],"reason_for_transfer":"string"}}}
    try:
        from google import genai
        client=genai.Client(api_key=GEMINI_API_KEY)
        response=client.models.generate_content(model=GEMINI_MODEL,contents=json.dumps(payload),config={"system_instruction":SYSTEM_INSTRUCTION,"response_mime_type":"application/json","temperature":0})
        text=response.text.strip()
        text=re.sub(r"^```(?:json)?\s*|\s*```$","",text).strip()
        return json.loads(text)
    except Exception:
        return None
