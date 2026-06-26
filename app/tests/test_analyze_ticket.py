import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def analyze(payload):
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 200
    return response.json()


def test_no_transaction_history():
    body = analyze({"ticket_id": "TKT-NO-TX", "complaint": "I need refund for 500 taka", "transaction_history": []})
    assert body["relevant_transaction_id"] is None
    assert body["evidence_verdict"] == "insufficient_data"


def test_wrong_transfer_consistent():
    body = analyze({
        "ticket_id": "TKT-WRONG",
        "complaint": "I sent 5000 taka to wrong number",
        "transaction_history": [
            {"transaction_id": "TXN-W", "timestamp": "2026-04-14T14:00:00Z", "type": "transfer", "amount": 5000, "counterparty": "+8801711111111", "status": "completed"}
        ],
    })
    assert body["case_type"] == "wrong_transfer"
    assert body["evidence_verdict"] == "consistent"
    assert body["department"] == "dispute_resolution"
    assert body["human_review_required"] is True


def test_wrong_transfer_insufficient():
    body = analyze({"ticket_id": "TKT-WI", "complaint": "I sent 5000 taka to wrong number", "transaction_history": []})
    assert body["case_type"] == "wrong_transfer"
    assert body["evidence_verdict"] == "insufficient_data"
    assert body["human_review_required"] is True


def test_payment_failed_consistent():
    body = analyze({
        "ticket_id": "TKT-PF",
        "complaint": "Payment failed but 1200 taka deducted",
        "transaction_history": [
            {"transaction_id": "TXN-PF", "timestamp": "2026-04-14T16:00:00Z", "type": "payment", "amount": 1200, "counterparty": "MERCHANT", "status": "failed"}
        ],
    })
    assert body["case_type"] == "payment_failed"
    assert body["evidence_verdict"] == "consistent"
    assert body["department"] == "payments_ops"


def test_payment_failed_inconsistent():
    body = analyze({
        "ticket_id": "TKT-PI",
        "complaint": "Payment failed but 1200 taka deducted",
        "transaction_history": [
            {"transaction_id": "TXN-PI", "timestamp": "2026-04-14T16:00:00Z", "type": "payment", "amount": 1200, "counterparty": "MERCHANT", "status": "completed"}
        ],
    })
    assert body["case_type"] == "payment_failed"
    assert body["evidence_verdict"] == "inconsistent"
    assert body["human_review_required"] is True


def test_refund_request():
    body = analyze({
        "ticket_id": "TKT-R",
        "complaint": "Please refund 500 taka for my merchant payment",
        "transaction_history": [
            {"transaction_id": "TXN-R", "timestamp": "2026-04-14T13:00:00Z", "type": "payment", "amount": 500, "counterparty": "MERCHANT", "status": "completed"}
        ],
    })
    assert body["case_type"] == "refund_request"
    assert body["evidence_verdict"] == "consistent"
    assert body["department"] == "customer_support"


def test_duplicate_payment():
    body = analyze({
        "ticket_id": "TKT-DUP",
        "complaint": "Electricity bill 850 taka deducted twice",
        "transaction_history": [
            {"transaction_id": "TXN-D1", "timestamp": "2026-04-14T08:15:30Z", "type": "payment", "amount": 850, "counterparty": "BILLER", "status": "completed"},
            {"transaction_id": "TXN-D2", "timestamp": "2026-04-14T08:15:42Z", "type": "payment", "amount": 850, "counterparty": "BILLER", "status": "completed"},
        ],
    })
    assert body["case_type"] == "duplicate_payment"
    assert body["relevant_transaction_id"] == "TXN-D2"
    assert body["evidence_verdict"] == "consistent"


def test_merchant_settlement_delay():
    body = analyze({
        "ticket_id": "TKT-M",
        "complaint": "I am a merchant. My 15000 taka settlement is pending.",
        "channel": "merchant_portal",
        "user_type": "merchant",
        "transaction_history": [
            {"transaction_id": "TXN-M", "timestamp": "2026-04-13T18:00:00Z", "type": "settlement", "amount": 15000, "counterparty": "MERCHANT-SELF", "status": "pending"}
        ],
    })
    assert body["case_type"] == "merchant_settlement_delay"
    assert body["department"] == "merchant_operations"
    assert body["evidence_verdict"] == "consistent"


def test_agent_cash_in_issue():
    body = analyze({
        "ticket_id": "TKT-A",
        "complaint": "I did cash in 2000 taka from agent but balance not added",
        "transaction_history": [
            {"transaction_id": "TXN-A", "timestamp": "2026-04-14T09:30:00Z", "type": "cash_in", "amount": 2000, "counterparty": "AGENT-318", "status": "pending"}
        ],
    })
    assert body["case_type"] == "agent_cash_in_issue"
    assert body["department"] == "agent_operations"
    assert body["human_review_required"] is True


def test_bangla_complaint():
    body = analyze({
        "ticket_id": "TKT-BN",
        "complaint": "আমি এজেন্টের কাছে ২০০০ টাকা ক্যাশ ইন করেছি কিন্তু ব্যালেন্সে টাকা আসেনি",
        "language": "bn",
        "transaction_history": [
            {"transaction_id": "TXN-BN", "timestamp": "2026-04-14T09:30:00Z", "type": "cash_in", "amount": 2000, "counterparty": "AGENT-318", "status": "pending"}
        ],
    })
    assert body["case_type"] == "agent_cash_in_issue"
    assert body["relevant_transaction_id"] == "TXN-BN"
    assert "আপনার" in body["customer_reply"]


def test_banglish_complaint():
    body = analyze({
        "ticket_id": "TKT-BL",
        "complaint": "Ami bhul number e 1000 taka pathaisi",
        "language": "mixed",
        "transaction_history": [
            {"transaction_id": "TXN-BL", "timestamp": "2026-04-14T09:30:00Z", "type": "transfer", "amount": 1000, "counterparty": "+8801711111111", "status": "completed"}
        ],
    })
    assert body["case_type"] == "wrong_transfer"
    assert body["evidence_verdict"] == "consistent"


def test_public_sample_cases_functional_match():
    sample_path = Path(__file__).resolve().parents[2] / "docs" / "SUST_Preli_Sample_Cases.json"
    data = json.loads(sample_path.read_text(encoding="utf-8"))
    for case in data["cases"]:
        body = analyze(case["input"])
        expected = case["expected_output"]
        assert body["ticket_id"] == expected["ticket_id"]
        assert body["relevant_transaction_id"] == expected["relevant_transaction_id"]
        assert body["evidence_verdict"] == expected["evidence_verdict"]
        assert body["case_type"] == expected["case_type"]
        assert body["department"] == expected["department"]
