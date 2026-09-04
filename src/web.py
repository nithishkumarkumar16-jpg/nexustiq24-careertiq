from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request
from src.config import ROOT_DIR, GEMINI_API_KEY
from src.repositories import list_customers, customer_context, get_messages
from src.schemas import AnalyzeRequest

app = FastAPI(title="NexusTiQ24 Customer Support Resolution Assistant")
app.mount("/static", StaticFiles(directory=str(ROOT_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(ROOT_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "gemini_configured": bool(GEMINI_API_KEY)}


@app.get("/api/customers")
def customers():
    return list_customers()


@app.get("/api/customers/{customer_id}")
def customer(customer_id: str):
    result = customer_context(customer_id)
    if not result:
        raise HTTPException(404, "Customer not found")
    return result


@app.get("/api/customers/{customer_id}/conversation")
def conversation(customer_id: str, session_id: str = "default"):
    if not customer_context(customer_id):
        raise HTTPException(404, "Customer not found")
    return get_messages(customer_id, session_id)


@app.post("/api/cases/analyze")
def analyze_case(payload: AnalyzeRequest):
    # Connected after RAG, reasoning, and deterministic guardrails are initialized.
    from src.case_service import analyze
    result = analyze(payload)
    if result is None:
        raise HTTPException(404, "Customer not found")
    return result.model_dump()
