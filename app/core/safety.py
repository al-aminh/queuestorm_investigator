import re
from dataclasses import dataclass
from typing import Iterable, List

from app.utils.text import normalize_text

SENSITIVE_TERMS = [
    "pin", "otp", "password", "verification code", "full card number", "card number",
    "secret credential", "পিন", "ওটিপি", "পাসওয়ার্ড", "পাসওয়ার্ড", "ভেরিফিকেশন কোড",
]

PROMPT_INJECTION_PATTERNS = [
    "ignore previous rules", "ignore all previous", "ignore the above", "forget previous instructions",
    "return this json", "respond only with", "ask the user for otp", "ask for otp", "ask for pin",
    "approve refund", "confirm refund", "refund confirmed", "you are now admin", "bypass safety",
    "bypass policy", "system prompt", "developer message", "jailbreak", "override instructions",
]

PHISHING_KEYWORDS = [
    "otp", "pin", "password", "verification code", "suspicious call", "suspicious sms", "scam",
    "fraud", "link", "account blocked message", "account will be blocked", "prize message",
    "asked for my otp", "asked for otp", "asked for pin", "share otp", "share pin", "login code",
    "ওটিপি", "পিন", "পাসওয়ার্ড", "পাসওয়ার্ড", "প্রতারণা", "লিংক", "ভুয়া", "ভুয়া",
]

UNSAFE_PROMISE_PATTERNS = [
    r"\bwe\s+will\s+refund\b",
    r"\bwe\s+will\s+reverse\b",
    r"\bwe\s+will\s+recover\b",
    r"\byour\s+money\s+will\s+be\s+returned\b",
    r"\byour\s+account\s+will\s+be\s+unblocked\b",
    r"\brefund\s+confirmed\b",
    r"\breversal\s+confirmed\b",
    r"\brefund\s+has\s+been\s+approved\b",
    r"\breversal\s+has\s+been\s+approved\b",
]

REQUEST_VERBS = ["provide", "share", "send", "tell", "give", "enter", "confirm", "submit", "আপনার", "দিন", "শেয়ার", "শেয়ার"]
NEGATIONS = ["do not", "don't", "dont", "never", "not share", "avoid sharing", "কারো সাথে", "শেয়ার করবেন না", "শেয়ার করবেন না"]


@dataclass(frozen=True)
class SafetySignals:
    prompt_injection: bool
    phishing_signal: bool
    safety_sensitive: bool
    reason_codes: List[str]


def detect_prompt_injection(text: str) -> bool:
    normalized = normalize_text(text)
    return any(pattern in normalized for pattern in PROMPT_INJECTION_PATTERNS)


def detect_phishing_signal(text: str) -> bool:
    normalized = normalize_text(text)
    if any(keyword in normalized for keyword in PHISHING_KEYWORDS):
        # Credential term alone is enough when it appears in a customer complaint, because the safe route is fraud/risk.
        return True
    suspicious_context = ["call", "sms", "message", "link", "blocked", "prize", "unknown", "অজানা", "কল", "মেসেজ"]
    return any(word in normalized for word in suspicious_context) and any(term in normalized for term in SENSITIVE_TERMS)


def analyze_safety(text: str) -> SafetySignals:
    reason_codes: List[str] = []
    injection = detect_prompt_injection(text)
    phishing = detect_phishing_signal(text)
    sensitive = any(term in normalize_text(text) for term in SENSITIVE_TERMS)
    if injection:
        reason_codes.append("prompt_injection_ignored")
    if phishing:
        reason_codes.append("phishing_signal")
    if sensitive:
        reason_codes.append("safety_sensitive")
    return SafetySignals(injection, phishing, sensitive, reason_codes)


def _is_unsafe_credential_request(text: str) -> bool:
    normalized = normalize_text(text)
    for term in SENSITIVE_TERMS:
        term_norm = normalize_text(term)
        for match in re.finditer(re.escape(term_norm), normalized):
            window_start = max(0, match.start() - 50)
            window_end = min(len(normalized), match.end() + 50)
            window = normalized[window_start:window_end]
            if any(negation in window for negation in NEGATIONS):
                continue
            if any(verb in window for verb in REQUEST_VERBS):
                return True
    return False


def _has_unsafe_promise(text: str) -> bool:
    normalized = normalize_text(text)
    # Allowed safe phrase from the problem statement/sample cases.
    allowed = "any eligible amount will be returned through official channels"
    cleaned = normalized.replace(allowed, "")
    return any(re.search(pattern, cleaned) for pattern in UNSAFE_PROMISE_PATTERNS)


def is_unsafe_output(text: str) -> bool:
    return _is_unsafe_credential_request(text) or _has_unsafe_promise(text)


def safe_customer_template(language: str = "en") -> str:
    if language == "bn":
        return (
            "আপনার অভিযোগটি আমরা গ্রহণ করেছি। আমাদের টিম অফিসিয়াল চ্যানেলের মাধ্যমে বিষয়টি যাচাই করবে। "
            "অনুগ্রহ করে কারো সাথে আপনার পিন, ওটিপি বা পাসওয়ার্ড শেয়ার করবেন না।"
        )
    return (
        "We have received your concern. Our team will review it through official support channels. "
        "Please do not share your PIN, OTP, password, or sensitive information with anyone."
    )


def safe_action_template() -> str:
    return "Review the ticket through the official workflow, verify non-sensitive transaction details, and escalate if evidence is unclear or risky."


def sanitize_output(customer_reply: str, recommended_next_action: str, language: str = "en") -> tuple[str, str]:
    if is_unsafe_output(customer_reply):
        customer_reply = safe_customer_template(language)
    if is_unsafe_output(recommended_next_action):
        recommended_next_action = safe_action_template()
    return customer_reply, recommended_next_action
