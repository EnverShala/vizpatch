"""Optionale PII-Redaction. Regex für IBAN und Kreditkarten. Vor LLM-Call anwenden."""
from __future__ import annotations

import re


# DE-IBAN + generische EU-IBAN (2 Buchstaben Land + 2 Ziffern Prüfsumme + 11-30 alphanumerisch)
_IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")

# Kreditkartennummern: 13-19 Ziffern, ggf. mit Leerzeichen oder Bindestrichen alle 4 Ziffern
_CC_PATTERN = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")


def _luhn_check(digits: str) -> bool:
    """Luhn-Check für Kreditkartennummer-Validierung."""
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _redact_cc(match: re.Match) -> str:
    raw = match.group(0)
    digits = re.sub(r"\D", "", raw)
    if len(digits) < 13 or len(digits) > 19:
        return raw
    if _luhn_check(digits):
        return "[CC_REDACTED]"
    return raw


def redact(text: str) -> str:
    """Redact IBANs and Luhn-valid credit-card numbers from text."""
    if not text:
        return text
    text = _IBAN_PATTERN.sub("[IBAN_REDACTED]", text)
    text = _CC_PATTERN.sub(_redact_cc, text)
    return text
