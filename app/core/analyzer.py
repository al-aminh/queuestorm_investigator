from typing import List

from app.core.classifier import classify_case
from app.core.evidence import determine_evidence
from app.core.response_builder import build_confidence, build_text_fields
from app.core.router import route_department
from app.core.safety import analyze_safety
from app.core.severity import determine_severity
from app.core.transaction_matcher import match_transaction
from app.schemas.request import AnalyzeTicketRequest, Transaction
from app.schemas.response import AnalyzeTicketResponse, CaseType, Department, EvidenceVerdict, Severity


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    output = []
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output


def _has_pending_match(match) -> bool:
    return bool(match.transaction and match.transaction.status.value == "pending")


def _max_amount(match, req: AnalyzeTicketRequest) -> float:
    if match.transaction:
        return float(match.transaction.amount)
    amounts = [float(tx.amount) for tx in (req.transaction_history or [])]
    return max(amounts) if amounts else 0.0


def determine_human_review(
    req: AnalyzeTicketRequest,
    case_type: CaseType,
    verdict: EvidenceVerdict,
    severity: Severity,
    match,
    safety_reasons: List[str],
    reason_codes: List[str],
) -> bool:
    if "prompt_injection_ignored" in safety_reasons:
        return True
    if case_type == CaseType.phishing_or_social_engineering:
        return True
    if case_type == CaseType.agent_cash_in_issue:
        return True
    if case_type == CaseType.duplicate_payment and verdict == EvidenceVerdict.consistent:
        return True
    if case_type == CaseType.wrong_transfer:
        # If multiple transactions match and we only need a clarification, do not create a dispute yet.
        return not match.ambiguous
    if case_type == CaseType.refund_request:
        return verdict != EvidenceVerdict.consistent or _max_amount(match, req) >= 5000
    if severity == Severity.critical:
        return True
    if _has_pending_match(match) and case_type not in {CaseType.merchant_settlement_delay}:
        return True
    if verdict == EvidenceVerdict.inconsistent:
        return True
    if verdict == EvidenceVerdict.insufficient_data:
        return case_type not in {CaseType.other} and not match.ambiguous
    if "ambiguous_match" in reason_codes:
        return False
    return False


def analyze_ticket(req: AnalyzeTicketRequest) -> AnalyzeTicketResponse:
    transactions = req.transaction_history or []
    safety = analyze_safety(req.complaint)
    classification = classify_case(
        req.complaint,
        safety,
        user_type=req.user_type.value if req.user_type else None,
        channel=req.channel.value if req.channel else None,
    )

    match = match_transaction(req.complaint, transactions, classification.case_type)
    verdict, evidence_reasons = determine_evidence(req.complaint, transactions, classification.case_type, match)
    severity = determine_severity(classification.case_type, verdict, req.complaint, match)
    department = route_department(classification.case_type, verdict, severity)

    reason_codes = _dedupe([
        *classification.reason_codes,
        *safety.reason_codes,
        *match.reason_codes,
        *evidence_reasons,
    ])

    human_review = determine_human_review(
        req,
        classification.case_type,
        verdict,
        severity,
        match,
        safety.reason_codes,
        reason_codes,
    )
    if human_review:
        reason_codes.append("human_review_required")
    reason_codes = _dedupe(reason_codes)

    agent_summary, next_action, customer_reply = build_text_fields(req, classification.case_type, verdict, match, severity)
    confidence = build_confidence(classification.case_type, verdict, match, classification.reason_codes)

    return AnalyzeTicketResponse(
        ticket_id=req.ticket_id,
        relevant_transaction_id=match.transaction.transaction_id if match.transaction else None,
        evidence_verdict=verdict,
        case_type=classification.case_type,
        severity=severity,
        department=department,
        agent_summary=agent_summary,
        recommended_next_action=next_action,
        customer_reply=customer_reply,
        human_review_required=human_review,
        confidence=round(max(0.0, min(1.0, confidence)), 2),
        reason_codes=reason_codes,
    )
