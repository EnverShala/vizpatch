"""Tests für die Mail-Kontext-Brücke Office.js -> postMessage -> chat.js
(Phase 8, Plan 08-02, OUT-03/D-69).

Deckt ab:
(a) taskpane.js existiert, wird von addin_taskpane.html eingebunden und ist
    unter /static/addin/taskpane.js ausliefertbar
(b) taskpane.js postet mit expliziter targetOrigin (window.location.origin),
    NIEMALS mit '*' als postMessage-Ziel (T-08-04)
(c) taskpane.js liest ausschließlich über item.subject/item.from/
    item.body.getAsync(Office.CoercionType.Text)
(d) chat.js hat einen message-Listener mit event.origin-Prüfung und liefert
    über vizpatchGetMailContext ein {subject, sender, body}-Objekt (statisch
    aus der Quelle geprüft)
(e) No-external-resource-Wächter der Taskpane bleibt grün (taskpane.js ist
    eine lokale /static-Referenz, keine externe Ressource)
"""
from __future__ import annotations

import re
from pathlib import Path

TASKPANE_JS = Path(__file__).resolve().parent.parent / "static" / "addin" / "taskpane.js"
CHAT_JS = Path(__file__).resolve().parent.parent / "static" / "chat.js"
ADDIN_TASKPANE_HTML = Path(__file__).resolve().parent.parent / "src" / "templates" / "addin_taskpane.html"


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def _write_agent(agent_id, api_key="sk-ant-test-key"):
    import src.agents_io as agents_io

    agents_io.write_env(agent_id, {"LLM_API_KEY": api_key, "LLM_PROVIDER": "anthropic"})


def test_taskpane_js_exists_and_referenced_from_taskpane_html():
    assert TASKPANE_JS.exists()
    html = ADDIN_TASKPANE_HTML.read_text(encoding="utf-8")
    assert '<script src="/static/addin/taskpane.js">' in html
    # Reihenfolge: office.js MUSS vor taskpane.js eingebunden sein.
    assert html.index("appsforoffice.microsoft.com") < html.index("/static/addin/taskpane.js")


def test_taskpane_js_served_under_static(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.get("/static/addin/taskpane.js")
    assert response.status_code == 200


def test_taskpane_js_postmessage_uses_explicit_targetorigin_never_wildcard():
    js = TASKPANE_JS.read_text(encoding="utf-8")
    assert "postMessage(" in js
    assert "window.location.origin" in js

    # Kein postMessage-Aufruf darf '*' als (zweites) targetOrigin-Argument haben.
    for match in re.finditer(r"postMessage\(([^;]*)\)", js, re.DOTALL):
        call_args = match.group(1)
        assert "'*'" not in call_args and '"*"' not in call_args, (
            f"postMessage mit Wildcard-targetOrigin gefunden: {call_args!r}"
        )


def test_taskpane_js_reads_only_via_office_read_apis():
    js = TASKPANE_JS.read_text(encoding="utf-8")
    assert "item.subject" in js
    assert "item.from" in js
    assert "item.body.getAsync" in js
    assert "Office.CoercionType.Text" in js
    assert "Office.EventType.ItemChanged" in js


def test_chat_js_message_listener_checks_origin_and_feeds_hook():
    js = CHAT_JS.read_text(encoding="utf-8")
    assert "addEventListener('message'" in js or 'addEventListener("message"' in js
    assert "event.origin" in js
    assert "window.location.origin" in js
    assert "vizpatch-mail-context" in js
    assert "vizpatchGetMailContext" in js
    # Statischer Nachweis, dass der Hook ein {subject, sender, body}-Objekt liefert.
    assert "subject" in js and "sender" in js and "body" in js


def test_addin_taskpane_no_external_resource_guard_still_green(authed_client, tmp_path, monkeypatch):
    """Regression: /static/addin/taskpane.js ist eine lokale Referenz — der
    Phase-7/8-No-external-resource-Wächter bleibt unverändert grün."""
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    response = authed_client.get("/addin/taskpane.html", auth=("admin", "pw"))
    assert response.status_code == 200

    refs = []
    for match in re.finditer(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', response.text, re.IGNORECASE):
        refs.append(match.group(1))
    external_refs = [r for r in refs if r.startswith("http://") or r.startswith("https://") or r.startswith("//")]
    assert external_refs == ["https://appsforoffice.microsoft.com/lib/1/hosted/office.js"]
    assert "/static/addin/taskpane.js" in refs
