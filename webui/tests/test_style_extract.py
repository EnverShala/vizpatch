"""Tests für extract_style() (STY-01/04/05, D-52..D-57).

Mockt imap_tools.MailBox + llm.llm_call analog test_llm_seed.py. Deckt ab:
1. Happy-Path (6 Abschnitte im Prompt-Input, redigierte Bodies)
2. PII läuft vor dem LLM-Call (IBAN im Body wird redigiert)
3. Real-Reply-Filter (Fwd/Ein-Wort-Antworten werden verworfen)
4. StyleExtractionEmpty bei < 3 verwertbaren Mails ohne Freitext
5. Graceful bei fehlendem/gescheitertem Sent-Ordner (kein Crash)
6. Provider-agnostisches Draft-Modell (D-55)
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def _make_prompt_file(tmp_path):
    p = tmp_path / "style-extract.txt"
    p.write_text(
        "Analysiere:\n\n"
        "## Anrede\n## Du/Sie\n## Grußformel\n## Satzlänge\n## Formalität\n## typische Wendungen\n\n"
        "# Mails\n{sent_mails}\n\n# Freitext\n{manual_style_note}\n\n# Ausgabe:",
        encoding="utf-8",
    )
    return p


def _write_agent_env(agent_id, provider="anthropic", model_draft=None, sent_folder=None):
    import src.agents_io as agents_io
    updates = {
        "IMAP_USER": "info@ionos.de",
        "IMAP_PASSWORD": "imap-pw",
        "LLM_API_KEY": "sk-test-key",
        "LLM_PROVIDER": provider,
    }
    if model_draft:
        updates["MODEL_DRAFT"] = model_draft
    if sent_folder:
        updates["IMAP_SENT_FOLDER"] = sent_folder
    agents_io.write_env(agent_id, updates)


def _msg(subject, text="", html=None, in_reply_to=None):
    m = MagicMock()
    m.subject = subject
    m.text = text
    m.html = html
    headers = {}
    if in_reply_to:
        headers["in-reply-to"] = (in_reply_to,)
    m.headers = headers
    return m


def _fake_mailbox(messages, sent_flag=True, fetch_raises=False, login_raises=False):
    mailbox = MagicMock()
    mailbox.__enter__ = MagicMock(return_value=mailbox)
    mailbox.__exit__ = MagicMock(return_value=False)
    if login_raises:
        mailbox.login.side_effect = RuntimeError("auth failed")

    folder_info = MagicMock()
    folder_info.name = "Gesendete Objekte"
    folder_info.flags = ("\\Sent",) if sent_flag else ()
    mailbox.folder.list.return_value = [folder_info]

    if fetch_raises:
        mailbox.folder.set.side_effect = RuntimeError("no such mailbox")
    mailbox.fetch.return_value = list(messages) if not fetch_raises else iter(messages)
    return mailbox


_LONG_REPLY_1 = "Hallo, vielen Dank für Ihre Anfrage. Wir kümmern uns morgen darum. Viele Grüße"
_LONG_REPLY_2 = "Guten Tag, Ihre Bestellung ist unterwegs und kommt bald bei Ihnen an. Grüße"
_LONG_REPLY_3 = "Moin, klar, das können wir so machen, ich melde mich die Tage nochmal bei Ihnen."


def _mock_llm_call(mocker, return_text="## Anrede\nDu\n## Du/Sie\nDu\n## Grußformel\nViele Grüße\n"
                                        "## Satzlänge\nkurz\n## Formalität\nlocker\n## typische Wendungen\nMoin"):
    return mocker.patch("src.style_extract.llm.llm_call", return_value=return_text)


def test_extract_style_happy_path_builds_prompt_with_six_sections(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_STYLE_EXTRACT_PROMPT", str(_make_prompt_file(tmp_path)))
    _write_agent_env("info")

    messages = [
        _msg("Re: Frage", text=_LONG_REPLY_1, in_reply_to="<abc@x.de>"),
        _msg("Re: Frage 2", text=_LONG_REPLY_2, in_reply_to="<def@x.de>"),
        _msg("AW: Frage 3", text=_LONG_REPLY_3, in_reply_to="<ghi@x.de>"),
    ]
    mock_mailbox = _fake_mailbox(messages)
    mocker.patch("src.style_extract.MailBox", return_value=mock_mailbox)
    mock_llm = _mock_llm_call(mocker)

    import src.style_extract as style_extract
    result = style_extract.extract_style("info")

    assert "Anrede" in result
    prompt = mock_llm.call_args.args[3]
    assert "## Anrede" in prompt
    assert "## Du/Sie" in prompt
    assert "## Grußformel" in prompt
    assert "## Satzlänge" in prompt
    assert "## Formalität" in prompt
    assert "## typische Wendungen" in prompt
    assert "vielen Dank für Ihre Anfrage" in prompt


def test_pii_runs_before_llm(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_STYLE_EXTRACT_PROMPT", str(_make_prompt_file(tmp_path)))
    _write_agent_env("info")

    iban_body = (
        "Hallo, bitte überweisen Sie den Betrag auf DE89370400440532013000, "
        "das ist unsere Bankverbindung für die Rechnung. Danke und Grüße."
    )
    messages = [
        _msg("Re: Rechnung", text=iban_body, in_reply_to="<a@x.de>"),
        _msg("Re: Frage 2", text=_LONG_REPLY_2, in_reply_to="<b@x.de>"),
        _msg("Re: Frage 3", text=_LONG_REPLY_3, in_reply_to="<c@x.de>"),
    ]
    mock_mailbox = _fake_mailbox(messages)
    mocker.patch("src.style_extract.MailBox", return_value=mock_mailbox)
    mock_llm = _mock_llm_call(mocker)

    import src.style_extract as style_extract
    style_extract.extract_style("info")

    prompt = mock_llm.call_args.args[3]
    assert "DE89370400440532013000" not in prompt
    assert "[IBAN_REDACTED]" in prompt


def test_real_reply_filter_discards_forwards_and_one_word_bodies(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_STYLE_EXTRACT_PROMPT", str(_make_prompt_file(tmp_path)))
    _write_agent_env("info")

    messages = [
        _msg("Re: Frage", text=_LONG_REPLY_1, in_reply_to="<a@x.de>"),
        _msg("Re: Frage 2", text=_LONG_REPLY_2, in_reply_to="<b@x.de>"),
        _msg("Re: Frage 3", text=_LONG_REPLY_3, in_reply_to="<c@x.de>"),
        _msg("Fwd: Interne Weiterleitung", text=_LONG_REPLY_1, in_reply_to="<d@x.de>"),
        _msg("Wg: Weiterleitung", text=_LONG_REPLY_2, in_reply_to="<e@x.de>"),
        _msg("Re: Danke", text="Danke.", in_reply_to="<f@x.de>"),
    ]
    mock_mailbox = _fake_mailbox(messages)
    mocker.patch("src.style_extract.MailBox", return_value=mock_mailbox)
    mock_llm = _mock_llm_call(mocker)

    import src.style_extract as style_extract
    style_extract.extract_style("info")

    prompt = mock_llm.call_args.args[3]
    assert "Interne Weiterleitung" not in prompt
    assert "Danke." not in prompt


def test_style_extraction_empty_raises_when_too_few_mails_and_no_note(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_STYLE_EXTRACT_PROMPT", str(_make_prompt_file(tmp_path)))
    _write_agent_env("info")

    messages = [_msg("Re: Frage", text=_LONG_REPLY_1, in_reply_to="<a@x.de>")]
    mock_mailbox = _fake_mailbox(messages)
    mocker.patch("src.style_extract.MailBox", return_value=mock_mailbox)
    _mock_llm_call(mocker)

    import src.style_extract as style_extract
    with pytest.raises(style_extract.StyleExtractionEmpty):
        style_extract.extract_style("info")


def test_manual_style_note_alone_is_sufficient(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_STYLE_EXTRACT_PROMPT", str(_make_prompt_file(tmp_path)))
    _write_agent_env("info")
    import src.agents_io as agents_io
    agents_io.write_style_note_atomic("info", "Wir duzen immer, sehr locker im Ton.")

    mock_mailbox = _fake_mailbox([])
    mocker.patch("src.style_extract.MailBox", return_value=mock_mailbox)
    mock_llm = _mock_llm_call(mocker)

    import src.style_extract as style_extract
    result = style_extract.extract_style("info")

    assert "Anrede" in result
    prompt = mock_llm.call_args.args[3]
    assert "Wir duzen immer, sehr locker im Ton." in prompt


def test_graceful_when_sent_folder_missing_no_crash(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_STYLE_EXTRACT_PROMPT", str(_make_prompt_file(tmp_path)))
    _write_agent_env("info")
    import src.agents_io as agents_io
    agents_io.write_style_note_atomic("info", "Freitext reicht als Fallback.")

    mock_mailbox = _fake_mailbox([], fetch_raises=True)
    mocker.patch("src.style_extract.MailBox", return_value=mock_mailbox)
    mock_llm = _mock_llm_call(mocker)

    import src.style_extract as style_extract
    result = style_extract.extract_style("info")

    assert "Anrede" in result
    mock_llm.assert_called_once()


def test_graceful_when_login_fails_no_crash(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_STYLE_EXTRACT_PROMPT", str(_make_prompt_file(tmp_path)))
    _write_agent_env("info")
    import src.agents_io as agents_io
    agents_io.write_style_note_atomic("info", "Freitext reicht als Fallback.")

    mock_mailbox = _fake_mailbox([], login_raises=True)
    mocker.patch("src.style_extract.MailBox", return_value=mock_mailbox)
    mock_llm = _mock_llm_call(mocker)

    import src.style_extract as style_extract
    result = style_extract.extract_style("info")

    assert "Anrede" in result
    mock_llm.assert_called_once()


def test_missing_api_key_raises(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "u@x.de", "IMAP_PASSWORD": "pw"})

    import src.style_extract as style_extract
    with pytest.raises(RuntimeError):
        style_extract.extract_style("info")


def test_invalid_agent_id_raises_value_error(tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.style_extract as style_extract
    with pytest.raises(ValueError):
        style_extract.extract_style("../evil")


def test_provider_agnostic_draft_model_resolution(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_STYLE_EXTRACT_PROMPT", str(_make_prompt_file(tmp_path)))
    _write_agent_env("info", provider="openai")

    messages = [
        _msg("Re: Frage", text=_LONG_REPLY_1, in_reply_to="<a@x.de>"),
        _msg("Re: Frage 2", text=_LONG_REPLY_2, in_reply_to="<b@x.de>"),
        _msg("Re: Frage 3", text=_LONG_REPLY_3, in_reply_to="<c@x.de>"),
    ]
    mock_mailbox = _fake_mailbox(messages)
    mocker.patch("src.style_extract.MailBox", return_value=mock_mailbox)
    mock_llm = _mock_llm_call(mocker)

    import src.style_extract as style_extract
    style_extract.extract_style("info")

    call_args = mock_llm.call_args.args
    assert call_args[0] == "openai"
    assert call_args[2] == style_extract.MODEL_DRAFT_DEFAULTS["openai"]


def test_no_direct_anthropic_call_in_style_extract():
    import inspect
    import src.style_extract as style_extract
    source = inspect.getsource(style_extract)
    assert "Anthropic(" not in source
