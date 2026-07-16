"""Tests for LLM classification (with mocked Anthropic client)."""
from __future__ import annotations

from src.classify import classify_email, _parse_response


def test_parse_reply_needed():
    assert _parse_response("REPLY_NEEDED") == "REPLY_NEEDED"
    assert _parse_response("  reply_needed  ") == "REPLY_NEEDED"


def test_parse_ignore():
    assert _parse_response("IGNORE") == "IGNORE"
    assert _parse_response(" ignore ") == "IGNORE"


def test_parse_unclear_defaults_to_ignore():
    assert _parse_response("hmm") == "IGNORE"
    assert _parse_response("") == "IGNORE"


def test_classify_customer_question_returns_reply_needed(mock_config, mock_anthropic_classify_reply_needed):
    result = classify_email(
        from_address="kunde@web.de",
        subject="Frage zu Öffnungszeiten",
        body="Guten Tag, wann haben Sie am Sonntag geöffnet?",
        config=mock_config,
    )
    assert result == "REPLY_NEEDED"
    mock_anthropic_classify_reply_needed.assert_called_once()
    assert mock_anthropic_classify_reply_needed.call_args.kwargs["provider"] == "anthropic"
    assert mock_anthropic_classify_reply_needed.call_args.kwargs["api_key"] == "sk-ant-test"


def test_classify_newsletter_returns_ignore(mock_config, mock_anthropic_classify_ignore):
    result = classify_email(
        from_address="newsletter@marketing.com",
        subject="Neue Angebote diese Woche!",
        body="Klicke hier für tolle Deals...",
        config=mock_config,
    )
    assert result == "IGNORE"


def test_classify_truncates_long_body(mock_config, mock_anthropic_classify_reply_needed):
    long_body = "x" * 5000
    result = classify_email(
        from_address="kunde@web.de",
        subject="Frage",
        body=long_body,
        config=mock_config,
    )
    # Check that the prompt sent to llm_call had truncated body
    call_args = mock_anthropic_classify_reply_needed.call_args
    prompt = call_args.kwargs["prompt"]
    assert len(prompt) < 5000 + 500  # prompt template + truncated body, no way it's 5000+
    assert "truncated" in prompt
