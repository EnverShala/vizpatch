"""Tests für die Outlook-Add-in-Taskpane-Serving-Route (Phase 8, Plan 08-01, OUT-02).

Deckt ab:
(a) GET /addin/taskpane.html ohne Passwort ueberhaupt -> 403 (require_setup);
    mit Passwort aber ohne Session -> 200 (Session-Gate-Ausnahme, T-jrq-06)
(b) mit Session -> 200, Dropdown mit angelegten Agenten + iframe auf /chat/{id}/embed
(c) leere Agentenliste -> Hinweistext statt iframe, kein 500
(d) No-external-resource-Wächter analog Phase 7 (`_find_external_refs`-Muster):
    die einzige externe URL des Taskpane-Bodys ist exakt die Office.js-CDN-URL.
"""
from __future__ import annotations

import re


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def _write_agent(agent_id, api_key="sk-ant-test-key"):
    import src.agents_io as agents_io

    agents_io.write_env(agent_id, {"LLM_API_KEY": api_key, "LLM_PROVIDER": "anthropic"})


def _find_external_refs(text: str) -> list[str]:
    """Identisches Muster wie test_endpoints_chat.py::_find_external_refs —
    sammelt src=/href=/url(...)-Referenzen und filtert auf externe Ziele
    (http://, https:// oder protokoll-relativ //)."""
    refs: list[str] = []
    for match in re.finditer(r'(?:src|href)\s*=\s*["\']([^"\']+)["\']', text, re.IGNORECASE):
        refs.append(match.group(1))
    for match in re.finditer(r'url\(\s*["\']?([^"\')]+)', text, re.IGNORECASE):
        refs.append(match.group(1))
    return [r for r in refs if r.startswith("http://") or r.startswith("https://") or r.startswith("//")]


def test_addin_taskpane_reachable_without_session_when_password_set(pw_set_client, tmp_path, monkeypatch):
    """260722-jrq (T-jrq-06): /addin/taskpane.html ist Session-Gate-Ausnahme —
    mit gesetztem Passwort (aber OHNE Session) weiterhin erreichbar (200)."""
    _setup_env(tmp_path, monkeypatch)
    response = pw_set_client.get("/addin/taskpane.html")
    assert response.status_code == 200


def test_addin_taskpane_blocked_without_password_at_all(client, tmp_path, monkeypatch):
    """Ohne jegliches WEBUI_PASSWORD greift require_setup als Rest-Schutz (403)."""
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "does-not-exist.env"))
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    response = client.get("/addin/taskpane.html")
    assert response.status_code == 403


def test_addin_taskpane_authed_returns_dropdown_and_iframe(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    _write_agent("zweitagent")
    response = authed_client.get("/addin/taskpane.html", auth=("admin", "pw"))
    assert response.status_code == 200
    body = response.text
    assert 'id="addin-agent-select"' in body
    assert 'id="addin-chat-frame"' in body
    assert '<option value="info"' in body
    assert '<option value="zweitagent"' in body
    # list_agent_ids() ist sortiert -> "info" kommt vor "zweitagent" -> initial_agent="info"
    assert re.search(r'src="/chat/info/embed"', body)


def test_addin_taskpane_no_agents_renders_hint_no_iframe(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.get("/addin/taskpane.html", auth=("admin", "pw"))
    assert response.status_code == 200
    body = response.text
    assert 'id="addin-chat-frame"' not in body
    assert "Kein Agent konfiguriert" in body


def test_addin_taskpane_only_external_resource_is_office_js(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _write_agent("info")
    response = authed_client.get("/addin/taskpane.html", auth=("admin", "pw"))
    assert response.status_code == 200
    refs = _find_external_refs(response.text)
    assert refs == ["https://appsforoffice.microsoft.com/lib/1/hosted/office.js"]


def test_addin_taskpane_no_agents_still_no_external_ref_besides_office_js(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.get("/addin/taskpane.html", auth=("admin", "pw"))
    assert response.status_code == 200
    refs = _find_external_refs(response.text)
    assert refs == ["https://appsforoffice.microsoft.com/lib/1/hosted/office.js"]
