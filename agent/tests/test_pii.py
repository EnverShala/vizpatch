"""Tests for PII redaction."""
from __future__ import annotations

from src.pii import redact


def test_redact_de_iban():
    result = redact("Bitte überweisen Sie auf IBAN DE89370400440532013000")
    assert "DE89370400440532013000" not in result
    assert "[IBAN_REDACTED]" in result


def test_redact_luhn_valid_credit_card():
    # 4111 1111 1111 1111 is a well-known Visa test number (Luhn-valid)
    result = redact("Meine Karte: 4111 1111 1111 1111")
    assert "4111" not in result
    assert "[CC_REDACTED]" in result


def test_does_not_redact_phone_number():
    # Deutsche Handynummer, kein Luhn-valid
    result = redact("Ruf mich an: +49 30 1234 5678")
    assert "1234 5678" in result or "12345678" in result


def test_empty_string():
    assert redact("") == ""


def test_no_pii():
    text = "Hallo, ich habe eine Frage zu Ihren Öffnungszeiten."
    assert redact(text) == text
