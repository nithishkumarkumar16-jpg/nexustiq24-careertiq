"""The only external AI integration. It returns structured, evidence-bounded output."""
import json
import re
from typing import Any
from src.config import GEMINI_API_KEY


SYSTEM_INSTRUCTION = """You draft support-agent recommendations. Use only ACCOUNT_FACTS, CONVERSATION, and RETRIEVED_EVIDENCE supplied by the application. Never invent facts, policies, times, charges, or troubleshooting. Return valid JSON only. A resolution must cite one or more supplied article IDs. If a required fact is missing, choose follow_up and ask exactly one targeted question. If unsupported, risky, contradictory, or an evidence escalation condition applies, choose escalate and include a concise handover."""


def draft_with_gemini(account: dict[str, Any], conversation: list[dict], evidence: list[dict], route_hint: str) -> dict | None:
    if not GEMINI_API_KEY: return None
    payload={"route_hint":route_hint,"account_facts":account,"conversation":conversation[-10:],"retrieved_evidence":[{"article_id":e["article_id"],"title":e["title"],"section":e["section"],"text":e["text"]} for e in evidence],"response_schema":{"outcome":"resolution|follow_up|escalate","draft_response":"string","follow_up_question":"string","citations":[{"article_id":"string","section":"string"}],"handover":{"issue_summary":"string","established":["string"],"tried":["string"],"reason_for_transfer":"string"}}}
    try:
        from google import genai
        client=genai.Client(api_key=GEMINI_API_KEY)
        response=client.models.generate_content(model="gemini-2.5-flash",contents=json.dumps(payload),config={"system_instruction":SYSTEM_INSTRUCTION,"response_mime_type":"application/json","temperature":0})
        text=response.text.strip()
        text=re.sub(r"^```(?:json)?\s*|\s*```$","",text).strip()
        return json.loads(text)
    except Exception:
        return None
