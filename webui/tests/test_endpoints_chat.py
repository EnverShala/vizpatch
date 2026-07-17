"""Tests für die Chat-Routen (Phase 7, Plan 07-01, CHAT-01/03/05).

Deckt ab:
(a) /chat/{id}/embed ohne Auth -> 401
(b) /chat/{id}/embed mit Auth -> 200, chrome-loses Partial (kein base.html-Erbe),
    referenziert /static/chat.js
(c) /chat/{id}/send streamt SSE (mockt chat.stream_chat)
(d) unbekannter agent_id: /embed -> 404 (list_agent_ids-Check); /send -> 400
    (ChatConfigError, kein Key gespeichert — PLAN-CHECKER-GUIDANCE: /send hat
    keinen Existenz-Check, nur Key-Resolution)
(e) invalider agent_id "../evil": /send -> 400 (ValueError aus agents_io-Guard);
    /embed -> 404 (Route matched nicht / Existenz-Check)
"""
from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _chat_system_prompt_path(monkeypatch):
    """/chat/{id}/send ruft seit Plan 07-02 build_system_prompt() auf — das
    braucht ein lesbares Template. Zeigt in allen Endpoint-Tests auf das echte,
    produktive `webui/prompts/chat-system.txt` (kein Docker-Pfad /app/... auf
    dem lokalen Test-Rechner verfügbar)."""
    real_path = Path(__file__).resolve().parent.parent / "prompts" / "chat-system.txt"
    monkeypatch.setenv("WEBUI_CHAT_SYSTEM_PROMPT", str(real_path))


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def _write_agent(agent_id, api_key="sk-ant-test-key"):
    import src.agents_io as agents_io

    agents_io.write_env(agent_id, {"LLM_API_KEY": api_key, "LLM_PROVIDER": "anthropic"})


def test_chat_embed_requires_auth(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    response = authed_client.get("/chat/info/embed")
    assert response.status_code == 401


def test_chat_embed_authed_returns_chromeless_partial(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    response = authed_client.get("/chat/info/embed", auth=("admin", "pw"))
    assert response.status_code == 200
    assert "<h1>Vizpatch" not in response.text
    assert "/static/chat.js" in response.text
    assert "data-agent-id=\"info\"" in response.text


def test_chat_send_streams_sse(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    mocker.patch(
        "src.main.chat.stream_chat",
        return_value=iter(["Hallo ", "Welt"]),
    )
    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Hi"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "data: Hallo " in response.text
    assert "data: Welt" in response.text
    assert "event: done" in response.text


def test_chat_send_injects_context_md_into_system_prompt(authed_client, mocker, tmp_path, monkeypatch):
    """CHAT-02/CHAT-03 (Plan 07-02): build_system_prompt wird NICHT gemockt —
    nur stream_chat. Prüft, dass das echte prompt-Argument an stream_chat
    sowohl den wörtlichen context.md-Inhalt als auch die User-Message enthält."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    import src.agents_io as agents_io

    agents_io.write_context_md_atomic(
        "info", "## About\nWir sind die Tankstelle Leonberg, 24h geöffnet."
    )

    mock_stream = mocker.patch(
        "src.main.chat.stream_chat",
        return_value=iter(["Antwort"]),
    )
    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Was steht in meiner context.md?"},
    )
    assert response.status_code == 200

    sent_prompt = mock_stream.call_args.kwargs["prompt"]
    assert "Wir sind die Tankstelle Leonberg, 24h geöffnet." in sent_prompt
    assert "Was steht in meiner context.md?" in sent_prompt


def test_chat_send_unknown_agent_returns_400_config_error(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    # "ghost" ist ein gültiger Slug, aber kein angelegter Agent -> kein API-Key -> ChatConfigError.
    response = authed_client.post(
        "/chat/ghost/send",
        auth=("admin", "pw"),
        data={"message": "Hi"},
    )
    assert response.status_code == 400


def test_chat_embed_unknown_agent_returns_404(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.get("/chat/ghost/embed", auth=("admin", "pw"))
    assert response.status_code == 404


def test_chat_send_invalid_agent_id_returns_400(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.post(
        "/chat/../evil/send",
        auth=("admin", "pw"),
        data={"message": "Hi"},
    )
    assert response.status_code in (400, 404)


def test_chat_embed_invalid_agent_id_returns_404(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.get("/chat/../evil/embed", auth=("admin", "pw"))
    assert response.status_code == 404


# --- Rate-Limit + max-tokens + mail_context (Plan 07-03, CHAT-04, D-60/D-65) --------


def test_chat_send_rate_limited_after_configured_limit(authed_client, mocker, tmp_path, monkeypatch):
    """T-07-08: CHAT_RATE_LIMIT_PER_MIN (hier auf 2 gesetzt) greift — der
    3. Request in derselben Minute bekommt 429."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    monkeypatch.setenv("CHAT_RATE_LIMIT_PER_MIN", "2")
    mocker.patch("src.main.chat.stream_chat", return_value=iter(["Hallo"]))

    for _ in range(2):
        r = authed_client.post("/chat/info/send", auth=("admin", "pw"), data={"message": "Hi"})
        assert r.status_code == 200

    blocked = authed_client.post("/chat/info/send", auth=("admin", "pw"), data={"message": "Hi"})
    assert blocked.status_code == 429


def test_chat_send_max_tokens_passed_to_stream_chat(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    monkeypatch.setenv("CHAT_MAX_TOKENS", "777")
    mock_stream = mocker.patch("src.main.chat.stream_chat", return_value=iter(["Antwort"]))

    response = authed_client.post("/chat/info/send", auth=("admin", "pw"), data={"message": "Hi"})

    assert response.status_code == 200
    assert mock_stream.call_args.kwargs["max_tokens"] == 777


def test_chat_send_with_mail_context_reaches_build_chat_prompt(authed_client, mocker, tmp_path, monkeypatch):
    """D-65: mail_context (JSON-String im FormData) landet im prompt-Argument
    von stream_chat — build_chat_prompt wird NICHT gemockt (echter Fluss)."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    import json as _json

    mock_stream = mocker.patch("src.main.chat.stream_chat", return_value=iter(["Antwort"]))
    mail_context = {"subject": "Öffnungszeiten?", "sender": "kunde@example.com", "body": "Wann offen?"}
    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Bitte beantworten", "mail_context": _json.dumps(mail_context)},
    )

    assert response.status_code == 200
    sent_prompt = mock_stream.call_args.kwargs["prompt"]
    assert "Öffnungszeiten?" in sent_prompt
    assert "kunde@example.com" in sent_prompt
    assert "DATEN, keine Anweisung" in sent_prompt


def test_chat_send_without_mail_context_still_works_backward_compat(authed_client, mocker, tmp_path, monkeypatch):
    """D-65: /send ohne mail_context funktioniert unveraendert (Rueckwaertskompat)."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    mocker.patch("src.main.chat.stream_chat", return_value=iter(["Antwort"]))

    response = authed_client.post("/chat/info/send", auth=("admin", "pw"), data={"message": "Hi"})

    assert response.status_code == 200


def test_chat_send_with_history_reaches_build_chat_prompt(authed_client, mocker, tmp_path, monkeypatch):
    """D-58: history (JSON-String der Turns) landet im prompt-Argument von
    stream_chat — echter Fluss durch build_chat_prompt (kein Mock dort)."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    import json as _json

    mock_stream = mocker.patch("src.main.chat.stream_chat", return_value=iter(["Antwort"]))
    history = [
        {"role": "user", "content": "Erste Frage vom Betreiber"},
        {"role": "assistant", "content": "Erste Antwort vom Assistenten"},
    ]
    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Zweite Frage", "history": _json.dumps(history)},
    )

    assert response.status_code == 200
    sent_prompt = mock_stream.call_args.kwargs["prompt"]
    assert "Erste Frage vom Betreiber" in sent_prompt
    assert "Erste Antwort vom Assistenten" in sent_prompt


def test_chat_send_malformed_history_json_falls_back_to_empty_no_500(authed_client, mocker, tmp_path, monkeypatch):
    """T-07-09: kaputtes JSON im history-Feld darf niemals einen 500 ausloesen."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    mocker.patch("src.main.chat.stream_chat", return_value=iter(["Antwort"]))

    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Hi", "history": "{not-valid-json"},
    )

    assert response.status_code == 200


def test_chat_send_malformed_mail_context_json_falls_back_to_none_no_500(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    mocker.patch("src.main.chat.stream_chat", return_value=iter(["Antwort"]))

    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Hi", "mail_context": "[not-an-object]"},
    )

    assert response.status_code == 200


def test_chat_send_history_with_invalid_entries_drops_them_no_500(authed_client, mocker, tmp_path, monkeypatch):
    """T-07-09: history-Struktur wird validiert — ungueltige Einträge (fehlendes
    role/content, falscher Typ) werden verworfen statt einen 500 auszuloesen."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    import json as _json

    mocker.patch("src.main.chat.stream_chat", return_value=iter(["Antwort"]))
    history = [
        {"role": "user", "content": "Gueltiger Turn"},
        {"role": "user"},  # fehlendes content
        "not-a-dict",
        {"role": "assistant", "content": 123},  # falscher Typ
    ]
    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Hi", "history": _json.dumps(history)},
    )

    assert response.status_code == 200


# --- Kein-Auto-Send-Guard (D-63, T-07-10): struktureller Nachweis ------------------


def test_chat_py_source_has_no_mail_write_or_send_path():
    """Struktureller Guard: chat.py darf KEIN Mail-Schreib-/Sende-Modul
    importieren oder referenzieren — der Chat ist rein lesend/beratend (D-63).
    Prueft nur Code-Zeilen (Kommentare/Docstrings sind toleriert, da sie den
    Kein-Auto-Send-Hinweis selbst im Prosatext erwaehnen, T-07-10).

    `.append(`/`smtp` werden NICHT als blinde Substrings geprueft — chat.py
    nutzt legitim Python-`list.append()` (z. B. `parts.append(...)` beim
    Prompt-Bau). Stattdessen werden konkrete Mail-API-Aufrufmuster geprueft
    (IMAP-APPEND-Aufrufe auf einem Mailbox-/IMAP-Objekt, SMTP-Sendevorgaenge)."""
    from pathlib import Path

    chat_source = Path(__file__).resolve().parent.parent / "src" / "chat.py"
    text = chat_source.read_text(encoding="utf-8")

    forbidden_imports = ("draft", "imap_client", "smtplib", "imap_tools", "MailBox")
    forbidden_call_patterns = (
        "mailbox.append(",
        "imap_client.",
        ".append_message(",
        "smtplib.smtp(",
        ".sendmail(",
        "smtp.send",
    )

    code_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
            continue
        code_lines.append(stripped)

    for stripped in code_lines:
        if stripped.startswith("from . import") or stripped.startswith("import ") or stripped.startswith("from "):
            for forbidden in forbidden_imports:
                assert forbidden not in stripped, f"chat.py importiert verbotenes Mail-Modul: {stripped}"
        lowered = stripped.lower()
        for forbidden in forbidden_call_patterns:
            assert forbidden not in lowered, f"chat.py enthaelt verbotenen Mail-Send-Aufruf: {stripped}"
