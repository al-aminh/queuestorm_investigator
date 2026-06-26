import re
from typing import Iterable, List

BENGALI_DIGIT_MAP = str.maketrans("০১২৩৪৫৬৭৮৯", "0123456789")


def normalize_text(text: str) -> str:
    """Lowercase, convert Bengali digits, and normalize common separators."""
    if not text:
        return ""
    text = text.translate(BENGALI_DIGIT_MAP)
    text = text.lower()
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"[_/]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def contains_bengali(text: str) -> bool:
    return bool(re.search(r"[\u0980-\u09FF]", text or ""))


def infer_language(text: str, explicit_language: str | None = None) -> str:
    if explicit_language in {"en", "bn", "mixed"}:
        return explicit_language
    return "bn" if contains_bengali(text) else "en"


def has_any(text: str, keywords: Iterable[str]) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(keyword) in normalized for keyword in keywords)


def matched_keywords(text: str, keywords: Iterable[str]) -> List[str]:
    normalized = normalize_text(text)
    return [keyword for keyword in keywords if normalize_text(keyword) in normalized]


def normalize_counterparty(value: str) -> str:
    """Normalize phone/ID counterparty for loose complaint matching."""
    if not value:
        return ""
    value = normalize_text(value)
    compact = re.sub(r"[^a-z0-9+]", "", value)
    if compact.startswith("+88"):
        compact = compact[3:]
    elif compact.startswith("88") and compact[2:].startswith("01"):
        compact = compact[2:]
    return compact


def text_tokens(text: str) -> set[str]:
    normalized = normalize_text(text)
    return set(re.findall(r"[a-z0-9\u0980-\u09FF]+", normalized))
