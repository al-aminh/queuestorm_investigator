from typing import List

from app.core.safety import sanitize_output
from app.core.transaction_matcher import MatchResult
from app.schemas.request import AnalyzeTicketRequest, Transaction
from app.schemas.response import CaseType, Department, EvidenceVerdict, Severity
from app.utils.numbers import extract_amounts
from app.utils.text import infer_language


def _tx_ref(tx: Transaction | None) -> str:
    return tx.transaction_id if tx else "the relevant transaction"


def _amount_text(tx: Transaction | None, complaint: str) -> str:
    amount = tx.amount if tx else (max(extract_amounts(complaint)) if extract_amounts(complaint) else None)
    if amount is None:
        return "the reported amount"
    if float(amount).is_integer():
        return f"{int(amount)} BDT"
    return f"{amount} BDT"


def build_agent_summary(req: AnalyzeTicketRequest, case_type: CaseType, verdict: EvidenceVerdict, match: MatchResult) -> str:
    tx = match.transaction
    ref = _tx_ref(tx)
    amount = _amount_text(tx, req.complaint)
    if case_type == CaseType.wrong_transfer:
        if match.ambiguous:
            return f"Customer reports a transfer issue, but multiple transactions in the history plausibly match. Evidence is insufficient to identify the exact transaction."
        return f"Customer reports a wrong-transfer or transfer non-receipt issue for {amount}; {ref} is the best matching transaction. Evidence verdict is {verdict.value}."
    if case_type == CaseType.payment_failed:
        status = tx.status.value if tx else "unknown"
        return f"Customer reports a failed payment with possible balance deduction for {amount}; {ref} has status {status}."
    if case_type == CaseType.refund_request:
        return f"Customer requests refund review for {amount}; {ref} is the related transaction and eligibility must be checked by policy."
    if case_type == CaseType.duplicate_payment:
        if match.duplicate_group:
            ids = ", ".join(item.transaction_id for item in match.duplicate_group)
            return f"Customer reports duplicate payment. Similar payment transactions were detected: {ids}; {ref} is likely the duplicate candidate."
        return f"Customer reports duplicate payment, but the transaction history does not clearly show a duplicate pair."
    if case_type == CaseType.merchant_settlement_delay:
        status = tx.status.value if tx else "unknown"
        return f"Merchant reports settlement delay for {amount}; {ref} has status {status}."
    if case_type == CaseType.agent_cash_in_issue:
        status = tx.status.value if tx else "unknown"
        return f"Customer reports cash-in through an agent not reflected in balance; {ref} has status {status}."
    if case_type == CaseType.phishing_or_social_engineering:
        return "Customer reports a suspicious call, message, link, or credential request. Treat as a potential social engineering incident."
    return "Customer reports a vague or uncategorized money-related issue. The provided details are not enough for a specific transaction-backed conclusion."


def build_next_action(case_type: CaseType, verdict: EvidenceVerdict, match: MatchResult, severity: Severity, language: str) -> str:
    tx = match.transaction
    ref = _tx_ref(tx)
    if case_type == CaseType.wrong_transfer:
        if match.ambiguous or verdict == EvidenceVerdict.insufficient_data:
            return "Ask for the recipient number and exact time to identify the correct transfer before starting a dispute workflow."
        return f"Verify non-sensitive details for {ref} and route it through the wrong-transfer dispute workflow according to policy."
    if case_type == CaseType.payment_failed:
        return f"Check ledger and payment gateway status for {ref}; if an eligible deduction is found, handle it through the standard reversal workflow."
    if case_type == CaseType.refund_request:
        if severity == Severity.low and verdict == EvidenceVerdict.consistent:
            return "Explain that refund eligibility depends on merchant/platform policy and guide the customer through the official support process."
        return f"Review {ref} under dispute/refund policy and escalate for human approval before any financial action."
    if case_type == CaseType.duplicate_payment:
        return f"Verify duplicate evidence for {ref} with payments operations and biller/merchant records before taking any reversal action."
    if case_type == CaseType.merchant_settlement_delay:
        return f"Check settlement batch and payout status for {ref}; update the merchant with an official ETA if the batch is delayed."
    if case_type == CaseType.agent_cash_in_issue:
        return f"Escalate {ref} to agent operations to verify agent-side posting and customer balance reflection."
    if case_type == CaseType.phishing_or_social_engineering:
        return "Escalate to fraud_risk immediately, log the reported source if available, and advise the customer to use only official support channels."
    return "Ask the customer for the transaction ID, amount, approximate time, and a short description of what went wrong."


def build_customer_reply(req: AnalyzeTicketRequest, case_type: CaseType, verdict: EvidenceVerdict, match: MatchResult, severity: Severity, language: str) -> str:
    tx = match.transaction
    ref = _tx_ref(tx)
    if language == "bn":
        if case_type == CaseType.phishing_or_social_engineering:
            return "ধন্যবাদ আমাদের জানানো জন্য। আমরা কখনো আপনার পিন, ওটিপি বা পাসওয়ার্ড চাই না। এগুলো কারো সাথে শেয়ার করবেন না। আমাদের ফ্রড টিম বিষয়টি পর্যালোচনা করবে।"
        if case_type == CaseType.agent_cash_in_issue:
            return f"আপনার লেনদেন {ref} সম্পর্কে আমরা অবগত হয়েছি। আমাদের এজেন্ট অপারেশন্স দল বিষয়টি অফিসিয়ালভাবে যাচাই করবে। অনুগ্রহ করে কারো সাথে আপনার পিন বা ওটিপি শেয়ার করবেন না।"
        if verdict == EvidenceVerdict.insufficient_data:
            return "আপনাকে দ্রুত সহায়তা করতে লেনদেন আইডি, টাকার পরিমাণ, সময় এবং কী সমস্যা হয়েছে তা জানান। অনুগ্রহ করে পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"
        return f"আপনার অভিযোগটি {ref} সম্পর্কে গ্রহণ করা হয়েছে। সংশ্লিষ্ট টিম অফিসিয়াল চ্যানেলের মাধ্যমে বিষয়টি যাচাই করবে। অনুগ্রহ করে পিন বা ওটিপি কারো সাথে শেয়ার করবেন না।"

    if case_type == CaseType.phishing_or_social_engineering:
        return "Thank you for reporting this. We never ask for your PIN, OTP, password, or verification code. Please do not share sensitive information with anyone. Our fraud team will review the incident through official channels."
    if case_type == CaseType.wrong_transfer:
        if match.ambiguous or verdict == EvidenceVerdict.insufficient_data:
            return "Thank you for reaching out. Please share the recipient number, transaction ID if available, and approximate time so we can identify the correct transfer. Please do not share your PIN or OTP with anyone."
        return f"We have noted your concern about transaction {ref}. Our dispute team will review it through official support channels. Please do not share your PIN or OTP with anyone."
    if case_type == CaseType.payment_failed:
        return f"We have noted that transaction {ref} may have caused an unexpected balance deduction. Our payments team will review it, and any eligible amount will be returned through official channels. Please do not share your PIN or OTP with anyone."
    if case_type == CaseType.refund_request:
        if severity == Severity.low and verdict == EvidenceVerdict.consistent:
            return "Thank you for reaching out. Refund eligibility for completed merchant payments depends on the relevant policy. We can guide you through the official support process. Please do not share your PIN or OTP with anyone."
        return f"We have received your request regarding transaction {ref}. The case will be reviewed according to policy through official channels. Please do not share your PIN or OTP with anyone."
    if case_type == CaseType.duplicate_payment:
        return f"We have noted the possible duplicate payment for transaction {ref}. Our payments team will verify it, and any eligible amount will be returned through official channels. Please do not share your PIN or OTP with anyone."
    if case_type == CaseType.merchant_settlement_delay:
        return f"We have noted your concern about settlement {ref}. Our merchant operations team will check the batch status and update you through official channels."
    if case_type == CaseType.agent_cash_in_issue:
        return f"We have noted your concern about cash-in transaction {ref}. Our agent operations team will review it through official channels. Please do not share your PIN or OTP with anyone."
    return "Thank you for reaching out. To help you faster, please share the transaction ID, amount, approximate time, and what went wrong. Please do not share your PIN or OTP with anyone."


def build_confidence(case_type: CaseType, verdict: EvidenceVerdict, match: MatchResult, classification_reasons: List[str]) -> float:
    if case_type == CaseType.phishing_or_social_engineering:
        return 0.95
    if case_type == CaseType.other:
        return 0.40 if verdict == EvidenceVerdict.insufficient_data else 0.55
    if verdict == EvidenceVerdict.consistent and match.score >= 0.85:
        return 0.90
    if verdict == EvidenceVerdict.consistent and match.score >= 0.60:
        return 0.75
    if verdict == EvidenceVerdict.inconsistent and match.score >= 0.60:
        return 0.75
    if verdict == EvidenceVerdict.insufficient_data and case_type != CaseType.other:
        return 0.55 if not match.ambiguous else 0.65
    return 0.40


def build_text_fields(req: AnalyzeTicketRequest, case_type: CaseType, verdict: EvidenceVerdict, match: MatchResult, severity: Severity) -> tuple[str, str, str]:
    language = infer_language(req.complaint, req.language.value if req.language else None)
    summary = build_agent_summary(req, case_type, verdict, match)
    action = build_next_action(case_type, verdict, match, severity, language)
    reply = build_customer_reply(req, case_type, verdict, match, severity, language)
    reply, action = sanitize_output(reply, action, language)
    return summary, action, reply
