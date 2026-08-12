# FinSight

FinSight is an MCP-powered payments analytics service. It keeps financial data access behind bounded, auditable tools so an AI host can retrieve facts without generating or executing raw SQL.

This first slice includes:

- deterministic synthetic merchant and transaction data;
- `query_transactions`, `get_merchant_summary`, and `detect_anomalies` MCP tools;
- the same operations as documented REST endpoints;
- a small rule-based `/api/chat` baseline that returns grounded data alongside every answer.

## Run locally

Requires Python 3.10+.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m app.seed --rows 25000
py -m uvicorn app.api:app --reload
```

Open <http://127.0.0.1:8000/docs>. The Streamable HTTP MCP endpoint is at `http://127.0.0.1:8000/mcp`.

Try the grounded chat baseline:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/chat `
  -ContentType application/json `
  -Body '{"question":"Which merchants had unusual chargeback spikes?"}'
```

Run the standard-library test suite:

```powershell
py -m unittest
```

## Current boundary

SQLite keeps the demo zero-setup. The analytics module is the single data-access boundary, so PostgreSQL can replace it without changing the REST or MCP contracts. The chat route is intentionally deterministic until an LLM provider is selected; it does not pretend to understand arbitrary questions.

Next useful slice: PostgreSQL plus an actual tool-calling orchestrator, then the React chart UI.
