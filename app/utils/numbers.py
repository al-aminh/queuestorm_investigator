import re
from typing import List

from app.utils.text import BENGALI_DIGIT_MAP, normalize_text

_AMOUNT_WORDS = {
    "taka", "tk", "bdt", "৳", "টাকা", "টাক", "taaka", "takaa"
}


def _clean_num(raw: str) -> float | None:
    cleaned = raw.translate(BENGALI_DIGIT_MAP).replace(",", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def extract_numbers(text: str) -> List[float]:
    """Extract plausible numeric values from English/Bangla/Banglish text."""
    if not text:
        return []
    text = text.translate(BENGALI_DIGIT_MAP)
    values: List[float] = []
    for match in re.finditer(r"(?<![A-Za-z0-9])(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?![A-Za-z0-9])", text):
        value = _clean_num(match.group(0))
        if value is None:
            continue
        values.append(value)
    return values


def extract_amounts(text: str) -> List[float]:
    """Extract likely money amounts while avoiding phone numbers and times."""
    if not text:
        return []
    original = text.translate(BENGALI_DIGIT_MAP)
    normalized = normalize_text(original)
    amounts: List[float] = []

    # Strong signal: number near money words.
    money_pattern = r"(?:৳\s*)?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)\s*(?:taka|tk|bdt|টাকা|টাক)?|(?:taka|tk|bdt|টাকা|টাক)\s*(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
    for match in re.finditer(money_pattern, normalized):
        raw = match.group(1) or match.group(2)
        value = _clean_num(raw)
        if value is None:
            continue
        # Ignore likely phone numbers and tiny time hints such as 2pm.
        digits = str(int(value)) if value.is_integer() else str(value)
        around = normalized[max(0, match.start() - 12): match.end() + 12]
        has_money_word = any(word in around for word in _AMOUNT_WORDS)
        if len(digits) >= 8 and not has_money_word:
            continue
        if value <= 0:
            continue
        if value < 10 and not has_money_word:
            continue
        amounts.append(value)

    # Weak signal: all medium-sized numbers if no money-word match exists.
    if not amounts:
        for value in extract_numbers(normalized):
            digits = str(int(value)) if float(value).is_integer() else str(value)
            if 10 <= value <= 1_000_000 and len(digits) < 8:
                amounts.append(value)

    # Deduplicate preserving order.
    output: List[float] = []
    for value in amounts:
        if not any(abs(value - existing) < 0.001 for existing in output):
            output.append(value)
    return output


def amount_matches(a: float, b: float, tolerance: float = 0.01) -> bool:
    return abs(float(a) - float(b)) <= tolerance
