"""Tests for the LLM-Adapter (agent/src/llm.py) — Dispatch auf 3 Provider."""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

from src import llm


def test_llm_call_anthropic_returns_text(mocker):
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="Hallo von Anthropic")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = fake_response
    mock_anthropic_cls = mocker.patch("src.llm.Anthropic", return_value=mock_client)

    result = llm.llm_call(
        provider="anthropic",
        api_key="sk-ant-test",
        model="claude-haiku-4-5",
        prompt="Test-Prompt",
        max_tokens=20,
        temperature=0.0,
    )

    assert result == "Hallo von Anthropic"
    mock_anthropic_cls.assert_called_once_with(api_key="sk-ant-test")
    mock_client.messages.create.assert_called_once_with(
        model="claude-haiku-4-5",
        max_tokens=20,
        temperature=0.0,
        messages=[{"role": "user", "content": "Test-Prompt"}],
    )


def test_llm_call_openai_returns_text(mocker):
    fake_message = MagicMock(content="Hallo von OpenAI")
    fake_choice = MagicMock(message=fake_message)
    fake_response = MagicMock(choices=[fake_choice])
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = fake_response
    mock_openai_cls = mocker.patch("openai.OpenAI", return_value=mock_client)

    result = llm.llm_call(
        provider="openai",
        api_key="sk-test",
        model="gpt-5-mini",
        prompt="Test-Prompt",
        max_tokens=20,
        temperature=0.0,
    )

    assert result == "Hallo von OpenAI"
    mock_openai_cls.assert_called_once_with(api_key="sk-test")
    mock_client.chat.completions.create.assert_called_once_with(
        model="gpt-5-mini",
        messages=[{"role": "user", "content": "Test-Prompt"}],
        max_tokens=20,
        temperature=0.0,
    )


def test_llm_call_google_returns_text(mocker):
    fake_response = MagicMock(text="Hallo von Google")
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = fake_response
    mock_genai_cls = mocker.patch("google.genai.Client", return_value=mock_client)

    result = llm.llm_call(
        provider="google",
        api_key="AIza-test",
        model="gemini-2.5-flash-lite",
        prompt="Test-Prompt",
        max_tokens=20,
        temperature=0.0,
    )

    assert result == "Hallo von Google"
    mock_genai_cls.assert_called_once_with(api_key="AIza-test")
    mock_client.models.generate_content.assert_called_once()


def test_llm_call_unknown_provider_falls_back_to_anthropic(mocker):
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="Fallback-Antwort")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = fake_response
    mocker.patch("src.llm.Anthropic", return_value=mock_client)

    result = llm.llm_call(
        provider="foobar",
        api_key="sk-ant-test",
        model="claude-haiku-4-5",
        prompt="Test-Prompt",
        max_tokens=20,
        temperature=0.0,
    )

    assert result == "Fallback-Antwort"


def test_llm_call_does_not_log_api_key(mocker, caplog):
    fake_response = MagicMock()
    fake_response.content = [MagicMock(text="Antwort")]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = fake_response
    mocker.patch("src.llm.Anthropic", return_value=mock_client)

    secret_key = "sk-ant-super-secret-do-not-log"
    with caplog.at_level(logging.DEBUG, logger="vizpatch.llm"):
        llm.llm_call(
            provider="anthropic",
            api_key=secret_key,
            model="claude-haiku-4-5",
            prompt="Test-Prompt",
            max_tokens=20,
            temperature=0.0,
        )

    for record in caplog.records:
        assert secret_key not in record.getMessage()
        for value in getattr(record, "__dict__", {}).values():
            assert value != secret_key
