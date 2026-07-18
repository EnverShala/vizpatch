"""Tests für die IMAP-Werkzeuge des Agenten-Chats (Phase 9, Plan 09-01 Task 1, CTOOL-02 Teil 1).

Deckt ab:
1. `open_agent_mailbox`/`mails_suchen`: IMAP-Verbindungsmuster (gemockt, analog
   test_style_extract._fake_mailbox), PII-Redaction VOR Rückgabe (D-78/T-09-02),
   graceful bei IMAP-/Login-/Fetch-Fehlern (T-09-05, kein Crash).
2. Registry-Kontrakt: TOOL_SCHEMAS/TOOL_HANDLERS enthalten genau `mails_suchen`,
   `wrap_tool_result` trägt den Untrusted-DATEN-Anker (D-78).
3. Struktureller Drift-Guard-Nachweis (D-73): kein `llm`-Import in chat_tools.py.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


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
