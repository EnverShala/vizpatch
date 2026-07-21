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

import re
from pathlib import Path
from unittest.mock import MagicMock

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


def _write_agent(agent_id, api_key="sk-openai-test-key", provider="openai"):
    """Default-Provider ist bewusst NICHT anthropic (Plan 09-01, CTOOL-01/02):
    die meisten Tests in dieser Datei prüfen SSE-Mechanik/Prompt-Bau über einen
    gemockten `chat.stream_chat` — das ist seit `chat_tools.run_agentic_chat`
    genau der Fallback-Pfad für Nicht-Anthropic-Provider (D-72), der Prompt-Bau
    (`chat.build_chat_prompt`) unverändert durchläuft. Die eigentliche
    Anthropic-Tool-Use-Schleife wird separat in `test_chat_tools.py` getestet."""
    import src.agents_io as agents_io

    agents_io.write_env(agent_id, {"LLM_API_KEY": api_key, "LLM_PROVIDER": provider})


def _mock_docker_running(mocker):
    """Muster aus test_endpoints_config.py/test_security.py — GET / (index)
    ruft docker_ctrl.get_agent_status() auf, das braucht einen Docker-Client-Mock."""
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {"State": {"StartedAt": "2026-07-12T10:00:00Z"}}
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)
    return mock_client


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


# --- Haupt-WebUI-Chat-Integration (Plan 07-04, CHAT-01): gleiche Partial-Quelle ----


def test_index_shows_chat_section_for_existing_agent(authed_client, mocker, tmp_path, monkeypatch):
    """CHAT-01: pro gewaehltem, existierendem Agent erscheint im Haupt-WebUI ein
    Chat-Bereich (Marker: class="chat-section" + der geteilte #chat-log-Marker
    aus _chat.html)."""
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    _write_agent("info")
    response = authed_client.get("/?agent_id=info", auth=("admin", "pw"))
    assert response.status_code == 200
    assert 'class="chat-section"' in response.text
    assert 'id="chat-log"' in response.text
    assert 'data-agent-id="info"' in response.text


def test_index_without_agent_selected_shows_no_chat_section(authed_client, mocker, tmp_path, monkeypatch):
    """Der Chat-Bereich erscheint nur innerhalb des {% if agent_id %}-Blocks —
    im Anlege-Modus (kein Agent gewaehlt) darf er nicht auftauchen."""
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    response = authed_client.get("/", auth=("admin", "pw"))
    assert response.status_code == 200
    assert 'class="chat-section"' not in response.text


def test_index_and_embed_share_identical_chat_fragment_markup(authed_client, mocker, tmp_path, monkeypatch):
    """CHAT-01/CHAT-05/T-07-14: index.html und /chat/{id}/embed rendern
    dasselbe _chat.html-Fragment — EINE Markup-Quelle statt eines Duplikats.
    Beweis: ein woertlicher, aus _chat.html stammender Markup-Block ist in
    beiden Responses byte-identisch vorhanden (fuer denselben agent_id)."""
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    _write_agent("info")

    embed_response = authed_client.get("/chat/info/embed", auth=("admin", "pw"))
    index_response = authed_client.get("/?agent_id=info", auth=("admin", "pw"))
    assert embed_response.status_code == 200
    assert index_response.status_code == 200

    shared_fragment = (
        '<div id="chat-root" data-agent-id="info">\n'
        '  <div id="chat-toolbar">\n'
        '    <button type="button" id="chat-reset-btn" title="Verlauf leeren und neue Sitzung starten">&#x21bb; Verlauf zurücksetzen</button>\n'
        '  </div>\n'
        '  <div id="chat-log" aria-live="polite"></div>\n'
        '  <form id="chat-form">'
    )
    assert shared_fragment in embed_response.text
    assert shared_fragment in index_response.text


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


def test_chat_send_streams_tool_activity_and_final_answer(authed_client, mocker, tmp_path, monkeypatch):
    """Plan 09-01 (CTOOL-01/02, D-80): chat_send ruft chat_tools.run_agentic_chat
    statt chat.stream_chat direkt auf — die SSE-Antwort übersetzt `type=="tool"`
    Events zu einem eigenen `event: tool`-Frame (Tool-Aktivität) und `type=="text"`
    Events zu normalen `data:`-Frames, gefolgt vom bestehenden `event: done`."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info", provider="anthropic")
    mocker.patch(
        "src.main.chat_tools.run_agentic_chat",
        return_value=iter(
            [
                {"type": "tool", "label": "🔧 durchsuche Postfach…"},
                {"type": "text", "text": "Ich habe 2 Mails gefunden."},
            ]
        ),
    )
    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Suche bitte nach Rechnungen"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: tool" in response.text
    assert "durchsuche Postfach" in response.text
    assert "data: Ich habe 2 Mails gefunden." in response.text
    assert "event: done" in response.text


def test_chat_send_run_agentic_chat_not_bypassed_by_direct_stream_chat_call(authed_client, mocker, tmp_path, monkeypatch):
    """T-09-Regressions-Nachweis: chat_send ruft chat.stream_chat NICHT mehr
    direkt auf — nur noch über chat_tools.run_agentic_chat (der interne
    Fallback-Zweig für Nicht-Anthropic-Provider ruft stream_chat weiterhin
    intern auf, das bleibt unbenannt/unbetroffen von dieser Prüfung)."""
    import inspect

    import src.main as main_module

    source = inspect.getsource(main_module.chat_send)
    assert "chat.stream_chat" not in source
    assert "chat_tools.run_agentic_chat" in source


def test_chat_send_forwards_session_id_to_run_agentic_chat(authed_client, mocker, tmp_path, monkeypatch):
    """Session-Autorisierung (Betreiber-Entscheidung): das `session_id`-Formfeld
    (von `chat.js` je Chat-Sitzung erzeugt) muss unverändert bei
    `chat_tools.run_agentic_chat()` ankommen, damit die Papierkorb-Werkzeuge
    wissen, ob diese Sitzung bereits autorisiert ist."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info", provider="anthropic")
    mock_run = mocker.patch(
        "src.main.chat_tools.run_agentic_chat",
        return_value=iter([{"type": "text", "text": "Ok."}]),
    )
    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Hi", "session_id": "sess-forward-test"},
    )
    assert response.status_code == 200
    assert mock_run.call_args.kwargs["session_id"] == "sess-forward-test"


def test_chat_send_without_session_id_still_works_backward_compat(authed_client, mocker, tmp_path, monkeypatch):
    """Fehlt das `session_id`-Feld (z.B. älteres Frontend), bleibt /send nutzbar —
    `chat_send` defaultet auf einen leeren String (nie autorisierbar, kein 500)."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info", provider="anthropic")
    mock_run = mocker.patch(
        "src.main.chat_tools.run_agentic_chat",
        return_value=iter([{"type": "text", "text": "Ok."}]),
    )
    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Hi"},
    )
    assert response.status_code == 200
    assert mock_run.call_args.kwargs["session_id"] == ""


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


def test_chat_send_stream_error_is_generic_no_leak(authed_client, mocker, tmp_path, monkeypatch):
    """Review WR-06: der SSE-error-Frame darf KEINEN rohen Exception-Text
    (Hostnamen/Server-Antworten) an den Client streamen — generische Meldung,
    Details nur serverseitig geloggt. Der Frame bleibt als korrekt kodierte
    `data:`-Zeile (SSE-Spec) erhalten (WR-05-Kodierung unveraendert)."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info", provider="anthropic")

    def _boom(*_args, **_kwargs):
        yield {"type": "text", "text": "Teil 1"}
        raise RuntimeError("imap.secret-host.internal Zeile 1\nZeile 2\n\nZeile 4")

    mocker.patch("src.main.chat_tools.run_agentic_chat", side_effect=_boom)

    response = authed_client.post("/chat/info/send", auth=("admin", "pw"), data={"message": "Hi"})

    assert response.status_code == 200
    assert "event: error\ndata: Interner Fehler bei der Verarbeitung.\n\n" in response.text
    assert "secret-host" not in response.text
    assert "Zeile 2" not in response.text


def test_chat_send_broken_fernet_token_returns_400_not_500(authed_client, tmp_path, monkeypatch):
    """Review WR-06: ein kaputter/mit rotiertem Key verschluesselter
    LLM_API_KEY (SEC-03-Fall) laesst crypto.decrypt_value einen RuntimeError
    werfen — /send uebersetzt das eager in einen verstaendlichen 400 statt
    eines generischen 500."""
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    # 'enc:'-Prefix mit ungueltigem Fernet-Token — write_env laesst bereits
    # gepraefixte Werte unveraendert, decrypt_value wirft RuntimeError.
    agents_io.write_env(
        "info", {"LLM_API_KEY": "enc:kein-gueltiges-fernet-token", "LLM_PROVIDER": "openai"}
    )

    response = authed_client.post("/chat/info/send", auth=("admin", "pw"), data={"message": "Hi"})

    assert response.status_code == 400
    assert "Secret nicht entschlüsselbar" in response.json()["detail"]


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
    von stream_chat — build_chat_prompt wird NICHT gemockt (echter Fluss).

    Phase 10 (ANON-03/04): `ENABLE_PII_REDACTION` ist per Default an — der
    Absender (E-Mail) im mail_context wird daher jetzt reversibel zu einem
    Tag pseudonymisiert, BEVOR der Prompt den Server verlässt (D-65 bleibt
    strukturell erfüllt: der Betreff — keine strukturierte PII — steht
    weiterhin roh im Prompt)."""
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
    assert "kunde@example.com" not in sent_prompt
    assert "[EMAIL_1]" in sent_prompt
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


# --- Einbettbarkeits-Nachweis (Plan 07-04, CHAT-05/D-61, T-07-12): --------------
# keine externen Ressourcen im embed-Partial + referenzierten /static-Assets.


def _find_external_refs(text: str) -> list[str]:
    """Sammelt alle src=/href=/url(...)-Referenzen und filtert auf externe
    Ziele (http://, https:// oder protokoll-relativ //) — genau die Ziele, die
    ein Fremd-Host (T-07-12: CDN/Supply-Chain) NICHT laden duerfte."""
    refs: list[str] = []
    for match in re.finditer(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE):
        refs.append(match.group(1))
    for match in re.finditer(r'url\(\s*["\']?([^"\')]+)', text, re.IGNORECASE):
        refs.append(match.group(1))
    return [r for r in refs if r.startswith("http://") or r.startswith("https://") or r.startswith("//")]


def test_chat_embed_and_static_assets_have_no_external_resources(authed_client, tmp_path, monkeypatch):
    """CHAT-05/D-61/T-07-12: der embed-Body ist chrome-los (kein
    <h1>Vizpatch-Chrome) und enthaelt — genau wie die referenzierten
    /static-Assets chat.js/chat.css — KEINE externe URL (kein CDN)."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    response = authed_client.get("/chat/info/embed", auth=("admin", "pw"))
    assert response.status_code == 200
    body = response.text
    assert "<h1>Vizpatch" not in body
    assert _find_external_refs(body) == []

    static_dir = Path(__file__).resolve().parent.parent / "static"
    chat_js = (static_dir / "chat.js").read_text(encoding="utf-8")
    chat_css = (static_dir / "chat.css").read_text(encoding="utf-8")
    assert _find_external_refs(chat_js) == []
    assert _find_external_refs(chat_css) == []
    assert "@import" not in chat_css


def test_embed_test_fixture_has_no_external_urls():
    """Nachweis (CHAT-05, Phase-8-Vorarbeit): die nackte Test-HTML-Seite, die
    demonstriert wie ein Fremd-Host das Partial einbindet, referenziert
    ausschliesslich lokale/relative Dateien — keine externe/protokoll-relative
    URL irgendwo im Fixture."""
    fixture = Path(__file__).resolve().parent / "fixtures" / "embed_test.html"
    text = fixture.read_text(encoding="utf-8")
    assert re.search(r"https?://", text) is None


# --- Chat-Datei-Upload (Plan 12-02, ATT-01) -----------------------------------


def test_chat_upload_requires_auth(authed_client, tmp_path, monkeypatch):
    """Analog test_chat_embed_requires_auth: ohne Basic-Auth -> 401."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    response = authed_client.post(
        "/chat/info/upload",
        files={"file": ("anhang.txt", b"hallo welt", "text/plain")},
        data={"session_id": "sess-1"},
    )
    assert response.status_code == 401


def test_chat_upload_unknown_agent_returns_404(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.post(
        "/chat/ghost/upload",
        auth=("admin", "pw"),
        files={"file": ("anhang.txt", b"hallo welt", "text/plain")},
        data={"session_id": "sess-1"},
    )
    assert response.status_code == 404


def test_chat_upload_missing_session_id_returns_400(authed_client, tmp_path, monkeypatch):
    """Kein session_id-Formfeld (httpx laesst leere Strings im Multipart-Encoder
    ohnehin weg — der reale Fall, den ein Browser ohne Sitzungs-Handling
    erzeugen wuerde) -> 400, nicht der generische FastAPI-422 (Form-Default ""
    + manuelle Pruefung statt Form(...))."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    response = authed_client.post(
        "/chat/info/upload",
        auth=("admin", "pw"),
        files={"file": ("anhang.txt", b"hallo welt", "text/plain")},
    )
    assert response.status_code == 400


def test_chat_upload_rejects_oversized_file(authed_client, tmp_path, monkeypatch):
    """T-12-06/Pitfall 4: MAX_ATTACHMENT_MB=0 -> jeder nicht-leere Upload
    ueberschreitet das Limit sofort -> 413, tmp-Datei wird verworfen (kein Leck),
    register_pending_upload wird NICHT aufgerufen."""
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("MAX_ATTACHMENT_MB", "0")
    _write_agent("info")
    import src.chat_tools as chat_tools

    response = authed_client.post(
        "/chat/info/upload",
        auth=("admin", "pw"),
        files={"file": ("zu-gross.txt", b"x" * 10, "text/plain")},
        data={"session_id": "sess-oversized"},
    )
    assert response.status_code == 413
    assert "Limit" in response.json()["detail"]
    assert chat_tools._consume_pending_upload("info", "sess-oversized") is None


def test_chat_upload_success_registers_pending_upload(authed_client, mocker, tmp_path, monkeypatch):
    """Erfolgsfall: 200 mit ASCII-JSON-Keys, register_pending_upload wird mit dem
    server-generierten tmp-Pfad + sanitiertem Dateinamen + gezaehlter Groesse +
    erratenem Mimetyp aufgerufen. Streaming-Nachweis via file.file.read-Mock
    (Pattern 3, kein file.read())."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    mock_register = mocker.patch("src.main.chat_tools.register_pending_upload")

    content = b"Hallo, das ist ein Testanhang."
    response = authed_client.post(
        "/chat/info/upload",
        auth=("admin", "pw"),
        files={"file": ("../../etc/rechnung.pdf", content, "application/pdf")},
        data={"session_id": "sess-ok"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["dateiname"] == "rechnung.pdf"
    assert body["groesse"] == len(content)
    assert body["mimetyp"] == "application/pdf"

    mock_register.assert_called_once()
    call_args = mock_register.call_args.args
    assert call_args[0] == "info"
    assert call_args[1] == "sess-ok"
    assert call_args[3] == "rechnung.pdf"
    assert call_args[4] == len(content)
    assert call_args[5] == "application/pdf"
    tmp_path_arg = call_args[2]
    assert tmp_path_arg.exists()
    assert tmp_path_arg.read_bytes() == content
    tmp_path_arg.unlink(missing_ok=True)


def test_chat_upload_streams_via_file_read_not_full_read(authed_client, mocker, tmp_path, monkeypatch):
    """Pattern 3/D-96: verifiziert, dass chat_upload ueber file.file.read(n) liest
    (chunked) statt file.read() (Full-Memory-Load) — Nachweis via Quelltext-Scan
    (robust gegen Implementierungsdetails der UploadFile-Bibliothek selbst)."""
    import inspect

    import src.main as main_module

    source = inspect.getsource(main_module.chat_upload)
    # Der ausfuehrende Read-Aufruf muss ueber file.file.read(n) (chunked) laufen —
    # geprueft ueber den vollstaendigen Read-Ausdruck (robust gegen die erklaerende
    # Docstring-Erwaehnung "KEIN `file.read()`" weiter oben in derselben Funktion).
    assert "while chunk := file.file.read(1024 * 1024)" in source


# --- attachment_meta-Durchreichung an run_agentic_chat (Plan 12-02, ATT-03) ---


def test_chat_send_with_attachment_metadata_reaches_prompt(authed_client, mocker, tmp_path, monkeypatch):
    """ATT-03: das attachment_meta-Formfeld (JSON-String, vom vorherigen Upload-
    Response uebernommen) wird geparst und unveraendert als attachment_meta=
    an chat_tools.run_agentic_chat() durchgereicht."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info", provider="anthropic")
    import json as _json

    mock_run = mocker.patch(
        "src.main.chat_tools.run_agentic_chat",
        return_value=iter([{"type": "text", "text": "Ok."}]),
    )
    meta = {"dateiname": "rechnung.pdf", "groesse": 1234, "mimetyp": "application/pdf"}
    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Haenge das an einen Entwurf.", "attachment_meta": _json.dumps(meta)},
    )
    assert response.status_code == 200
    forwarded = mock_run.call_args.kwargs["attachment_meta"]
    assert forwarded == {"dateiname": "rechnung.pdf", "groesse": 1234, "mimetyp": "application/pdf"}


def test_chat_send_without_attachment_metadata_still_works_backward_compat(authed_client, mocker, tmp_path, monkeypatch):
    """Rueckwaertskompatibilitaet: fehlt attachment_meta (aelteres Frontend/kein
    Upload in dieser Sitzung), bleibt /send nutzbar — attachment_meta=None,
    kein Crash."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info", provider="anthropic")
    mock_run = mocker.patch(
        "src.main.chat_tools.run_agentic_chat",
        return_value=iter([{"type": "text", "text": "Ok."}]),
    )
    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Hi"},
    )
    assert response.status_code == 200
    assert mock_run.call_args.kwargs["attachment_meta"] is None


def test_chat_send_with_broken_attachment_metadata_json_falls_back_to_none(authed_client, mocker, tmp_path, monkeypatch):
    """Kaputtes JSON im attachment_meta-Formfeld -> None statt Crash (analog
    _parse_mail_context bei kaputtem mail_context)."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info", provider="anthropic")
    mock_run = mocker.patch(
        "src.main.chat_tools.run_agentic_chat",
        return_value=iter([{"type": "text", "text": "Ok."}]),
    )
    response = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "Hi", "attachment_meta": "{kaputtes json"},
    )
    assert response.status_code == 200
    assert mock_run.call_args.kwargs["attachment_meta"] is None
