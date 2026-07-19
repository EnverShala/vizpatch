"""PII-Redaction und reversible Pseudonymisierung. Vor LLM-Call anwenden.

Zwei Bausteine:
- `redact()` (Alt, bleibt für Rückwärtskompatibilität unverändert): einseitige,
  nicht-nummerierte IBAN/Kreditkarten-Redaction.
- `Anonymizer` (Phase 10, ANON-01..05): reversible, getypte Pseudonymisierung
  über sechs strukturierte PII-Typen (IBAN, KARTE, EMAIL, URL, DATUM, TELEFON).
"""
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


# --- Reversible Pseudonymisierung (Phase 10, Variante A, D-01..D-09) ---

# Reihenfolge ist SICHERHEITSRELEVANT (spezifischste zuerst, jeweils sofort per
# .sub() ersetzt) — siehe 10-RESEARCH.md §"Overlap-/Präzedenz-Handling":
# IBAN vor KARTE (Luhn-Gate) vor EMAIL vor URL vor DATUM vor TELEFON (das mit
# Abstand permissivste Muster, muss zuletzt laufen).
_PATTERNS: list[tuple[str, re.Pattern]] = [
    # Deckt kompakte IBANs (keine Leerzeichen, Restlänge oft KEIN Vielfaches
    # von 4, z.B. DE mit 18-stelliger BBAN) UND formatierte IBANs (4er-Gruppen
    # mit Leerzeichen, letzte Gruppe 1-4 Zeichen) gleichermaßen ab.
    ("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,6}(?:[ ]?[A-Z0-9]{1,4})?\b")),
    ("KARTE", _CC_PATTERN),
    ("EMAIL", re.compile(r"\b[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("URL", re.compile(r"\b(?:https?://|www\.)[^\s<>\"']+")),
    ("DATUM", re.compile(r"\b(0?[1-9]|[12]\d|3[01])[.\/](0?[1-9]|1[0-2])[.\/](\d{4}|\d{2})\b")),
    # Review CR-01: KEIN führendes \b vor der +49-Alternative — zwischen einem
    # Nicht-Wortzeichen (Leerzeichen/Zeilenanfang/":") und "+" existiert keine
    # Word-Boundary, die \+49-Alternative wäre damit faktisch tot und
    # internationale Nummern (+49 …, das häufigste Format deutscher
    # Geschäfts-Signaturen) gingen roh an den LLM. \b bleibt gezielt vor den
    # 0049-/0-Alternativen (dort beginnt die Nummer mit einem Wortzeichen).
    (
        "TELEFON",
        re.compile(
            r"(?:\+49[ /-]?|\b0049[ /-]?|\b0)"
            r"(?:\(?\d{2,5}\)?[ /-]?)"
            r"\d{3,4}(?:[ /-]?\d{2,4}){0,3}\b"
        ),
    ),
]

_RESIDUAL_PLACEHOLDER_PATTERN = re.compile(r"\[?(EMAIL|TELEFON|IBAN|KARTE|URL|DATUM)_\d+\]?")


class Anonymizer:
    """Reversible Pseudonymisierungs-Engine für strukturierte PII (Variante A).

    Pro Request instanziieren, NIE über Requests hinweg wiederverwenden oder
    persistieren — das Platzhalter<->Original-Mapping lebt ausschließlich im
    RAM dieser Instanz (D-04). Es wird nirgends geloggt, gespeichert oder an
    den LLM übergeben.
    """

    def __init__(self) -> None:
        self._tag_to_original: dict[str, str] = {}
        self._original_to_tag: dict[str, str] = {}
        self._counters: dict[str, int] = {}

    def _tag_for(self, entity_type: str, original: str) -> str:
        if original in self._original_to_tag:
            return self._original_to_tag[original]
        n = self._counters.get(entity_type, 0) + 1
        self._counters[entity_type] = n
        tag = f"[{entity_type}_{n}]"
        self._original_to_tag[original] = tag
        self._tag_to_original[tag] = original
        return tag

    def anonymize(self, text: str) -> str:
        """Ersetzt strukturierte PII in `text` durch getypte, nummerierte Tags."""
        if not text:
            return text
        for entity_type, pattern in _PATTERNS:
            def _sub(m: re.Match, et: str = entity_type) -> str:
                if et == "KARTE" and not _luhn_check(re.sub(r"\D", "", m.group(0))):
                    return m.group(0)
                return self._tag_for(et, m.group(0))

            text = pattern.sub(_sub, text)
        return text

    def deanonymize(self, text: str) -> str:
        """Ersetzt Tags zurück durch die Originalwerte (str.replace, kein Regex)."""
        if not text:
            return text
        for tag, original in sorted(self._tag_to_original.items(), key=lambda kv: -len(kv[0])):
            text = text.replace(tag, original)
        return text


def warn_residual_placeholders(text: str, logger) -> None:
    """Billiger Nachlauf-Regex-Check nach deanonymize(): loggt bei übrig
    gebliebenen [TYP_N]-Platzhaltern GENAU EINE Warnung (nur Typ/Anzahl, keine
    Originalwerte, kein Mapping) — Defense-in-Depth (D-09), kein Abbruch.
    """
    if not text:
        return
    matches = _RESIDUAL_PLACEHOLDER_PATTERN.findall(text)
    if not matches:
        return
    counts: dict[str, int] = {}
    for entity_type in matches:
        counts[entity_type] = counts.get(entity_type, 0) + 1
    logger.warning("possible_placeholder_leak", extra={"placeholder_counts": counts})
