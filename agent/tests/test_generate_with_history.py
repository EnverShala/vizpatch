"""Tests for generate_draft_text() with conversation_history parameter (D-26)."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from src.generate import generate_draft_text, _build_history_block, _truncate_body


def test_generate_includes_history_in_prompt(mock_config, mock_anthropic_generate):
    """generate_draft_text mit conversation_history: Prompt enthält Gesprächsverlauf."""
    msg = MagicMock()
    msg.from_ = "kunde@web.de"
    msg.date = datetime(2026, 7, 1, 10, 0)
    msg.subject = "Waschanlage-Termin"
    msg.text = "Kann ich am Montag einen Termin buchen?"
    msg.html_to_text = MagicMock(return_value="")

    generate_draft_text(
        from_address="kunde@web.de",
        subject="Re: Waschanlage-Termin",
        body="Und wie läuft das ab?",
        config=mock_config,
        client=mock_anthropic_generate,
        conversation_history=[msg],
    )

    call_args = mock_anthropic_generate.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    assert "Bisheriger Gesprächsverlauf" in prompt
    assert "Waschanlage-Termin" in prompt


def test_generate_empty_history_no_none_in_prompt(mock_config, mock_anthropic_generate):
    """generate_draft_text mit leerer History: kein 'None'-String im Prompt."""
    generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Test",
        config=mock_config,
        client=mock_anthropic_generate,
        conversation_history=[],
    )

    call_args = mock_anthropic_generate.messages.create.call_args
    prompt = call_args.kwargs["messages"][0]["content"]
    # Slice zwischen den History-Abschnittmarkern
    start = prompt.find("# Bisheriger")
    end = prompt.find("# Eingehende")
    section = prompt[start:end] if start != -1 and end != -1 else prompt
    assert "None" not in section


def test_generate_no_history_parameter_backward_compat(mock_config, mock_anthropic_generate):
    """generate_draft_text ohne conversation_history-Parameter funktioniert wie vorher."""
    result = generate_draft_text(
        from_address="kunde@web.de",
        subject="Frage",
        body="Wie sind die Öffnungszeiten?",
        config=mock_config,
        client=mock_anthropic_generate,
    )
    # Kein Fehler, Ergebnis ist ein String
    assert isinstance(result, str)
    assert len(result) > 0


def test_truncate_body_at_800():
    """_truncate_body kürzt auf max. 800 Zeichen und fügt Markierung ein."""
    long_text = "x" * 1000
    result = _truncate_body(long_text)
    # 800 Zeichen + Suffix "\n[... gekürzt ...]" (18 Zeichen) = max 818
    assert len(result) <= 820
    assert "gekürzt" in result


def test_truncate_body_passthrough():
    """_truncate_body lässt kurze Texte unverändert."""
    short_text = "kurzer Text"
    result = _truncate_body(short_text)
    assert result == short_text


def test_build_history_block_format(mock_config):
    """_build_history_block formatiert Absender, Datum und Betreff korrekt."""
    msg = MagicMock()
    msg.from_ = "a@b.de"
    msg.date = datetime(2026, 7, 1, 10, 0)
    msg.subject = "Frage zum Service"
    msg.text = "Das ist der Body-Text."
    msg.html_to_text = MagicMock(return_value="")

    block = _build_history_block([msg])

    assert "Von: a@b.de" in block
    assert "Betreff: Frage zum Service" in block
    assert "Das ist der Body-Text." in block


def test_build_history_block_html_only():
    """_build_history_block nutzt HTML-Fallback wenn text leer."""
    msg = MagicMock()
    msg.from_ = "x@y.de"
    msg.date = datetime(2026, 7, 1, 10, 0)
    msg.subject = "HTML-Mail"
    msg.text = ""
    msg.html_to_text = MagicMock(return_value="Aus HTML konvertiert")

    block = _build_history_block([msg])

    assert "Aus HTML konvertiert" in block


def test_build_history_block_separator_between_messages():
    """_build_history_block trennt mehrere Nachrichten mit '---'."""
    msg1 = MagicMock()
    msg1.from_ = "a@b.de"
    msg1.date = datetime(2026, 7, 1, 10, 0)
    msg1.subject = "Erste Frage"
    msg1.text = "Erster Body"
    msg1.html_to_text = MagicMock(return_value="")

    msg2 = MagicMock()
    msg2.from_ = "a@b.de"
    msg2.date = datetime(2026, 7, 2, 10, 0)
    msg2.subject = "Zweite Frage"
    msg2.text = "Zweiter Body"
    msg2.html_to_text = MagicMock(return_value="")

    block = _build_history_block([msg1, msg2])

    assert "\n\n---\n\n" in block
