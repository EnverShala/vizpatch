import os
from unittest.mock import MagicMock

import pytest


def _make_prompt_file(tmp_path, content=None):
    p = tmp_path / "context-seed.txt"
    p.write_text(content or "Du bist Assistent.\n\n{firma_input}\n\n# Deine Ausgabe:", encoding="utf-8")
    return p


def _mock_anthropic(mocker, return_text="# About\nGenerated"):
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = return_text
    mock_message = MagicMock()
    mock_message.content = [mock_block]
    mock_client_instance = MagicMock()
    mock_client_instance.messages.create.return_value = mock_message
    mock_anthropic_class = mocker.patch("src.llm_seed.Anthropic", return_value=mock_client_instance)
    return mock_client_instance, mock_anthropic_class


def test_generate_calls_sonnet_with_correct_args(mocker, tmp_path, monkeypatch):
    prompt_file = _make_prompt_file(tmp_path)
    monkeypatch.setenv("WEBUI_SEED_PROMPT", str(prompt_file))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    mock_client, _ = _mock_anthropic(mocker)
    import src.llm_seed as llm_seed
    result = llm_seed.generate("Meine Tankstelle in Leonberg")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-sonnet-4-6"
    assert call_kwargs["max_tokens"] == 2000
    assert "Meine Tankstelle in Leonberg" in call_kwargs["messages"][0]["content"]
    assert "Generated" in result


def test_input_length_limit_5000(mocker, tmp_path, monkeypatch):
    prompt_file = _make_prompt_file(tmp_path)
    monkeypatch.setenv("WEBUI_SEED_PROMPT", str(prompt_file))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    import src.llm_seed as llm_seed
    with pytest.raises(ValueError):
        llm_seed.generate("x" * 5001)


def test_input_at_5000_is_valid(mocker, tmp_path, monkeypatch):
    prompt_file = _make_prompt_file(tmp_path)
    monkeypatch.setenv("WEBUI_SEED_PROMPT", str(prompt_file))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    _mock_anthropic(mocker)
    import src.llm_seed as llm_seed
    result = llm_seed.generate("x" * 5000)
    assert result == "# About\nGenerated"


def test_missing_api_key_raises(mocker, tmp_path, monkeypatch):
    prompt_file = _make_prompt_file(tmp_path)
    monkeypatch.setenv("WEBUI_SEED_PROMPT", str(prompt_file))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import src.llm_seed as llm_seed
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        llm_seed.generate("test")


def test_env_model_override(mocker, tmp_path, monkeypatch):
    prompt_file = _make_prompt_file(tmp_path)
    monkeypatch.setenv("WEBUI_SEED_PROMPT", str(prompt_file))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("MODEL_DRAFT", "claude-opus-4-6")
    mock_client, _ = _mock_anthropic(mocker)
    import src.llm_seed as llm_seed
    llm_seed.generate("test")
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-opus-4-6"


def test_empty_content_returns_empty_string(mocker, tmp_path, monkeypatch):
    prompt_file = _make_prompt_file(tmp_path)
    monkeypatch.setenv("WEBUI_SEED_PROMPT", str(prompt_file))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    mock_message = MagicMock()
    mock_message.content = []
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    mocker.patch("src.llm_seed.Anthropic", return_value=mock_client)
    import src.llm_seed as llm_seed
    result = llm_seed.generate("test")
    assert result == ""


def test_lazy_prompt_path_evaluation(mocker, tmp_path, monkeypatch):
    prompt_a = tmp_path / "seed_a.txt"
    prompt_a.write_text("Template A {firma_input}", encoding="utf-8")
    prompt_b = tmp_path / "seed_b.txt"
    prompt_b.write_text("Template B {firma_input}", encoding="utf-8")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    mock_block = MagicMock()
    mock_block.type = "text"
    mock_block.text = "Result from B"
    mock_message = MagicMock()
    mock_message.content = [mock_block]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    mocker.patch("src.llm_seed.Anthropic", return_value=mock_client)
    import src.llm_seed as llm_seed
    monkeypatch.setenv("WEBUI_SEED_PROMPT", str(prompt_b))
    result = llm_seed.generate("test")
    call_content = mock_client.messages.create.call_args.kwargs["messages"][0]["content"]
    assert "Template B" in call_content
