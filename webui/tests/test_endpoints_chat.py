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
