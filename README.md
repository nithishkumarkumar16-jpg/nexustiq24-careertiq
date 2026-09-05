TRACK_ID=PS04

# NexusTiQ24 — Customer Support Resolution Assistant

ResolveIQ is a local, agent-facing MVP for a fictional broadband and mobile support desk. It uses customer account records, ticket history, conversation context, and local support articles to produce a grounded resolution, one targeted follow-up question, or a human handover.

## Start

```bash
pip install -r requirements.txt
python app.py
```

Open [http://localhost:8000](http://localhost:8000). The app seeds its fictional SQLite data on first start.

## Problem Statement

PS04 — Customer Support Resolution Assistant.

This solution supports routine telecom support requests using verified customer account context and relevant support articles. When information is missing, the assistant asks one targeted follow-up question. When a request is complex, uncertain, unsupported, contradictory, security-sensitive, or repeatedly unresolved, it escalates to a human with the relevant context and history.

## Architecture & Workflow

The request flow is:

```
Customer message
  ↓
Deterministic case routing
  ↓
Local knowledge retrieval + caching
  ↓
Verified account & ticket context
  ↓
Bounded Gemini reasoning (structured output)
  ↓
Deterministic guardrails validation
  ↓
Resolution, follow-up, or escalation
```

The LLM is responsible for bounded language reasoning and drafting text. Deterministic application logic controls all safety-critical decisions: routing, evidence validation, escalation, follow-up limits, and response boundaries.

## Gemini Configuration

Set `GEMINI_API_KEY` in the environment before starting the app. Gemini is used for:

1. **Embeddings** (`gemini-embedding-001`): Semantic retrieval of local support articles with local caching.
2. **Bounded drafting** (`gemini-3.5-flash-lite`): Generating grounded resolutions within a structured response schema validated by deterministic guardrails.

If Gemini is unavailable, the application stays operational with local keyword retrieval and deterministic fallback behavior. No response is generated without valid evidence.

## Local Knowledge Base

The knowledge base consists of 9 fictional telecom support articles stored locally in `knowledge_base/` as Markdown:

- KB-BILL-001: Higher-than-expected bills
- KB-BILL-002: Payment restoration and overdue accounts
- KB-CONN-001: Broadband connectivity troubleshooting
- KB-CONN-002: WiFi device diagnosis
- KB-CONN-003: Known area network outages
- KB-ESC-001: Repeated faults and escalation criteria
- KB-MOB-001: Mobile data allowance
- KB-PLAN-001: Plan changes and options
- KB-SEC-001: Unknown charges and account security

Articles are parsed once at startup. Sections are indexed and embedded. Retrieval uses semantic similarity when embeddings are available, with deterministic keyword fallback when Gemini embeddings are unavailable.

Embedding results are cached locally in `data/embedding_cache.json` to avoid redundant API calls.

Customer contact details and service addresses are not sent to Gemini during retrieval; only support-relevant context (service type, status, plan, billing state, and recent conversation) is used as retrieval context.

## Retrieval & Grounding

The system retrieves support articles using:

1. **Semantic retrieval** (when Gemini embeddings available): Query embedding compared against cached article embeddings.
2. **Keyword fallback** (always available): Word-overlap scoring against article titles, sections, and keywords.

Retrieved evidence is the single source of truth for resolution generation. Every resolution must cite evidence with matching article ID and section.

Ungrounded or fabricated citations invalidate the generated response and trigger escalation to a human.

## Deterministic Routing

Before Gemini is invoked, the application applies deterministic routing rules to classify the case:

- **Security-sensitive** (unknown charge, fraud, account compromise) → escalate immediately
- **Contradictory payment claim** (customer claims payment but account shows overdue) → escalate immediately
- **Known outage** (service status = outage-affected + connectivity language) → grounded resolution using outage article
- **Repeated troubleshooting** (prior ticket actions include all major troubleshooting steps) → escalate to prevent repeated steps
- **Missing diagnostic detail** (connectivity request without device scope) → one targeted follow-up
- **Unsupported request** (non-telecom: refrigerator, car, computer repair) → escalate immediately
- **Plan changes** (upgrade/downgrade requests) → escalate to plan specialist

Routing decisions take precedence over Gemini prose.

## Citation Validation

After Gemini generates a response, all citations are validated:

1. Cited article ID must exist in retrieved evidence.
2. Cited section must match retrieved section exactly.
3. No citation can be fabricated or partially correct.
4. Mixed valid/fabricated citations invalidate the entire response.

Failed validation triggers fallback to a safe deterministic response.

## Follow-up Questions

When the available information is insufficient for safe resolution, the assistant asks exactly one targeted question for the missing diagnostic detail (e.g., "Are all devices affected, or only one device?").

Follow-up behavior is bounded: if a customer remains unresolved after two targeted follow-ups, the case is automatically escalated to a human.

## Escalation & Handover

Cases requiring human intervention receive a concise handover containing:

- **Case Summary**: The latest customer message
- **Established Facts**: Verified account facts (service type, plan, billing status)
- **Troubleshooting Attempted**: Actual recorded troubleshooting actions from the customer's ticket history and prior conversation (excluding the current message)
- **Reason for Transfer**: Why the case is being escalated

Repeated broadband faults preserve previously attempted troubleshooting in the handover so support specialists can avoid asking the customer to repeat the same steps.

## Demo Cases

Six fictional customer scenarios demonstrate the system's behavior:

- **Asha Raman (C001):** Higher invoice. Account shows router delivery charge. Resolution grounded in KB-BILL-001.
- **Vikram Das (C002):** Broadband outage. Service status is outage-affected. Resolution grounded in KB-CONN-003.
- **Meera Iyer (C003):** Mobile data question or unsupported request (refrigerator repair). Follows routing accordingly.
- **Rohan Shah (C004):** Unknown charge. Security escalation triggered immediately.
- **Nila Bose (C005):** Claims payment was made. Billing account shows overdue status. Contradictory payment escalation.
- **Arjun Rao (C006):** Broadband still down. Ticket history includes router reboot, cable check, router reset. Escalated; prior troubleshooting preserved in handover.

## Safety Design

- **Local corpus only**: Support articles are the only knowledge source. No external data sources.
- **No invented facts**: Customer/account facts are read from SQLite. Gemini never infers account information.
- **Citation validation**: Every resolution requires valid evidence citations. Fabricated citations trigger fallback.
- **Targeted follow-ups**: Missing information produces a single targeted question, not general clarification.
- **Deterministic safety**: Security, contradiction, unsupported, and repeated-fault cases are escalated by rules, not LLM discretion.
- **Graceful degradation**: Gemini unavailability or malformed output result in safe fallback behavior, never invented responses.
- **No chain-of-thought**: Internal reasoning is not exposed to users.
- **Credential safety**: API credentials are read from the environment and never committed to the repository.

## Fallback Behavior

If Gemini is unavailable or returns invalid output, the application provides a safe fallback response:

- Determines the appropriate response type (resolution, follow-up, or escalation) using deterministic routing.
- For resolutions, uses a templated response grounded in the retrieved evidence.
- For escalations, includes the same handover structure with established facts and prior troubleshooting.
- Never invents content or contact information.
- Clearly signals when a human agent should review the response.

## Tests

```bash
python -m pytest -q
```

The test suite (32 tests) covers:

- Normal resolution with grounded billing citation
- Missing diagnostic detail producing targeted follow-up
- Known outage producing grounded resolution
- Unknown/security charge triggering escalation
- Contradictory payment claim triggering escalation
- Repeated troubleshooting exhaustion triggering escalation
- Unsupported request (non-telecom) triggering escalation
- Prior conversation troubleshooting preserved in handover
- Current customer message excluded from troubleshooting attempted
- Follow-up bounded to prevent infinite loops
- Valid Gemini grounded resolution accepted
- Invalid/fabricated Gemini output rejected
- API endpoint behavior under normal and error conditions
