from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class EvidenceVerdict(str, Enum):
    consistent = "consistent"
    inconsistent = "inconsistent"
    insufficient_data = "insufficient_data"


class CaseType(str, Enum):
    wrong_transfer = "wrong_transfer"
    payment_failed = "payment_failed"
    refund_request = "refund_request"
    duplicate_payment = "duplicate_payment"
    merchant_settlement_delay = "merchant_settlement_delay"
    agent_cash_in_issue = "agent_cash_in_issue"
    phishing_or_social_engineering = "phishing_or_social_engineering"
    other = "other"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Department(str, Enum):
    customer_support = "customer_support"
    dispute_resolution = "dispute_resolution"
    payments_ops = "payments_ops"
    merchant_operations = "merchant_operations"
    agent_operations = "agent_operations"
    fraud_risk = "fraud_risk"


class AnalyzeTicketResponse(BaseModel):
    ticket_id: str
    relevant_transaction_id: Optional[str]
    evidence_verdict: EvidenceVerdict
    case_type: CaseType
    severity: Severity
    department: Department
    agent_summary: str
    recommended_next_action: str
    customer_reply: str
    human_review_required: bool
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason_codes: List[str] = Field(default_factory=list)

    @field_validator("reason_codes")
    @classmethod
    def dedupe_reason_codes(cls, values: List[str]) -> List[str]:
        seen = set()
        out = []
        for value in values:
            if value not in seen:
                out.append(value)
                seen.add(value)
        return out
