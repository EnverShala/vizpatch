"""Tests für das XML-Add-in-Manifest (Phase 8, Plan 08-02, OUT-01/D-67).

Deckt ab:
(a) GET /addin/manifest.xml ohne Passwort ueberhaupt -> 403 (require_setup);
    mit Passwort aber ohne Session -> 200 (Session-Gate-Ausnahme, T-jrq-06)
(b) mit Session + gültiger ADDIN_BASE_URL -> 200, media_type application/xml,
    wohlgeformt (xml.etree.ElementTree.fromstring), SourceLocation mit der
    eingesetzten Basis-URL, KEIN verbleibendes {ADDIN_BASE_URL}-Platzhalter
(c) genau ReadItem als Permission, KEIN ReadWriteItem/ReadWriteMailbox
(d) ADDIN_BASE_URL mit http:// oder XML-Sonderzeichen -> 400 (T-08-06,
    XML-Injection-Schutz), kein 500, kein kaputtes XML ausgeliefert
"""
from __future__ import annotations

import xml.etree.ElementTree as ET


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))


def test_addin_manifest_reachable_without_session_when_password_set(pw_set_client, tmp_path, monkeypatch):
    """260722-jrq (T-jrq-06): /addin/manifest.xml ist Session-Gate-Ausnahme —
    mit gesetztem Passwort (aber OHNE Session) weiterhin erreichbar (200)."""
    _setup_env(tmp_path, monkeypatch)
    response = pw_set_client.get("/addin/manifest.xml")
    assert response.status_code == 200


def test_addin_manifest_blocked_without_password_at_all(client, tmp_path, monkeypatch):
    """Ohne jegliches WEBUI_PASSWORD greift require_setup als Rest-Schutz (403)."""
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "does-not-exist.env"))
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    response = client.get("/addin/manifest.xml")
    assert response.status_code == 403


def test_addin_manifest_authed_wellformed_and_templated(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("ADDIN_BASE_URL", "https://kunde.example")
    response = authed_client.get("/addin/manifest.xml", auth=("admin", "pw"))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/xml")

    body = response.text
    assert "{ADDIN_BASE_URL}" not in body
    assert "https://kunde.example/addin/taskpane.html" in body

    root = ET.fromstring(body)  # wirft bei kaputtem XML
    assert root is not None


def test_addin_manifest_permission_is_readitem_only(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("ADDIN_BASE_URL", "https://kunde.example")
    response = authed_client.get("/addin/manifest.xml", auth=("admin", "pw"))
    assert response.status_code == 200
    body = response.text
    ns = {"m": "http://schemas.microsoft.com/office/appforoffice/1.1"}
    root = ET.fromstring(body)
    permissions = root.find("m:Permissions", ns)
    assert permissions is not None
    assert permissions.text.strip() == "ReadItem"
    assert "ReadWriteItem" not in body
    assert "ReadWriteMailbox" not in body


def test_addin_manifest_default_base_url_still_wellformed(authed_client, tmp_path, monkeypatch):
    """Ohne ADDIN_BASE_URL greift der https://-Platzhalter-Default — muss
    weiterhin wohlgeformtes XML liefern (kein 500 bei fehlender Konfiguration)."""
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.delenv("ADDIN_BASE_URL", raising=False)
    response = authed_client.get("/addin/manifest.xml", auth=("admin", "pw"))
    assert response.status_code == 200
    ET.fromstring(response.text)


def test_addin_manifest_rejects_http_base_url(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("ADDIN_BASE_URL", "http://kunde.example")
    response = authed_client.get("/addin/manifest.xml", auth=("admin", "pw"))
    assert response.status_code == 400


def test_addin_manifest_rejects_xml_special_chars_in_base_url(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.setenv("ADDIN_BASE_URL", 'https://kunde.example"><Injected>')
    response = authed_client.get("/addin/manifest.xml", auth=("admin", "pw"))
    assert response.status_code == 400
