# QueueStorm Investigator Runbook

Copy-paste commands for running, testing, and verifying the service.

## 1. Install locally

```bash
cd queuestorm-investigator
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 2. Run locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 3. Run tests

Open another terminal:

```bash
cd queuestorm-investigator
source .venv/bin/activate
pytest -q
```

Expected result:

```text
26 passed
```

## 4. Call health endpoint

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## 5. Call analyze-ticket endpoint with sample file

```bash
curl -X POST http://localhost:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  -d @samples/sample_input.json
```

## 6. Call analyze-ticket endpoint with inline JSON

```bash
curl -X POST http://localhost:8000/analyze-ticket \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_id": "TKT-LOCAL-001",
    "complaint": "I paid my electricity bill 850 taka but it deducted twice from my account.",
    "language": "en",
    "channel": "in_app_chat",
    "user_type": "customer",
    "transaction_history": [
      {
        "transaction_id": "TXN-10001",
        "timestamp": "2026-04-14T08:15:30Z",
        "type": "payment",
        "amount": 850,
        "counterparty": "BILLER-DESCO",
        "status": "completed"
      },
      {
        "transaction_id": "TXN-10002",
        "timestamp": "2026-04-14T08:15:42Z",
        "type": "payment",
        "amount": 850,
        "counterparty": "BILLER-DESCO",
        "status": "completed"
      }
    ]
  }'
```

## 7. Run with Docker

```bash
cd queuestorm-investigator
docker build -t queuestorm-investigator .
docker run --rm -p 8000:8000 --env-file .env.example queuestorm-investigator
```

Then verify:

```bash
curl http://localhost:8000/health
```

## 8. Run with Docker Compose

```bash
cd queuestorm-investigator
docker compose up --build
```

## 9. Submission checklist

```bash
pytest -q
curl http://localhost:8000/health
curl -X POST http://localhost:8000/analyze-ticket -H "Content-Type: application/json" -d @samples/sample_input.json
```

Before submission, confirm:

- `/health` returns `{"status":"ok"}`.
- `/analyze-ticket` returns all required fields.
- No customer reply asks for PIN, OTP, password, verification code, or full card number.
- No reply confirms refund, reversal, recovery, or account unblock.
- `.env` or real secrets are not committed.
