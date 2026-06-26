from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Language(str, Enum):
    en = "en"
    bn = "bn"
    mixed = "mixed"


class Channel(str, Enum):
    in_app_chat = "in_app_chat"
    call_center = "call_center"
    email = "email"
    merchant_portal = "merchant_portal"
    field_agent = "field_agent"


class UserType(str, Enum):
    customer = "customer"
    merchant = "merchant"
    agent = "agent"
    unknown = "unknown"


class TransactionType(str, Enum):
    transfer = "transfer"
    payment = "payment"
    cash_in = "cash_in"
    cash_out = "cash_out"
    settlement = "settlement"
    refund = "refund"


class TransactionStatus(str, Enum):
    completed = "completed"
    failed = "failed"
    pending = "pending"
    reversed = "reversed"


class Transaction(BaseModel):
    transaction_id: str = Field(..., min_length=1)
    timestamp: str = Field(..., min_length=1, description="ISO 8601 timestamp")
    type: TransactionType
    amount: float = Field(..., ge=0)
    counterparty: str = Field(..., min_length=1)
    status: TransactionStatus

    @field_validator("transaction_id", "timestamp", "counterparty")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field cannot be empty")
        return value


class AnalyzeTicketRequest(BaseModel):
    ticket_id: str = Field(..., min_length=1)
    complaint: str = Field(..., min_length=1)
    language: Optional[Language] = None
    channel: Optional[Channel] = None
    user_type: Optional[UserType] = None
    campaign_context: Optional[str] = None
    transaction_history: Optional[List[Transaction]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    @field_validator("ticket_id", "complaint")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field cannot be empty")
        return value
