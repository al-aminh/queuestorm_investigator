from typing import Iterable, Optional

from app.core.transaction_matcher import MatchResult
from app.schemas.request import Transaction
from app.schemas.response import CaseType, EvidenceVerdict, Severity
from app.utils.numbers import extract_amounts

_ORDER = {
    Severity.low: 0,
    Severity.medium: 1,
    Severity.high: 2,
    Severity.critical: 3,
}


def _max_severity(a: Severity, b: Severity) -> Severity:
    return a if _ORDER[a] >= _ORDER[b] else b


def _amount_from_context(complaint: str, match: MatchResult) -> float:
    if match.transaction:
        return float(match.transaction.amount)
    amounts = extract_amounts(complaint)
    return max(amounts) if amounts else 0.0


def determine_severity(case_type: CaseType, evidence_verdict: EvidenceVerdict, complaint: str, match: MatchResult) -> Severity:
    amount = _amount_from_context(complaint, match)

    if case_type == CaseType.phishing_or_social_engineering:
        return Severity.critical

    if case_type == CaseType.other:
        return Severity.medium if evidence_verdict in {EvidenceVerdict.inconsistent, EvidenceVerdict.insufficient_data} and amount >= 5000 else Severity.low

    if case_type == CaseType.wrong_transfer:
        severity = Severity.medium if evidence_verdict != EvidenceVerdict.consistent else Severity.high
    elif case_type == CaseType.duplicate_payment:
        severity = Severity.high
    elif case_type == CaseType.payment_failed:
        severity = Severity.high if evidence_verdict == EvidenceVerdict.consistent else Severity.medium
    elif case_type == CaseType.refund_request:
        severity = Severity.low if amount and amount < 1000 and evidence_verdict == EvidenceVerdict.consistent else Severity.medium
        if amount >= 5000:
            severity = Severity.high
    elif case_type == CaseType.merchant_settlement_delay:
        severity = Severity.medium
        if amount >= 50000:
            severity = Severity.high
    elif case_type == CaseType.agent_cash_in_issue:
        severity = Severity.high if evidence_verdict != EvidenceVerdict.insufficient_data else Severity.medium
        if amount >= 5000:
            severity = Severity.high
    else:
        severity = Severity.medium

    # High-value customer/agent disputes are critical, but merchant settlement uses business SLA severity.
    if amount >= 10000 and case_type not in {CaseType.merchant_settlement_delay}:
        severity = Severity.critical

    if evidence_verdict in {EvidenceVerdict.inconsistent, EvidenceVerdict.insufficient_data} and case_type != CaseType.other:
        severity = _max_severity(severity, Severity.medium)

    return severity
