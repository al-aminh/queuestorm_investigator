from collections import Counter
from typing import List, Tuple

from app.core.transaction_matcher import MatchResult, find_duplicate_payment_group
from app.schemas.request import Transaction
from app.schemas.response import CaseType, EvidenceVerdict
from app.utils.text import normalize_counterparty, normalize_text


def _established_recipient_pattern(tx: Transaction, transactions: List[Transaction]) -> bool:
    cp = normalize_counterparty(tx.counterparty)
    if not cp:
        return False
    prior_same = [
        item for item in transactions
        if item.transaction_id != tx.transaction_id
        and item.type.value == "transfer"
        and normalize_counterparty(item.counterparty) == cp
        and item.status.value == "completed"
    ]
    return len(prior_same) >= 2


def determine_evidence(complaint: str, transactions: List[Transaction], case_type: CaseType, match: MatchResult) -> Tuple[EvidenceVerdict, List[str]]:
    reasons: List[str] = []
    text = normalize_text(complaint)

    if case_type == CaseType.phishing_or_social_engineering:
        return EvidenceVerdict.insufficient_data, ["insufficient_data", "phishing_signal"]

    if not transactions:
        return EvidenceVerdict.insufficient_data, ["no_transaction_history", "insufficient_data"]

    if case_type == CaseType.duplicate_payment:
        group = match.duplicate_group or find_duplicate_payment_group(transactions)
        if group:
            return EvidenceVerdict.consistent, ["evidence_consistent", "duplicate_payment"]
        if match.transaction:
            return EvidenceVerdict.inconsistent, ["evidence_inconsistent", "duplicate_payment"]
        return EvidenceVerdict.insufficient_data, ["insufficient_data"]

    tx = match.transaction
    if tx is None:
        return EvidenceVerdict.insufficient_data, ["insufficient_data"]

    tx_type = tx.type.value
    status = tx.status.value

    if case_type == CaseType.wrong_transfer:
        if tx_type == "transfer" and status == "completed":
            if _established_recipient_pattern(tx, transactions):
                return EvidenceVerdict.inconsistent, ["evidence_inconsistent", "established_recipient_pattern"]
            return EvidenceVerdict.consistent, ["evidence_consistent"]
        return EvidenceVerdict.inconsistent, ["evidence_inconsistent"]

    if case_type == CaseType.payment_failed:
        if tx_type == "payment" and status in {"failed", "pending"}:
            return EvidenceVerdict.consistent, ["evidence_consistent"]
        if tx_type == "payment" and status == "completed":
            return EvidenceVerdict.inconsistent, ["evidence_inconsistent"]
        return EvidenceVerdict.insufficient_data, ["insufficient_data"]

    if case_type == CaseType.refund_request:
        not_received = any(phrase in text for phrase in ["not received", "didn't receive", "did not receive", "paini", "পাইনি", "পায়নি", "পায়নি"])
        if (tx_type == "refund" or status == "reversed") and not_received:
            return EvidenceVerdict.inconsistent, ["evidence_inconsistent"]
        if tx_type in {"payment", "refund"}:
            return EvidenceVerdict.consistent, ["evidence_consistent"]
        return EvidenceVerdict.insufficient_data, ["insufficient_data"]

    if case_type == CaseType.merchant_settlement_delay:
        if tx_type == "settlement" and status in {"pending", "failed"}:
            return EvidenceVerdict.consistent, ["evidence_consistent"]
        if tx_type == "settlement" and status in {"completed", "reversed"}:
            return EvidenceVerdict.inconsistent, ["evidence_inconsistent"]
        return EvidenceVerdict.insufficient_data, ["insufficient_data"]

    if case_type == CaseType.agent_cash_in_issue:
        if tx_type == "cash_in" and status in {"pending", "failed"}:
            return EvidenceVerdict.consistent, ["evidence_consistent"]
        if tx_type == "cash_in" and status == "completed":
            return EvidenceVerdict.inconsistent, ["evidence_inconsistent"]
        return EvidenceVerdict.insufficient_data, ["insufficient_data"]

    return EvidenceVerdict.insufficient_data, ["insufficient_data"]
