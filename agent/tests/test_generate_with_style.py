"""Tests for generate_draft_text() with style.md-Injection (STY-02).

Deckt die vier Kernverhalten ab:
1. style.md gesetzt + enable_style_adaption=True -> Prompt enthält Stil-Text + Hierarchie-Marker
2. style.md leer -> kein "None"-String im Schreibstil-Abschnitt (Verhalten wie heute)
3. style.md gesetzt ABER enable_style_adaption=False -> Stil-Text NICHT im Prompt
4. Rückwärtskompat: generate_draft_text ohne style-bezogene Aufruf-Änderungen funktioniert weiter
"""
from __future__ import annotations

import dataclasses

from src.generate import generate_draft_text

_STYLE_MD = (
    "## Anrede\nDu\n"
    "## Du/Sie\nDu\n"
    "## Grußformel\nViele Grüße\n"
    "## Satzlänge\nkurz\n"
    "## Formalität\nlocker\n"
    "## typische Wendungen\nMoin"
)


def test_generate_injects_style_md_with_hierarchy_marker(mock_config, mock_anthropic_generate):
    """style.md gesetzt + enable_style_adaption=True -> Prompt enthält Stil-Text + Hierarchie-Marker."""
    style_config = dataclasses.replace(
        mock_config, style_md=_STYLE_MD, enable_style_adaption=True
    )

    generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Test",
        config=style_config,
    )

    call_args = mock_anthropic_generate.call_args
    prompt = call_args.kwargs["prompt"]
    assert "Viele Grüße" in prompt
    assert "Schreibstil" in prompt


def test_generate_empty_style_md_no_none_in_prompt(mock_config, mock_anthropic_generate):
    """style.md leer -> kein 'None'-String im Schreibstil-Abschnitt (Verhalten wie heute)."""
    style_config = dataclasses.replace(mock_config, style_md="", enable_style_adaption=True)

    generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Test",
        config=style_config,
    )

    call_args = mock_anthropic_generate.call_args
    prompt = call_args.kwargs["prompt"]
    start = prompt.find("# Schreibstil")
    end = prompt.find("# Eingehende")
    section = prompt[start:end] if start != -1 and end != -1 else prompt
    assert "None" not in section


def test_generate_style_adaption_disabled_omits_style_md(mock_config, mock_anthropic_generate):
    """style.md gesetzt ABER enable_style_adaption=False -> Stil-Text NICHT im Prompt."""
    style_config = dataclasses.replace(
        mock_config, style_md=_STYLE_MD, enable_style_adaption=False
    )

    generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Test",
        config=style_config,
    )

    call_args = mock_anthropic_generate.call_args
    prompt = call_args.kwargs["prompt"]
    assert "Viele Grüße" not in prompt


def test_generate_without_style_call_args_backward_compat(mock_config, mock_anthropic_generate):
    """generate_draft_text ohne style-bezogene Aufruf-Änderungen funktioniert weiter."""
    result = generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Wie sind die Öffnungszeiten?",
        config=mock_config,
    )
    assert isinstance(result, str)
    assert len(result) > 0
