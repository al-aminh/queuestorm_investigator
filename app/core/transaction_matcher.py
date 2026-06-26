from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from app.schemas.request import Transaction
from app.schemas.response import CaseType
from app.utils.numbers import amount_matches, extract_amounts
from app.utils.text import normalize_counterparty, normalize_text
from app.utils.time import parse_iso_datetime

CASE_TO_TYPES: Dict[CaseType, set[str]] = {
    CaseType.wrong_transfer: {"transfer"},
    CaseType.payment_failed: {"payment"},
    CaseType.refund_request: {"payment", "refund"},
    CaseType.duplicate_payment: {"payment"},
    CaseType.merchant_settlement_delay: {"settlement"},
    CaseType.agent_cash_in_issue: {"cash_in"},
    CaseType.phishing_or_social_engineering: set(),
    CaseType.other: set(),
}

KEYWORD_ALIGNMENT = {
    CaseType.wrong_transfer: ["transfer", "sent", "wrong", "পাঠ", "ভুল"],
    CaseType.payment_failed: ["payment", "failed", "deduct", "পেমেন্ট", "কেটে"],
    CaseType.refund_request: ["refund", "money back", "ফেরত", "রিফান্ড"],
    CaseType.duplicate_payment: ["duplicate", "twice", "double", "দুইবার"],
    CaseType.merchant_settlement_delay: ["settlement", "merchant", "payout", "sales", "সেটেলমেন্ট"],
    CaseType.agent_cash_in_issue: ["cash in", "cash-in", "agent", "deposit", "ক্যাশ", "এজেন্ট"],
    CaseType.other: [],
    CaseType.phishing_or_social_engineering: [],
}


@dataclass
class TransactionScore:
    transaction: Transaction
    score: float
    reason_codes: List[str] = field(default_factory=list)


@dataclass
class MatchResult:
    transaction: Optional[Transaction]
    score: float
    reason_codes: List[str]
    ambiguous: bool = False
    duplicate_group: List[Transaction] = field(default_factory=list)


def _status_relevant(case_type: CaseType, tx: Transaction) -> bool:
    status = tx.status.value
    tx_type = tx.type.value
    if case_type == CaseType.wrong_transfer:
        return tx_type == "transfer" and status == "completed"
    if case_type == CaseType.payment_failed:
        return tx_type == "payment" and status in {"failed", "pending"}
    if case_type == CaseType.refund_request:
        return tx_type in {"payment", "refund"} and status in {"completed", "reversed", "pending"}
    if case_type == CaseType.duplicate_payment:
        return tx_type == "payment" and status in {"completed", "pending"}
    if case_type == CaseType.merchant_settlement_delay:
        return tx_type == "settlement" and status in {"pending", "failed"}
    if case_type == CaseType.agent_cash_in_issue:
        return tx_type == "cash_in" and status in {"pending", "failed", "completed"}
    return False


def _counterparty_mentioned(complaint: str, counterparty: str) -> bool:
    text = normalize_text(complaint)
    text_compact = normalize_counterparty(text)
    cp = normalize_counterparty(counterparty)
    if not cp:
        return False
    if cp in text_compact:
        return True
    # Phone numbers may be written as local suffixes or without country code.
    if len(cp) >= 8 and cp[-8:] in text_compact:
        return True
    if len(cp) >= 10 and cp[-10:] in text_compact:
        return True
    # Merchant/agent IDs may be partially referenced.
    alpha_num = cp.replace("+", "")
    return len(alpha_num) >= 6 and alpha_num in text_compact


def _keyword_aligned(complaint: str, case_type: CaseType, tx: Transaction) -> bool:
    text = normalize_text(complaint)
    if any(keyword in text for keyword in KEYWORD_ALIGNMENT.get(case_type, [])):
        return True
    return tx.type.value.replace("_", " ") in text


def score_transaction(complaint: str, tx: Transaction, case_type: CaseType) -> TransactionScore:
    score = 0.0
    reasons: List[str] = []
    amounts = extract_amounts(complaint)
    if amounts and any(amount_matches(amount, tx.amount) for amount in amounts):
        score += 0.40
        reasons.append("amount_match")

    expected_types = CASE_TO_TYPES.get(case_type, set())
    if tx.type.value in expected_types:
        score += 0.20
        reasons.append("type_match")

    if _status_relevant(case_type, tx):
        score += 0.10
        reasons.append("status_relevance")

    if _counterparty_mentioned(complaint, tx.counterparty):
        score += 0.15
        reasons.append("counterparty_match")

    if _keyword_aligned(complaint, case_type, tx):
        score += 0.15
        reasons.append("keyword_alignment")

    return TransactionScore(tx, round(min(score, 1.0), 4), reasons)


def _sort_transactions(transactions: Iterable[Transaction]) -> List[Transaction]:
    return sorted(transactions, key=lambda tx: parse_iso_datetime(tx.timestamp) or tx.timestamp)


def find_duplicate_payment_group(transactions: List[Transaction]) -> List[Transaction]:
    groups: Dict[Tuple[str, float, str], List[Transaction]] = defaultdict(list)
    for tx in transactions:
        if tx.type.value != "payment":
            continue
        if tx.status.value not in {"completed", "pending"}:
            continue
        key = (tx.type.value, round(float(tx.amount), 2), normalize_counterparty(tx.counterparty))
        groups[key].append(tx)
    duplicate_groups = [group for group in groups.values() if len(group) >= 2]
    if not duplicate_groups:
        return []
    # Prefer the largest, then the latest group.
    duplicate_groups.sort(key=lambda group: (len(group), parse_iso_datetime(_sort_transactions(group)[-1].timestamp) or parse_iso_datetime("1970-01-01T00:00:00Z")), reverse=True)
    return _sort_transactions(duplicate_groups[0])


def match_transaction(complaint: str, transactions: List[Transaction], case_type: CaseType, threshold: float = 0.45) -> MatchResult:
    if not transactions or case_type == CaseType.phishing_or_social_engineering:
        return MatchResult(None, 0.0, ["no_transaction_history"] if not transactions else ["weak_transaction_match"])

    if case_type == CaseType.duplicate_payment:
        group = find_duplicate_payment_group(transactions)
        if group:
            suspected_duplicate = group[-1]
            return MatchResult(suspected_duplicate, 0.95, ["transaction_match", "duplicate_payment", "amount_match", "type_match"], False, group)

    scores = [score_transaction(complaint, tx, case_type) for tx in transactions]
    scores.sort(key=lambda item: item.score, reverse=True)
    if not scores or scores[0].score < threshold:
        return MatchResult(None, scores[0].score if scores else 0.0, ["weak_transaction_match"])

    top = scores[0]
    contenders = [item for item in scores if item.score >= threshold and top.score - item.score <= 0.08]
    if len(contenders) > 1:
        return MatchResult(None, top.score, ["ambiguous_match", "weak_transaction_match"], True)

    return MatchResult(top.transaction, top.score, ["transaction_match", *top.reason_codes])
