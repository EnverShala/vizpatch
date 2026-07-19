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


def test_classify_prompt_has_no_raw_pii(mock_config, mocker):
    """ANON-03: Klassifikation pseudonymisiert VOR dem Prompt-Aufbau (Pitfall 5)."""
    mock_llm = mocker.patch("src.classify.llm.llm_call", return_value="REPLY_NEEDED")
    classify_email(
        from_address="kunde@web.de",
        subject="Rueckerstattung auf DE89370400440532013000",
        body="Bitte ueberweisen Sie an DE89 3704 0044 0532 0130 00, ruf mich an: 07152 123456",
        config=mock_config,
    )
    prompt = mock_llm.call_args.kwargs["prompt"]
    assert "DE89370400440532013000" not in prompt
    assert "DE89 3704 0044 0532 0130 00" not in prompt
    assert "07152 123456" not in prompt


def test_classify_flag_off_passes_raw(mock_config, mocker):
    """Flag aus = Rueckfallverhalten wie vor Phase 10 (Klartext an die Cloud)."""
    from dataclasses import replace

    config_off = replace(mock_config, enable_pii_redaction=False)
    mock_llm = mocker.patch("src.classify.llm.llm_call", return_value="REPLY_NEEDED")
    classify_email(
        from_address="kunde@web.de",
        subject="Frage",
        body="IBAN DE89370400440532013000",
        config=config_off,
    )
    prompt = mock_llm.call_args.kwargs["prompt"]
    assert "DE89370400440532013000" in prompt
