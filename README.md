# NexusTiQ24 — Customer Support Resolution Assistant

> TODO: Confirm the organizer-required `TRACK_ID` value before final submission. The supplied hackathon material appears inconsistent, so this repository intentionally does not finalize that line yet.

A local, agent-facing MVP for a fictional broadband and mobile support desk. It uses customer account records, ticket history, conversation context, and local support articles to produce a grounded resolution, one targeted follow-up question, or a human handover.

## Start

```bash
pip install -r requirements.txt
python app.py
```

Open [http://localhost:8000](http://localhost:8000). The app seeds its fictional SQLite data on first start.

## Gemini configuration

Set `GEMINI_API_KEY` in the environment before starting the app. Gemini is used only for embeddings (`gemini-embedding-001`) and bounded resolution drafting. It is never stored in the repository.

Without a key or if Gemini is unavailable, the application stays operational with local keyword retrieval and deterministic, safe outcomes.

## Demo cases

- **Asha Raman (C001):** higher invoice with account-backed explanation.
- **Vikram Das (C002):** known broadband outage.
- **Meera Iyer (C003):** mobile data-plan question or unsupported request.
- **Rohan Shah (C004):** unknown charge; immediate security escalation.
- **Nila Bose (C005):** claimed payment contradicts overdue account record.
- **Arjun Rao (C006):** repeated broadband fault; prior troubleshooting is preserved in the handover.

## Safety design

- Local articles are the only knowledge corpus.
- A resolution must have valid retrieved-article citations.
- Customer/account facts are read from SQLite, not inferred by Gemini.
- Missing diagnostic detail produces one targeted question.
- Security, contradiction, unsupported, and repeated-fault cases are escalated.
- Gemini errors or malformed output result in a safe local fallback rather than invented content.

## Tests

```bash
python -m pytest -q
```

Tests cover normal resolution, missing details, known outage, unknown charge, contradictory payment, repeated troubleshooting, unsupported requests, and invalid Gemini-style responses.
