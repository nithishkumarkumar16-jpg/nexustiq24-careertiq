from typing import Literal
from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    customer_id: str
    session_id: str = "default"
    message: str = Field(min_length=1, max_length=4000)


class Citation(BaseModel):
    article_id: str
    title: str = ""
    section: str = ""
    excerpt: str = ""


class Handover(BaseModel):
    issue_summary: str
    established: list[str]
    tried: list[str]
    reason_for_transfer: str


class AssistantResult(BaseModel):
    outcome: Literal["resolution", "follow_up", "escalate"]
    draft_response: str = ""
    follow_up_question: str = ""
    citations: list[Citation] = []
    handover: Handover | None = None
    status_note: str = ""
