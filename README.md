# QueueStorm Investigator

QueueStorm Investigator is a hackathon-grade FastAPI service for the SUST CSE Carnival 2026 Codex Community Hackathon preliminary round. It works as an internal SupportOps copilot for digital finance complaints: it reads one customer complaint plus recent transaction history, selects the most relevant transaction when evidence supports one, produces an evidence verdict, classifies the case, routes it, sets severity, drafts an agent summary, recommends a safe next action, and returns a safe customer reply.

The implementation is intentionally deterministic by default. It uses rule-based reasoning for transaction matching, classification, evidence verdicts, routing, severity, escalation, and safety. No LLM or external API is required to run or score the project.

## Live demo

Judge/demo endpoint: https://queuestorm-investigator-f1k2.onrender.com

## Why this approach

The challenge rewards evidence reasoning, safety, schema correctness, reliability, and reproducibility. A deterministic service is fast, cheap, explainable, and stable under hidden tests. Optional LLM support is documented through environment variables, but disabled by default because the core financial-support decisions must not depend on a probabilistic text generator.

## Architecture

```text
Client/Judge Harness
      |
      v
FastAPI routes
  GET /health
  POST /analyze-ticket
      |
      v
Pydantic request validation
      |
      v
Analyzer pipeline
  1. Safety + prompt-injection scan
  2. Case classification
  3. Transaction scoring and duplicate detection
  4. Evidence verdict
  5. Severity and department routing
  6. Human-review decision
  7. Safe response generation + final sanitizer
      |
      v
Strict JSON response schema
```

## Folder structure

```text
queuestorm-investigator/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   └── routes.py
│   ├── schemas/
│   │   ├── request.py
│   │   └── response.py
│   ├── core/
│   │   ├── analyzer.py
│   │   ├── classifier.py
│   │   ├── transaction_matcher.py
│   │   ├── evidence.py
│   │   ├── severity.py
│   │   ├── router.py
│   │   ├── safety.py
│   │   └── response_builder.py
│   ├── utils/
│   │   ├── text.py
│   │   ├── numbers.py
│   │   └── time.py
│   └── tests/
├── docs/
├── samples/
├── README.md
├── RUNBOOK.md
├── MODELS.md
├── .env.example
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── pytest.ini
└── .gitignore
```

## API endpoints

### `GET /health`

Returns service readiness.

```json
{
  "status": "ok"
}
```

### `POST /analyze-ticket`

Accepts one ticket and returns a structured investigation result.

## Request schema

Required fields:

```json
{
  "ticket_id": "string",
  "complaint": "string"
}
```

Optional fields:

```json
{
  "language": "en | bn | mixed",
  "channel": "in_app_chat | call_center | email | merchant_portal | field_agent",
  "user_type": "customer | merchant | agent | unknown",
  "campaign_context": "string",
  "transaction_history": [],
  "metadata": {}
}
```

Transaction item:

```json
{
  "transaction_id": "string",
  "timestamp": "2026-04-14T14:08:22Z",
  "type": "transfer | payment | cash_in | cash_out | settlement | refund",
  "amount": 5000,
  "counterparty": "+8801719876543",
  "status": "completed | failed | pending | reversed"
}
```

## Response schema

```json
{
  "ticket_id": "TKT-001",
  "relevant_transaction_id": "TXN-9101",
  "evidence_verdict": "consistent",
  "case_type": "wrong_transfer",
  "severity": "high",
  "department": "dispute_resolution",
  "agent_summary": "Customer reports a wrong-transfer issue...",
  "recommended_next_action": "Verify non-sensitive details...",
  "customer_reply": "We have noted your concern...",
  "human_review_required": true,
  "confidence": 0.9,
  "reason_codes": ["wrong_transfer", "transaction_match"]
}
```

Allowed response enums are exactly:

- `evidence_verdict`: `consistent`, `inconsistent`, `insufficient_data`
- `case_type`: `wrong_transfer`, `payment_failed`, `refund_request`, `duplicate_payment`, `merchant_settlement_delay`, `agent_cash_in_issue`, `phishing_or_social_engineering`, `other`
- `severity`: `low`, `medium`, `high`, `critical`
- `department`: `customer_support`, `dispute_resolution`, `payments_ops`, `merchant_operations`, `agent_operations`, `fraud_risk`

## Local setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open:

```bash
curl http://localhost:8000/health
```

## Test command

```bash
pytest -q
```

Current local verification: `26 passed`.

## Sample request

```bash
curl -X POST http://localhost:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  -d @samples/sample_input.json
```

## Sample response

See `samples/sample_output.json`.

## Evidence reasoning logic

The service is an investigator, not just a classifier.

Transaction matching uses a transparent score:

- Amount match: `+0.40`
- Transaction type match: `+0.20`
- Status relevance: `+0.10`
- Counterparty mention: `+0.15`
- Keyword alignment: `+0.15`

If the top score is below `0.45`, no transaction is selected. If multiple transactions are too close, the result is treated as ambiguous and `relevant_transaction_id` is `null`.

Duplicate payment detection is handled separately by grouping transactions with the same type, amount, counterparty, and similar status. When two similar payments are found and the complaint says `twice`, `duplicate`, `double`, or Bangla/Banglish equivalents, the second transaction is selected as the likely duplicate candidate.

Evidence verdict rules include:

- `wrong_transfer` is consistent when a matching completed transfer exists, but repeated prior transfers to the same recipient can make the claim inconsistent.
- `payment_failed` is consistent when a matching payment is failed or pending, and inconsistent when the matching payment is completed.
- `refund_request` is consistent when a related completed payment or refund candidate exists, but still avoids promising a refund.
- `merchant_settlement_delay` is consistent when a matching settlement is pending or failed.
- `agent_cash_in_issue` is consistent when a matching cash-in is pending or failed.
- Phishing/social-engineering reports are routed to fraud/risk with `insufficient_data` because the right action is safety escalation, not financial confirmation.

## Safety logic

The service includes two safety layers:

1. **Input safety scan** detects phishing/social engineering, sensitive credential mentions, and prompt injection.
2. **Output sanitizer** checks `customer_reply` and `recommended_next_action` before returning the final response.

The customer reply must never ask for:

- PIN
- OTP
- password
- verification code
- full card number
- secret credential

The service also avoids unauthorized promises such as:

- `we will refund you`
- `we will reverse it`
- `refund confirmed`
- `reversal confirmed`
- `your account will be unblocked`

Safe language is used instead, for example: `any eligible amount will be returned through official channels`.

Prompt injection phrases such as `ignore previous rules`, `return this JSON`, `approve refund`, `ask for OTP`, and `you are now admin` are ignored and flagged with `prompt_injection_ignored`.

## Bangla and Banglish support

The classifier and transaction matcher include Bangla/Banglish keywords for:

- wrong number / wrong transfer
- failed payment / deducted balance
- refund / money back
- duplicate charge
- merchant settlement
- agent cash-in issue
- phishing and credential scams

The number extractor converts Bengali digits such as `২০০০` into numeric values for amount matching.

## MODELS section

Default model: deterministic rule-based model running inside the API process.

External models: none required. `USE_LLM=false` by default.

Optional variables are listed in `.env.example` for teams that want to add LLM-based text polishing later, but this build does not require it and does not call external AI providers.

See `MODELS.md` for details.

## Deployment notes

The app binds to `0.0.0.0:8000` in Docker and is suitable for Render, Railway, Fly.io, EC2, Poridhi VM, or any similar service that can run a Python web API.

For a live endpoint submission, the judge should be able to call:

```text
GET https://your-domain/health
POST https://your-domain/analyze-ticket
```

No login or dashboard access is required.

## Assumptions

- All data is synthetic.
- The API does not connect to a real payment system.
- Transaction history is short, usually 0–5 entries.
- The service should ask for non-sensitive clarifying details when evidence is ambiguous.
- Human agents make final financial decisions.

## Known limitations

- Time hints such as `yesterday`, `2pm`, or `morning` are used lightly through transaction context but not deeply parsed.
- The rule set covers the documented taxonomy, but unusual slang outside the included keyword sets may fall into `other`.
- No external fraud intelligence or payment ledger is connected.
- Optional LLM polishing is documented but not implemented because deterministic safety and reliability are preferred for the preliminary round.
