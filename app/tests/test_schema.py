from fastapi.testclient import TestClient

from app.main import app
from app.schemas.response import CaseType, Department, EvidenceVerdict, Severity

client = TestClient(app)

VALID_PAYLOAD = {
    "ticket_id": "TKT-SCHEMA",
    "complaint": "Payment failed but 1200 taka deducted.",
    "language": "en",
    "transaction_history": [
        {
            "transaction_id": "TXN-S1",
            "timestamp": "2026-04-14T10:00:00Z",
            "type": "payment",
            "amount": 1200,
            "counterparty": "MERCHANT-1",
            "status": "failed",
        }
    ],
}

REQUIRED_RESPONSE_FIELDS = {
    "ticket_id",
    "relevant_transaction_id",
    "evidence_verdict",
    "case_type",
    "severity",
    "department",
    "agent_summary",
    "recommended_next_action",
    "customer_reply",
    "human_review_required",
    "confidence",
    "reason_codes",
}


def test_valid_analyze_ticket_schema():
    response = client.post("/analyze-ticket", json=VALID_PAYLOAD)
    assert response.status_code == 200
    body = response.json()
    assert REQUIRED_RESPONSE_FIELDS.issubset(body.keys())
    assert body["ticket_id"] == VALID_PAYLOAD["ticket_id"]
    assert 0 <= body["confidence"] <= 1
    assert isinstance(body["reason_codes"], list)


def test_missing_ticket_id_is_rejected():
    payload = VALID_PAYLOAD.copy()
    payload.pop("ticket_id")
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 422
    assert "error" in response.json()


def test_empty_complaint_is_rejected():
    payload = VALID_PAYLOAD.copy()
    payload["complaint"] = "   "
    response = client.post("/analyze-ticket", json=payload)
    assert response.status_code == 422


def test_malformed_json_is_controlled():
    response = client.post("/analyze-ticket", data="{not-json", headers={"Content-Type": "application/json"})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"


def test_all_enum_values_are_valid():
    body = client.post("/analyze-ticket", json=VALID_PAYLOAD).json()
    assert body["evidence_verdict"] in {item.value for item in EvidenceVerdict}
    assert body["case_type"] in {item.value for item in CaseType}
    assert body["severity"] in {item.value for item in Severity}
    assert body["department"] in {item.value for item in Department}
