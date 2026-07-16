"""Tests for LLM draft generation (with mocked Anthropic client)."""
from __future__ import annotations

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
