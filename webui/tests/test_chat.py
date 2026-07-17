"""Tests für den Streaming-Adapter webui/src/chat.py (Phase 7, Plan 07-01, CHAT-01/03).

Mockt die SDK-Clients analog test_llm.py (agent) / test_style_extract.py (webui).
Deckt ab:
1. stream_chat(provider="anthropic") yieldet mehrere Chunks in Reihenfolge
2. resolve_chat_target liefert (provider, api_key, model) aus der Agent-.env
3. invalider agent_id -> ValueError (agents_io-Guard)
4. fehlender LLM_API_KEY -> ChatConfigError, kein Crash im SDK
5. api_key taucht in keinem Log-Record auf (T-05-08-Muster)
6. unbekannter/leerer Provider -> Anthropic-Streaming-Fallback
"""
from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def _write_agent_env(agent_id, provider=None, model_draft=None, api_key="sk-ant-test-key"):
    import src.agents_io as agents_io

    updates: dict[str, str] = {"LLM_API_KEY": api_key}
    if provider is not None:
        updates["LLM_PROVIDER"] = provider
    if model_draft:
        updates["MODEL_DRAFT"] = model_draft
    agents_io.write_env(agent_id, updates)


def _anthropic_stream_context(chunks):
    """Baut einen Context-Manager-Mock analog `client.messages.stream(...)`."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    cm.text_stream = iter(chunks)
    return cm


def test_stream_chat_anthropic_yields_chunks_in_order(mocker):
    import src.chat as chat

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = _anthropic_stream_context(["Hallo ", "vom ", "Chat"])
    mocker.patch("src.chat.Anthropic", return_value=mock_client)

    chunks = list(
        chat.stream_chat(
            provider="anthropic",
            api_key="sk-ant-test",
            model="claude-sonnet-4-6",
            prompt="Test-Prompt",
            max_tokens=200,
            temperature=0.7,
        )
    )

    assert chunks == ["Hallo ", "vom ", "Chat"]
    assert "".join(chunks) == "Hallo vom Chat"
    mock_client.messages.stream.assert_called_once_with(
        model="claude-sonnet-4-6",
        max_tokens=200,
        temperature=0.7,
        messages=[{"role": "user", "content": "Test-Prompt"}],
    )


def test_stream_chat_unknown_provider_falls_back_to_anthropic(mocker):
    import src.chat as chat

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = _anthropic_stream_context(["Fallback"])
    mocker.patch("src.chat.Anthropic", return_value=mock_client)

    chunks = list(
        chat.stream_chat(
            provider="foobar",
            api_key="sk-ant-test",
            model="claude-sonnet-4-6",
            prompt="Test-Prompt",
            max_tokens=200,
            temperature=0.7,
        )
    )

    assert chunks == ["Fallback"]


def test_stream_chat_empty_provider_falls_back_to_anthropic(mocker):
    import src.chat as chat

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = _anthropic_stream_context(["Default"])
    mocker.patch("src.chat.Anthropic", return_value=mock_client)

    chunks = list(
        chat.stream_chat(
            provider="",
            api_key="sk-ant-test",
            model="claude-sonnet-4-6",
            prompt="Test-Prompt",
            max_tokens=200,
            temperature=0.7,
        )
    )

    assert chunks == ["Default"]


def test_stream_chat_openai_yields_delta_chunks(mocker):
    import src.chat as chat

    def _chunk(content):
        delta = MagicMock(content=content)
        choice = MagicMock(delta=delta)
        return MagicMock(choices=[choice])

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = iter([_chunk("Hi "), _chunk(None), _chunk("there")])
    mocker.patch("openai.OpenAI", return_value=mock_client)

    chunks = list(
        chat.stream_chat(
            provider="openai",
            api_key="sk-test",
            model="gpt-5.1",
            prompt="Test-Prompt",
            max_tokens=200,
            temperature=0.7,
        )
    )

    assert chunks == ["Hi ", "there"]
    mock_client.chat.completions.create.assert_called_once_with(
        model="gpt-5.1",
        messages=[{"role": "user", "content": "Test-Prompt"}],
        max_completion_tokens=200,
        stream=True,
    )


def test_stream_chat_google_yields_text_chunks(mocker):
    import src.chat as chat

    mock_client = MagicMock()
    mock_client.models.generate_content_stream.return_value = iter(
        [MagicMock(text="Servus "), MagicMock(text=None), MagicMock(text="Welt")]
    )
    mocker.patch("google.genai.Client", return_value=mock_client)

    chunks = list(
        chat.stream_chat(
            provider="google",
            api_key="AIza-test",
            model="gemini-2.5-pro",
            prompt="Test-Prompt",
            max_tokens=200,
            temperature=0.7,
        )
    )

    assert chunks == ["Servus ", "Welt"]


def test_resolve_chat_target_decrypts_key_and_resolves_provider_model(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info", provider="anthropic", api_key="sk-ant-plaintext")

    import src.chat as chat

    provider, api_key, model = chat.resolve_chat_target("info")

    assert provider == "anthropic"
    assert api_key == "sk-ant-plaintext"
    assert model == "claude-sonnet-4-6"


def test_resolve_chat_target_defaults_provider_to_anthropic(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info", provider=None, api_key="sk-ant-plaintext")

    import src.chat as chat

    provider, _api_key, model = chat.resolve_chat_target("info")

    assert provider == "anthropic"
    assert model == "claude-sonnet-4-6"


def test_resolve_chat_target_uses_explicit_model_draft(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info", provider="openai", model_draft="gpt-custom", api_key="sk-test")

    import src.chat as chat

    provider, _api_key, model = chat.resolve_chat_target("info")

    assert provider == "openai"
    assert model == "gpt-custom"


def test_resolve_chat_target_invalid_agent_id_raises_value_error(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)

    import src.chat as chat

    with pytest.raises(ValueError):
        chat.resolve_chat_target("../evil")


def test_resolve_chat_target_missing_api_key_raises_chat_config_error(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", {"LLM_PROVIDER": "anthropic"})

    import src.chat as chat

    with pytest.raises(chat.ChatConfigError):
        chat.resolve_chat_target("info")


def test_stream_chat_does_not_log_api_key(mocker, caplog):
    import src.chat as chat

    mock_client = MagicMock()
    mock_client.messages.stream.return_value = _anthropic_stream_context(["Antwort"])
    mocker.patch("src.chat.Anthropic", return_value=mock_client)

    secret_key = "sk-ant-super-secret-do-not-log"
    with caplog.at_level(logging.DEBUG, logger="vizpatch.chat"):
        list(
            chat.stream_chat(
                provider="anthropic",
                api_key=secret_key,
                model="claude-sonnet-4-6",
                prompt="Test-Prompt",
                max_tokens=200,
                temperature=0.7,
            )
        )

    for record in caplog.records:
        assert secret_key not in record.getMessage()
        for value in getattr(record, "__dict__", {}).values():
            assert value != secret_key
