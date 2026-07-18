"""Tests für die agentische Tool-Use-Schleife (Phase 9, Plan 09-01, CTOOL-01/02).

Deckt ab:
1. `open_agent_mailbox`/`mails_suchen`: IMAP-Verbindungsmuster (gemockt, analog
   test_style_extract._fake_mailbox), PII-Redaction VOR Rückgabe (D-78/T-09-02),
   graceful bei IMAP-/Login-/Fetch-Fehlern (T-09-05, kein Crash).
2. Registry-Kontrakt: TOOL_SCHEMAS/TOOL_HANDLERS enthalten genau `mails_suchen`,
   `wrap_tool_result` trägt den Untrusted-DATEN-Anker (D-78).
3. Struktureller Drift-Guard-Nachweis (D-73): kein `llm`-Import in chat_tools.py.
4. `run_agentic_chat`: Anthropic-Tool-Use-Schleife mit Rundenlimit (T-09-04),
   sauberer Fallback für Nicht-Anthropic-Provider (T-09-06), unbekanntes
   Werkzeug crasht nicht, api_key erscheint in keinem Log-Aufruf (T-09-03).
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock

import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def _chat_system_prompt(tmp_path):
    from pathlib import Path

    real_path = Path(__file__).resolve().parent.parent / "prompts" / "chat-system.txt"
    return real_path


def _write_agent_env(agent_id, provider="anthropic", api_key="sk-ant-test-key"):
    import src.agents_io as agents_io

    agents_io.write_env(
        agent_id,
        {
            "IMAP_USER": "info@ionos.de",
            "IMAP_PASSWORD": "imap-pw",
            "LLM_API_KEY": api_key,
            "LLM_PROVIDER": provider,
        },
    )


def _msg(subject="Re: Frage", text="Hallo, hier ist die Antwort.", uid="42", from_="kunde@example.com"):
    m = MagicMock()
    m.subject = subject
    m.text = text
    m.html = None
    m.uid = uid
    m.from_ = from_
    m.date = None
    return m


def _fake_mailbox(messages=None, login_raises=False, fetch_raises=False, folder_set_raises=False):
    mailbox = MagicMock()
    mailbox.__enter__ = MagicMock(return_value=mailbox)
    mailbox.__exit__ = MagicMock(return_value=False)
    if login_raises:
        mailbox.login.side_effect = RuntimeError("auth failed")
    if folder_set_raises:
        mailbox.folder.set.side_effect = RuntimeError("no such mailbox")
    if fetch_raises:
        mailbox.fetch.side_effect = RuntimeError("search failed")
    else:
        mailbox.fetch.return_value = list(messages or [])
    return mailbox


def test_mails_suchen_redacts_pii_before_returning(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info")

    iban_body = "Bitte überweisen Sie auf DE89370400440532013000, danke."
    mock_mailbox = _fake_mailbox([_msg(text=iban_body)])
    mocker.patch("src.chat_tools.MailBox", return_value=mock_mailbox)

    import src.chat_tools as chat_tools

    result = chat_tools.mails_suchen("info", query="Rechnung")

    assert "fehler" not in result
    assert len(result["treffer"]) == 1
    body = result["treffer"][0]["body_redigiert"]
    assert "DE89370400440532013000" not in body
    assert "[IBAN_REDACTED]" in body


def test_mails_suchen_login_failure_returns_error_dict_no_crash(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info")

    mock_mailbox = _fake_mailbox(login_raises=True)
    mocker.patch("src.chat_tools.MailBox", return_value=mock_mailbox)

    import src.chat_tools as chat_tools

    result = chat_tools.mails_suchen("info", query="irrelevant")

    assert "fehler" in result
    assert result["treffer"] == []


def test_mails_suchen_fetch_failure_returns_error_dict_no_crash(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info")

    mock_mailbox = _fake_mailbox(fetch_raises=True)
    mocker.patch("src.chat_tools.MailBox", return_value=mock_mailbox)

    import src.chat_tools as chat_tools

    result = chat_tools.mails_suchen("info")

    assert "fehler" in result
    assert result["treffer"] == []


def test_mails_suchen_invalid_agent_id_raises_value_error(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.chat_tools as chat_tools

    with pytest.raises(ValueError):
        chat_tools.mails_suchen("../evil")


def test_mails_suchen_respects_limit_and_folder(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info")

    messages = [_msg(uid=str(i)) for i in range(5)]
    mock_mailbox = _fake_mailbox(messages)
    mocker.patch("src.chat_tools.MailBox", return_value=mock_mailbox)

    import src.chat_tools as chat_tools

    result = chat_tools.mails_suchen("info", folder="Archiv", limit=3)

    mock_mailbox.folder.set.assert_called_once_with("Archiv")
    assert mock_mailbox.fetch.call_args.kwargs["limit"] == 3
    assert result["ordner"] == "Archiv"


def test_tool_handlers_registry_contains_exactly_mails_suchen():
    import src.chat_tools as chat_tools

    assert set(chat_tools.TOOL_HANDLERS.keys()) == {"mails_suchen"}
    schema_names = {schema["name"] for schema in chat_tools.TOOL_SCHEMAS}
    assert schema_names == {"mails_suchen"}


def test_wrap_tool_result_contains_untrusted_data_anchor():
    import src.chat_tools as chat_tools

    wrapped = chat_tools.wrap_tool_result("mails_suchen", {"treffer": []})
    assert "UNTRUSTED" in wrapped.upper()
    assert "mails_suchen" in wrapped


def test_chat_tools_defines_required_contract_symbols():
    import inspect
    import src.chat_tools as chat_tools

    source = inspect.getsource(chat_tools)
    for needle in (
        "def open_agent_mailbox",
        "def mails_suchen",
        "TOOL_SCHEMAS",
        "TOOL_HANDLERS",
        "def wrap_tool_result",
    ):
        assert needle in source


def test_chat_tools_does_not_import_llm_module_but_calls_pii_crypto_provider_config():
    """D-73-Drift-Guard-Nachweis: chat_tools.py importiert NICHT `llm.py` (das
    ist llm.py's Provider-Dispatch-Sonderweg, den dieses Modul bewusst nicht
    nachbaut), ruft aber crypto/pii/provider_config auf."""
    import ast
    import inspect
    import src.chat_tools as chat_tools

    source = inspect.getsource(chat_tools)
    tree = ast.parse(source)

    top_level_import_names = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_import_names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            top_level_import_names.append(module)
            top_level_import_names.extend(alias.name for alias in node.names)

    assert "llm" not in top_level_import_names
    assert "crypto" in top_level_import_names
    assert "pii" in top_level_import_names
    assert any("provider_config" in n or n == "resolve_imap_config" for n in top_level_import_names)


# --- Task 2: run_agentic_chat — Anthropic-Tool-Use-Schleife + Fallback -------------


def _text_block(text):
    return types.SimpleNamespace(type="text", text=text)


def _tool_use_block(name, tool_input, tool_id="toolu_1"):
    return types.SimpleNamespace(type="tool_use", id=tool_id, name=name, input=tool_input)


def _fake_response(stop_reason, content):
    return types.SimpleNamespace(stop_reason=stop_reason, content=content)


def test_run_agentic_chat_two_round_tool_use_then_text(mocker, tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(_chat_system_prompt(tmp_path)))
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info", provider="anthropic")

    import src.chat_tools as chat_tools

    round1 = _fake_response("tool_use", [_tool_use_block("mails_suchen", {"query": "Rechnung"})])
    round2 = _fake_response("end_turn", [_text_block("Hier ist die Antwort.")])

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [round1, round2]
    mocker.patch("src.chat_tools.Anthropic", return_value=mock_client)
    monkeypatch.setitem(
        chat_tools.TOOL_HANDLERS, "mails_suchen", MagicMock(return_value={"treffer": []})
    )

    events = list(chat_tools.run_agentic_chat("info", "Suche bitte nach Rechnung"))

    assert any(e["type"] == "tool" for e in events)
    assert events[-1]["type"] == "text"
    assert "Hier ist die Antwort." in "".join(e["text"] for e in events if e["type"] == "text")
    assert mock_client.messages.create.call_count == 2


def test_run_agentic_chat_fallback_for_non_anthropic_provider(mocker, tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(_chat_system_prompt(tmp_path)))
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info", provider="openai", api_key="sk-openai-test-key")

    import src.chat_tools as chat_tools

    mock_anthropic_cls = mocker.patch("src.chat_tools.Anthropic")
    mocker.patch("src.chat_tools.chat.stream_chat", return_value=iter(["Hallo ", "Welt"]))

    events = list(chat_tools.run_agentic_chat("info", "Hi"))

    mock_anthropic_cls.assert_not_called()
    assert [e["type"] for e in events] == ["text", "text"]
    assert "".join(e["text"] for e in events) == "Hallo Welt"


def test_run_agentic_chat_disabled_tools_flag_forces_fallback(mocker, tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(_chat_system_prompt(tmp_path)))
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info", provider="anthropic")
    monkeypatch.setenv("ENABLE_CHAT_TOOLS", "false")

    import src.chat_tools as chat_tools

    mock_anthropic_cls = mocker.patch("src.chat_tools.Anthropic")
    mocker.patch("src.chat_tools.chat.stream_chat", return_value=iter(["Beratung"]))

    events = list(chat_tools.run_agentic_chat("info", "Hi"))

    mock_anthropic_cls.assert_not_called()
    assert events == [{"type": "text", "text": "Beratung"}]


def test_run_agentic_chat_max_tool_rounds_terminates(mocker, tmp_path, monkeypatch):
    """T-09-04: Anthropic-Mock liefert IMMER stop_reason=tool_use — der Generator
    MUSS nach MAX_TOOL_ROUNDS mit einem abschliessenden Text-Event terminieren
    (kein Endlos-Loop)."""
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(_chat_system_prompt(tmp_path)))
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info", provider="anthropic")

    import src.chat_tools as chat_tools

    always_tool_use = _fake_response("tool_use", [_tool_use_block("mails_suchen", {})])
    mock_client = MagicMock()
    mock_client.messages.create.return_value = always_tool_use
    mocker.patch("src.chat_tools.Anthropic", return_value=mock_client)
    monkeypatch.setitem(
        chat_tools.TOOL_HANDLERS, "mails_suchen", MagicMock(return_value={"treffer": []})
    )

    events = list(chat_tools.run_agentic_chat("info", "Immer weiter suchen"))

    assert mock_client.messages.create.call_count == chat_tools.MAX_TOOL_ROUNDS
    assert events[-1]["type"] == "text"
    assert "Runden" in events[-1]["text"] or "Werkzeug" in events[-1]["text"]


def test_run_agentic_chat_unknown_tool_name_no_crash(mocker, tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(_chat_system_prompt(tmp_path)))
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info", provider="anthropic")

    import src.chat_tools as chat_tools

    round1 = _fake_response("tool_use", [_tool_use_block("loesche_alles", {})])
    round2 = _fake_response("end_turn", [_text_block("Das kann ich nicht.")])
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [round1, round2]
    mocker.patch("src.chat_tools.Anthropic", return_value=mock_client)

    events = list(chat_tools.run_agentic_chat("info", "Loesche alles"))

    assert events[-1]["type"] == "text"
    assert "Das kann ich nicht." in events[-1]["text"]
    # Der unbekannte Tool-Name landet als Fehler im tool_result der zweiten Runde.
    second_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
    tool_result_msg = second_call_messages[-1]
    assert tool_result_msg["role"] == "user"
    assert "Unbekanntes Werkzeug" in tool_result_msg["content"][0]["content"]


def test_run_agentic_chat_propagates_chat_config_error_for_missing_key(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    import src.chat as chat
    import src.chat_tools as chat_tools

    agents_io.write_env("info", {"IMAP_USER": "u@x.de", "IMAP_PASSWORD": "pw"})

    with pytest.raises(chat.ChatConfigError):
        list(chat_tools.run_agentic_chat("info", "Hi"))


def test_no_api_key_in_logger_calls():
    """T-09-03: `api_key` darf in keinem `logger.*`-Aufruf von chat_tools.py
    vorkommen (Kommentare/Docstrings ausgenommen)."""
    from pathlib import Path

    source_path = Path(__file__).resolve().parent.parent / "src" / "chat_tools.py"
    text = source_path.read_text(encoding="utf-8")

    in_logger_call = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("#"):
            continue
        if "logger." in line:
            in_logger_call = True
        if in_logger_call:
            assert "api_key" not in line, f"api_key erscheint in Logger-Kontext: {line}"
        if in_logger_call and line.endswith(")"):
            in_logger_call = False
