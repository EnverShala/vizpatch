"""POST /test-connection: Live-Verbindungstest für IMAP bzw. LLM OHNE zu
speichern (Betreiber-Wunsch: „Verbindung testen"-Button im Agent-Formular).

Nutzt dieselbe autouse-Stub-Fixture wie die /save-Tests: `check_imap`/`check_llm`
sind standardmäßig No-Ops (= Prüfung besteht). Fehlerfälle patchen die jeweilige
Prüffunktion gezielt auf „wirft" (überschreibt den Stub — letzte Zuweisung
gewinnt). Kernzusicherung gegenüber /save: es wird NICHTS persistiert.
"""
from __future__ import annotations


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))


def test_imap_test_ok(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    r = authed_client.post(
        "/test-connection",
        data={"target": "imap", "imap_user": "u@example.com", "imap_password": "secret"},
    )
    assert r.status_code == 200
    assert "erfolgreich" in r.text


def test_imap_test_fail_returns_400(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.validate_conn as validate_conn

    monkeypatch.setattr(
        validate_conn,
        "check_imap",
        lambda *a, **k: (_ for _ in ()).throw(
            validate_conn.ConnectionCheckError("IMAP-Anmeldung fehlgeschlagen — Benutzer/Passwort prüfen.")
        ),
    )
    r = authed_client.post(
        "/test-connection",
        data={"target": "imap", "imap_user": "u@example.com", "imap_password": "wrong"},
    )
    assert r.status_code == 400
    assert "IMAP-Anmeldung fehlgeschlagen" in r.text


def test_llm_test_ok_detects_provider(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    r = authed_client.post(
        "/test-connection",
        data={"target": "llm", "llm_api_key": "sk-ant-testkey"},
    )
    assert r.status_code == 200
    assert "Anthropic" in r.text  # aus PROVIDER_LABELS['anthropic']


def test_llm_test_fail_returns_400(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.validate_conn as validate_conn

    monkeypatch.setattr(
        validate_conn,
        "check_llm",
        lambda *a, **k: (_ for _ in ()).throw(
            validate_conn.ConnectionCheckError(
                "LLM-Zugang fehlgeschlagen — Verbindung zu api.anthropic.com fehlgeschlagen."
            )
        ),
    )
    r = authed_client.post(
        "/test-connection",
        data={"target": "llm", "llm_api_key": "sk-ant-testkey"},
    )
    assert r.status_code == 400
    assert "api.anthropic.com" in r.text


def test_llm_test_unrecognized_key_400(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    r = authed_client.post(
        "/test-connection",
        data={"target": "llm", "llm_api_key": "not-a-key"},
    )
    assert r.status_code == 400
    assert "nicht erkannt" in r.text


def test_test_connection_persists_nothing(authed_client, tmp_path, monkeypatch):
    """Gegenüber /save die zentrale Zusicherung: ein Test schreibt NICHTS."""
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
    r = authed_client.post(
        "/test-connection",
        data={
            "target": "imap",
            "agent_id": "info",
            "imap_user": "u@example.com",
            "imap_password": "secret",
        },
    )
    assert r.status_code == 200
    assert (agents_io.read_env_raw("info").get("IMAP_USER") or "") == ""


def test_llm_test_uses_stored_key_when_field_empty(authed_client, tmp_path, monkeypatch):
    """Leeres Key-Feld (Edit-Fall) -> der bereits gespeicherte, entschlüsselte
    Key/Provider wird getestet — genau wie beim Speichern."""
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", {"LLM_PROVIDER": "anthropic", "LLM_API_KEY": "sk-ant-stored"})
    r = authed_client.post(
        "/test-connection",
        data={"target": "llm", "agent_id": "info", "llm_api_key": ""},
    )
    assert r.status_code == 200
    assert "Anthropic" in r.text
