"""Tests for LLM draft generation (with mocked Anthropic client)."""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock

from src.generate import generate_draft_text, _extract_company_name


def test_extract_company_name_from_context():
    md = "# Firmen-Kontext für Shell-Tankstelle Musterstadt\n\n## About\n..."
    assert _extract_company_name(md) == "Shell-Tankstelle Musterstadt"


def test_extract_company_name_fallback():
    assert _extract_company_name("") == "der Firma"
    assert _extract_company_name("## About\nno h1") == "der Firma"


def test_generate_returns_string(mock_config, mock_anthropic_generate):
    result = generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Wie sind die Öffnungszeiten?",
        config=mock_config,
    )
    assert isinstance(result, str)
    assert len(result) > 0
    assert "freundlichen Grüßen" in result or "Grüßen" in result


def test_generate_injects_context(mock_config, mock_anthropic_generate):
    generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Test",
        config=mock_config,
    )
    call_args = mock_anthropic_generate.call_args
    prompt = call_args.kwargs["prompt"]
    assert "Test-Tankstelle" in prompt
    assert "Mo-Fr 8-20" in prompt


def test_generate_body_anonymized_in_prompt(mock_config, mocker):
    """ANON-03: der Draft-Prompt enthaelt getypte Tags statt Rohwerten."""
    mock_llm = mocker.patch("src.generate.llm.llm_call", return_value="Draft ok")
    generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Meine IBAN ist DE89370400440532013000, Mail: kunde@web.de",
        config=mock_config,
    )
    prompt = mock_llm.call_args.kwargs["prompt"]
    assert "DE89370400440532013000" not in prompt
    assert "[IBAN_1]" in prompt


def test_generate_context_md_stays_raw(mock_config, mocker):
    """D-08: context.md wird NIE maskiert, auch wenn es PII enthaelt (Pitfall 4)."""
    context_with_pii = (
        mock_config.context_md
        + "\n\n## Zahlung\nVorkasse an IBAN DE89370400440532013000, "
        "Rueckfragen: 07152 123456"
    )
    config = replace(mock_config, context_md=context_with_pii)
    mock_llm = mocker.patch("src.generate.llm.llm_call", return_value="Draft ok")
    generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Normaler Text ohne PII",
        config=config,
    )
    prompt = mock_llm.call_args.kwargs["prompt"]
    assert "DE89370400440532013000" in prompt
    assert "07152 123456" in prompt


def test_generate_history_anonymized(mock_config, mocker):
    """History-Bloecke werden anonymisiert; geteilter Wert -> gleicher Tag."""
    hist_msg = MagicMock()
    hist_msg.text = "Historischer Kontakt: kunde@web.de"
    hist_msg.html_to_text = MagicMock(return_value="")
    hist_msg.from_ = "kunde@web.de"
    hist_msg.date = "2026-01-01"
    hist_msg.subject = "Alte Anfrage"

    mock_llm = mocker.patch("src.generate.llm.llm_call", return_value="Draft ok")
    generate_draft_text(
        from_address="kunde@web.de",
        subject="Neue Anfrage",
        body="aktuelle Mail von kunde@web.de",
        config=mock_config,
        conversation_history=[hist_msg],
    )
    prompt = mock_llm.call_args.kwargs["prompt"]
    assert "kunde@web.de" not in prompt
    # gleicher Rohwert in from/body/History -> derselbe Tag [EMAIL_1], keine Inflation
    assert "[EMAIL_1]" in prompt
    assert "[EMAIL_2]" not in prompt


def test_generate_deanonymizes_output(mock_config, mocker):
    """ANON-04: kein Platzhalter-Leck im fertigen Draft."""
    mocker.patch(
        "src.generate.llm.llm_call",
        return_value="Ihre IBAN ist [IBAN_1], vielen Dank.",
    )
    draft = generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Bitte pruefen Sie IBAN DE89370400440532013000",
        config=mock_config,
    )
    assert "DE89370400440532013000" in draft
    assert "[IBAN_1]" not in draft


def test_generate_calls_warn_residual_placeholders(mock_config, mocker):
    """D-09 Defense-in-Depth: Nachlauf-Check laeuft, blockiert aber nicht."""
    spy = mocker.patch("src.generate.pii.warn_residual_placeholders")
    mocker.patch(
        "src.generate.llm.llm_call",
        return_value="Rest: [TELEFON_5] nicht aufloesbar",
    )
    draft = generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="kein passendes Telefon im Input",
        config=mock_config,
    )
    spy.assert_called_once()
    assert draft  # kein Abbruch trotz nicht aufloesbarem Rest-Platzhalter
