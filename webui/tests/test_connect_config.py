"""GET /connect-config: Verknüpfungs-Datei für „Mit Outlook verknüpfen".

Liefert eine JSON-Datei zum Download (Backend-URL + Agent-ID + Benutzer +
Origin-Token) — OHNE Passwort (DPAPI-bedingt am Ziel-PC einzugeben).
"""
from __future__ import annotations

import json


def test_connect_config_download(authed_client):
    r = authed_client.get("/connect-config?agent_id=info")
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert "vizpatch-verknuepfung.json" in cd

    data = json.loads(r.text)
    assert data["AgentId"] == "info"
    assert data["Username"] == "admin"
    assert data["BackendUrl"].startswith("http")
    assert data["AddinOriginToken"] == "https://outlook.office.com"
    # KEIN Passwort in der Verknüpfungs-Datei.
    assert "Password" not in data
    assert "PasswordProtected" not in data


def test_connect_config_requires_auth(pw_set_client):
    """Ohne gültige Session -> 401 (kein Download der Verknüpfungs-Datei)."""
    r = pw_set_client.get("/connect-config?agent_id=info", follow_redirects=False)
    assert r.status_code in (401, 303)
