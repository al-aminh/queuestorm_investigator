from dataclasses import dataclass
from typing import List

from app.core.safety import SafetySignals
from app.schemas.response import CaseType
from app.utils.text import has_any, normalize_text

WRONG_TRANSFER_KEYWORDS = [
    "wrong number", "wrong recipient", "sent to wrong", "wrong transfer", "wrong person",
    "vul number", "bhul number", "vul kore", "bhul kore", "wrongly sent",
    "ভুল নাম্বার", "ভুল নম্বর", "ভুলে পাঠিয়েছি", "ভুলে পাঠিয়েছি", "ভুল করে পাঠিয়েছি", "ভুল করে পাঠিয়েছি",
]
TRANSFER_NONRECEIPT_KEYWORDS = [
    "sent", "transfer", "didn't get", "did not get", "not received", "didn’t get", "he says he", "she says she",
    "pathaisi", "paisi na", "pay nai", "পাঠিয়েছি", "পাঠিয়েছি", "পায়নি", "পায়নি", "আসেনি",
]
PAYMENT_FAILED_KEYWORDS = [
    "payment failed", "failed but deducted", "failed", "balance deducted", "deducted", "payment hoyni",
    "taka kete gese", "taka kete geche", "tk kete gese", "পেমেন্ট হয়নি", "পেমেন্ট হয়নি",
    "টাকা কেটে গেছে", "ব্যালেন্স কেটে", "balance kete",
]
REFUND_KEYWORDS = [
    "refund", "money back", "taka ferot", "tk ferot", "ফেরত", "টাকা ফেরত", "রিফান্ড",
    "changed my mind", "don't want it", "dont want it", "return my money",
]
DUPLICATE_KEYWORDS = [
    "duplicate", "twice", "double charged", "double charge", "two times", "deducted twice",
    "duibar", "dui bar", "দুইবার", "দুই বার", "ডাবল",
]
MERCHANT_SETTLEMENT_KEYWORDS = [
    "settlement", "merchant settlement", "payout pending", "merchant payment not received", "sales settled",
    "settled", "payout", "batch", "সেটেলমেন্ট", "পেআউট",
]
MERCHANT_CONTEXT_KEYWORDS = ["merchant", "মার্চেন্ট"]
AGENT_CASH_IN_KEYWORDS = [
    "cash in", "cash-in", "cashin", "agent", "deposit not added", "deposit", "balance not added",
    "ক্যাশ ইন", "ক্যাশইন", "এজেন্ট", "জমা", "ব্যালেন্সে টাকা আসেনি",
]


@dataclass(frozen=True)
class ClassificationResult:
    case_type: CaseType
    reason_codes: List[str]
    ambiguous: bool = False


def classify_case(complaint: str, safety: SafetySignals, user_type: str | None = None, channel: str | None = None) -> ClassificationResult:
    text = normalize_text(complaint)
    reasons: List[str] = []

    if safety.phishing_signal:
        return ClassificationResult(CaseType.phishing_or_social_engineering, ["phishing_signal", "safety_sensitive"])

    if has_any(text, DUPLICATE_KEYWORDS):
        return ClassificationResult(CaseType.duplicate_payment, ["duplicate_payment"])

    if has_any(text, PAYMENT_FAILED_KEYWORDS) and ("failed" in text or "deduct" in text or "কেটে" in text or "হয়নি" in text or "হয়নি" in text):
        return ClassificationResult(CaseType.payment_failed, ["payment_failed"])

    if (user_type == "merchant" or channel == "merchant_portal" or has_any(text, MERCHANT_CONTEXT_KEYWORDS)) and has_any(text, MERCHANT_SETTLEMENT_KEYWORDS):
        return ClassificationResult(CaseType.merchant_settlement_delay, ["merchant_settlement_delay"])

    if has_any(text, AGENT_CASH_IN_KEYWORDS) and ("cash" in text or "deposit" in text or "agent" in text or "ক্যাশ" in text or "এজেন্ট" in text):
        return ClassificationResult(CaseType.agent_cash_in_issue, ["agent_cash_in_issue"])

    if has_any(text, WRONG_TRANSFER_KEYWORDS):
        return ClassificationResult(CaseType.wrong_transfer, ["wrong_transfer"])

    # Transfer non-receipt is treated as a dispute-style transfer issue because there is no narrower enum.
    if ("sent" in text or "transfer" in text or "পাঠ" in text) and any(k in text for k in ["didn't get", "did not get", "not received", "পায়নি", "পায়নি", "আসেনি"]):
        return ClassificationResult(CaseType.wrong_transfer, ["wrong_transfer", "transfer_nonreceipt"])

    if has_any(text, REFUND_KEYWORDS):
        return ClassificationResult(CaseType.refund_request, ["refund_request"])

    vague_terms = ["something is wrong", "please check", "money", "সমস্যা", "চেক"]
    if has_any(text, vague_terms):
        reasons.append("vague_complaint")

    return ClassificationResult(CaseType.other, reasons or ["other"])
