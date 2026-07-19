"""Tests for PII redaction."""
from __future__ import annotations

from src.pii import redact, Anonymizer, warn_residual_placeholders


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


# --- Anonymizer-Engine (reversible Pseudonymisierung, D-01..D-09) ---


def test_anonymize_iban_with_spaces_reversible():
    a = Anonymizer()
    text = "IBAN: DE89 3704 0044 0532 0130 00"
    anon = a.anonymize(text)
    assert "DE89 3704 0044 0532 0130 00" not in anon
    assert "[IBAN_1]" in anon
    assert a.deanonymize(anon) == text


def test_anonymize_iban_without_spaces_reversible():
    a = Anonymizer()
    text = "DE89370400440532013000"
    anon = a.anonymize(text)
    assert "DE89370400440532013000" not in anon
    assert "[IBAN_1]" in anon
    assert a.deanonymize(anon) == text


def test_same_value_gets_same_tag():
    a = Anonymizer()
    text = "Kontakt: max@kunde.de, nochmal: max@kunde.de"
    anon = a.anonymize(text)
    assert anon.count("[EMAIL_1]") == 2
    assert "[EMAIL_2]" not in anon


def test_different_values_get_incrementing_tags():
    a = Anonymizer()
    anon = a.anonymize("max@kunde.de und peter@kunde.de")
    assert "[EMAIL_1]" in anon
    assert "[EMAIL_2]" in anon


def test_iban_not_split_into_phone_or_date():
    a = Anonymizer()
    anon = a.anonymize("IBAN DE89370400440532013000 am 07.12.2024")
    assert "[IBAN_1]" in anon
    assert "[DATUM_1]" in anon
    assert "[TELEFON_1]" not in anon


def test_deanonymize_handles_two_digit_tag_numbers():
    a = Anonymizer()
    text = " ".join(f"user{i}@kunde.de" for i in range(1, 12))  # erzeugt EMAIL_1..EMAIL_11
    anon = a.anonymize(text)
    assert "[EMAIL_11]" in anon
    assert a.deanonymize(anon) == text


def test_phone_email_url_date_each_get_typed_tag():
    a = Anonymizer()
    text = (
        "Ruf an: 07152 123456, mail an max@kunde.de, "
        "besuch https://kunde-tankstelle.de/info, Termin am 19.07.2026"
    )
    anon = a.anonymize(text)
    assert "[TELEFON_1]" in anon
    assert "[EMAIL_1]" in anon
    assert "[URL_1]" in anon
    assert "[DATUM_1]" in anon


def test_phone_international_plus49_formats_are_tagged():
    """Review CR-01: das häufigste deutsche Geschäfts-Format (+49 …) MUSS
    matchen — ein führendes \\b vor '+' machte die Alternative faktisch tot."""
    for text in (
        "Ruf mich an: +49 170 1234567",
        "Tel: +49 30 1234 5678",
        "Handy +4917012345678",
    ):
        a = Anonymizer()
        anon = a.anonymize(text)
        assert "[TELEFON_1]" in anon, f"nicht getaggt: {text!r}"
        assert a.deanonymize(anon) == text


def test_phone_legacy_formats_still_tagged_after_cr01_fix():
    """Regression zu CR-01: die bisher abgedeckten Formate (0049/0-Präfix)
    matchen weiterhin."""
    for text in ("0049 170 1234567", "07152 123456", "030/1234567"):
        a = Anonymizer()
        anon = a.anonymize(text)
        assert "[TELEFON_1]" in anon, f"nicht getaggt: {text!r}"


def test_iso_date_is_tagged_as_datum():
    """Review IN-07: ISO-Format (JJJJ-MM-TT) wird als DATUM erfasst; eine
    Telefonnummer wie 0711-123456 bleibt davon unberührt (kein False-Positive
    des ISO-Musters, TELEFON greift wie gehabt)."""
    a = Anonymizer()
    anon = a.anonymize("Ihr Termin am 2026-07-19, alternativ am 19.07.2026.")
    assert "[DATUM_1]" in anon
    assert "[DATUM_2]" in anon
    assert "2026-07-19" not in anon
    assert a.deanonymize(anon) == "Ihr Termin am 2026-07-19, alternativ am 19.07.2026."

    b = Anonymizer()
    anon2 = b.anonymize("Ruf an: 0711-123456")
    assert "[TELEFON_1]" in anon2
    assert "[DATUM_1]" not in anon2


def test_phone_no_false_positive_on_iban_remainder():
    """CR-01-Gegenprobe: IBAN läuft VOR TELEFON — weder die IBAN noch ihr
    Platzhalter-Rest darf zusätzlich als Telefonnummer getaggt werden."""
    a = Anonymizer()
    anon = a.anonymize("IBAN DE89370400440532013000, Tel +49 170 1234567")
    assert "[IBAN_1]" in anon
    assert "[TELEFON_1]" in anon
    assert "[TELEFON_2]" not in anon


def test_credit_card_only_luhn_valid():
    a = Anonymizer()
    anon = a.anonymize("Meine Karte: 4111 1111 1111 1111")
    assert "[KARTE_1]" in anon
    assert "4111 1111 1111 1111" not in anon

    b = Anonymizer()
    non_luhn = "Kundennummer: 1234 5678 9012 3456"
    anon2 = b.anonymize(non_luhn)
    assert anon2 == non_luhn


def test_empty_and_none_safe():
    a = Anonymizer()
    assert a.anonymize("") == ""
    assert a.deanonymize("") == ""


def test_warn_residual_placeholders(mocker):
    logger = mocker.MagicMock()
    warn_residual_placeholders("Ihre IBAN ist [IBAN_1] leider unaufgeloest.", logger)
    logger.warning.assert_called_once()
    call_args = logger.warning.call_args
    assert call_args.args[0] == "possible_placeholder_leak"
    # Keine Originalwerte oder Mapping in der Warnung — nur Typ/Anzahl
    extra = call_args.kwargs.get("extra", {})
    assert "IBAN" not in str(extra) or extra.get("placeholder_counts", {}).get("IBAN") == 1
    assert "1]" not in str(extra.get("placeholder_counts"))

    logger2 = mocker.MagicMock()
    warn_residual_placeholders("Ein sauberer Text ohne Reste.", logger2)
    logger2.warning.assert_not_called()
