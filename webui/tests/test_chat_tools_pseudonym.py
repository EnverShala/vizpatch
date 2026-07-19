"""Tests für die vollständige Pseudonymisierung der agentischen Tool-Use-Schleife
und des Fallback-Chats (Phase 10, Plan 10-03, ANON-03/04).

Deckt die drei kritischen Pitfalls aus 10-RESEARCH.md ab:
- Pitfall 1 (Truncate-vor-Redact): bereits in Plan 10-01/10-02/Task 1 dieses
  Plans regressionsabgesichert.
- Pitfall 2 (Streaming-Chunk zerreißt Platzhalter): `test_fallback_chat_streaming_deanonymized`.
- Pitfall 3 (Tool-Argument nicht de-anonymisiert vor Handler-Aufruf, KRITISCHSTER
  Einzeltest der Phase): `test_tool_argument_deanonymized_before_handler`.

Zusätzlich: geteilte Instanz über alle Runden (`test_shared_instance_across_rounds`),
Initial-Message-Anonymisierung (`test_initial_message_anonymized`) und der
Flag-aus-Rückfall (`test_flag_off_no_anonymization`).
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock

import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def _chat_system_prompt():
    from pathlib import Path

    return Path(__file__).resolve().parent.parent / "prompts" / "chat-system.txt"


def _write_agent_env(agent_id, provider="anthropic", api_key="sk-ant-test-key", enable_pii="true"):
    import src.agents_io as agents_io

    agents_io.write_env(
        agent_id,
        {
            "IMAP_USER": "info@ionos.de",
            "IMAP_PASSWORD": "imap-pw",
            "LLM_API_KEY": api_key,
            "LLM_PROVIDER": provider,
            "ENABLE_PII_REDACTION": enable_pii,
        },
    )


def _msg(
    subject="Re: Frage",
    text="Hallo, hier ist die Antwort.",
    uid="42",
    from_="kunde@example.com",
    to=(),
    headers=None,
):
    m = MagicMock()
    m.subject = subject
    m.text = text
    m.html = None
    m.uid = uid
    m.from_ = from_
    m.to = to
    m.date = None
    m.headers = headers or {}
    return m


def _fake_mailbox(messages=None):
    mailbox = MagicMock()
    mailbox.__enter__ = MagicMock(return_value=mailbox)
    mailbox.__exit__ = MagicMock(return_value=False)
    msgs = list(messages or [])

    def _fetch_side_effect(*_args, **_kwargs):
        return [] if mailbox.move.called else list(msgs)

    mailbox.fetch.side_effect = _fetch_side_effect
    return mailbox


def _text_block(text):
    return types.SimpleNamespace(type="text", text=text)


def _tool_use_block(name, tool_input, tool_id="toolu_1"):
    return types.SimpleNamespace(type="tool_use", id=tool_id, name=name, input=tool_input)


def _fake_response(stop_reason, content):
    return types.SimpleNamespace(stop_reason=stop_reason, content=content)


IBAN = "DE89 3704 0044 0532 0130 00"


def test_tool_argument_deanonymized_before_handler(mocker, tmp_path, monkeypatch):
    """KRITISCH (Pitfall 3): das LLM zitiert einen Platzhalter aus dem
    pseudonymisierten Mail-Kontext in `entwurf_bearbeiten.neuer_text` — der
    tatsächlich an den Handler übergebene Wert MUSS die echte IBAN enthalten,
    NIE den wörtlichen Platzhalter-String."""
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(_chat_system_prompt()))
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info")

    import src.chat_tools as chat_tools

    # Die IBAN im Mail-Kontext wird beim Bau der Initial-Message zu [IBAN_1] getaggt.
    round1 = _fake_response(
        "tool_use",
        [
            _tool_use_block(
                "entwurf_bearbeiten",
                {"uid": "5", "neuer_text": "Ihre IBAN lautet [IBAN_1]."},
            )
        ],
    )
    round2 = _fake_response("end_turn", [_text_block("Erledigt.")])

    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [round1, round2]
    mocker.patch("src.chat_tools.Anthropic", return_value=mock_client)

    entwurf_bearbeiten_mock = MagicMock(return_value={"ok": True})
    monkeypatch.setitem(chat_tools.TOOL_HANDLERS, "entwurf_bearbeiten", entwurf_bearbeiten_mock)

    mail_context = {"subject": "Zahlung", "sender": "kunde@example.com", "body": f"IBAN: {IBAN}"}
    list(chat_tools.run_agentic_chat("info", "Bitte Entwurf anpassen", mail_context=mail_context))

    entwurf_bearbeiten_mock.assert_called_once()
    call_kwargs = entwurf_bearbeiten_mock.call_args.kwargs
    assert call_kwargs["uid"] == "5"
    assert IBAN in call_kwargs["neuer_text"]
    assert "[IBAN_1]" not in call_kwargs["neuer_text"]
    # entwurf_bearbeiten ist NICHT in _ANON_AWARE_TOOLS -> kein anonymizer-Kwarg.
    assert "anonymizer" not in call_kwargs


def test_text_block_deanonymized_before_yield(mocker, tmp_path, monkeypatch):
    """Ein Assistant-Text-Block, der einen Platzhalter zitiert, muss VOR dem
    yield an den Betreiber de-anonymisiert werden (T-10-14)."""
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(_chat_system_prompt()))
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info")

    import src.chat_tools as chat_tools

    round1 = _fake_response("end_turn", [_text_block("Die IBAN ist [IBAN_1].")])
    mock_client = MagicMock()
    mock_client.messages.create.return_value = round1
    mocker.patch("src.chat_tools.Anthropic", return_value=mock_client)

    events = list(
        chat_tools.run_agentic_chat("info", f"Meine IBAN ist {IBAN}, bitte notieren.")
    )

    text_events = [e["text"] for e in events if e["type"] == "text"]
    assert any(IBAN in t for t in text_events)
    assert not any("[IBAN_1]" in t for t in text_events)


def test_initial_message_anonymized(mocker, tmp_path, monkeypatch):
    """message + mail_context.body mit PII -> die an client.messages.create
    übergebene Message-Liste enthält Tags statt Rohwerten. System-Prompt bleibt
    roh (D-08 — hier nur strukturell geprüft: system wird unverändert übergeben)."""
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(_chat_system_prompt()))
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info")

    import src.chat_tools as chat_tools

    round1 = _fake_response("end_turn", [_text_block("Alles klar.")])
    mock_client = MagicMock()
    mock_client.messages.create.return_value = round1
    mocker.patch("src.chat_tools.Anthropic", return_value=mock_client)

    mail_context = {"subject": "Zahlung", "sender": "kunde@example.com", "body": f"IBAN: {IBAN}"}
    list(chat_tools.run_agentic_chat("info", f"Kontakt: max@kunde.de, IBAN {IBAN}", mail_context=mail_context))

    call_kwargs = mock_client.messages.create.call_args.kwargs
    messages_sent = call_kwargs["messages"]
    serialized = str(messages_sent)
    assert IBAN not in serialized
    assert "max@kunde.de" not in serialized
    assert "[IBAN_1]" in serialized
    assert "[EMAIL_1]" in serialized


def test_shared_instance_across_rounds(mocker, tmp_path, monkeypatch):
    """Derselbe Wert in Runde-1-Tool-Ergebnis und Runde-2-LLM-Zitat trägt
    denselben Tag (eine Anonymizer-Instanz pro Chat-Turn, über alle Runden)."""
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(_chat_system_prompt()))
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info")

    import src.chat_tools as chat_tools

    mock_mailbox = _fake_mailbox([_msg(text=f"Bitte überweisen Sie auf {IBAN}, danke.")])
    mocker.patch("src.chat_tools.MailBox", return_value=mock_mailbox)

    round1 = _fake_response("tool_use", [_tool_use_block("mails_suchen", {"query": "Rechnung"})])
    # Runde 2: das LLM zitiert exakt den Tag, den es im Tool-Ergebnis von Runde 1 gesehen hat.
    round2 = _fake_response("end_turn", [_text_block("Ich fand: [IBAN_1]")])
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = [round1, round2]
    mocker.patch("src.chat_tools.Anthropic", return_value=mock_client)

    events = list(chat_tools.run_agentic_chat("info", "Suche nach Rechnung"))

    # Das Tool-Ergebnis, das an Runde 2 zurückgeschickt wurde, muss denselben Tag tragen.
    second_call_messages = mock_client.messages.create.call_args_list[1].kwargs["messages"]
    tool_result_msg = second_call_messages[-1]
    tool_result_text = tool_result_msg["content"][0]["content"]
    assert "[IBAN_1]" in tool_result_text
    assert IBAN not in tool_result_text

    # Die finale, an den Betreiber gestreamte Antwort enthält die ECHTE IBAN.
    final_text = "".join(e["text"] for e in events if e["type"] == "text")
    assert IBAN in final_text
    assert "[IBAN_1]" not in final_text


def test_fallback_chat_streaming_deanonymized(mocker, tmp_path, monkeypatch):
    """Nicht-Anthropic-Provider: build_chat_prompt bekommt den Anonymizer, der
    Stream wird durch deanonymize_stream geführt; ein über zwei Chunks
    fragmentierter Tag (Pitfall 2) wird korrekt zur echten IBAN aufgelöst."""
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(_chat_system_prompt()))
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info", provider="openai", api_key="sk-openai-test-key")

    import src.chat_tools as chat_tools

    mocker.patch("src.chat_tools.Anthropic")
    # Der Tag [IBAN_1] wird über zwei Stream-Chunks zerrissen.
    mocker.patch(
        "src.chat_tools.chat.stream_chat",
        return_value=iter(["Ihre IBAN ist [IBA", "N_1]. Danke."]),
    )

    events = list(chat_tools.run_agentic_chat("info", f"Meine IBAN ist {IBAN}"))

    full_text = "".join(e["text"] for e in events)
    assert IBAN in full_text
    assert "[IBAN_1]" not in full_text
    assert "[IBA" not in full_text


def test_flag_off_no_anonymization(mocker, tmp_path, monkeypatch):
    """ENABLE_PII_REDACTION=false -> keine Anonymizer-Instanz, Rohwerte im
    Prompt, keine De-Anonymisierung (Rückfall auf Alt-Verhalten vor Phase 10)."""
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(_chat_system_prompt()))
    _setup_env(tmp_path, monkeypatch)
    _write_agent_env("info", provider="openai", api_key="sk-openai-test-key", enable_pii="false")

    import src.chat_tools as chat_tools

    mocker.patch("src.chat_tools.Anthropic")
    build_chat_prompt_spy = mocker.patch(
        "src.chat_tools.chat.build_chat_prompt", wraps=chat_tools.chat.build_chat_prompt
    )
    mocker.patch(
        "src.chat_tools.chat.stream_chat",
        return_value=iter([f"Ihre IBAN ist {IBAN}. Danke."]),
    )

    events = list(chat_tools.run_agentic_chat("info", f"Meine IBAN ist {IBAN}"))

    # anonymizer=None wurde an build_chat_prompt durchgereicht.
    assert build_chat_prompt_spy.call_args.kwargs["anonymizer"] is None

    full_text = "".join(e["text"] for e in events)
    assert IBAN in full_text
