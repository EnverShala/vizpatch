"""Integrationstests: POST /save blockiert bei fehlgeschlagener Verbindungs-
prüfung (hart, kein Persistieren) und speichert bei erfolgreicher Prüfung.

Diese Tests tragen KEINEN `real_conn_check`-Marker: die conftest-Stub-Fixture
macht `check_imap`/`check_llm` standardmäßig zu No-Ops (= Prüfung besteht). Für
die Block-Fälle wird die jeweilige Prüffunktion im Test gezielt auf „wirft" neu
gepatcht (überschreibt den autouse-Stub — letzte Zuweisung gewinnt).
"""
from __future__ import annotations

import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))


_HTMX = {"HX-Request": "true"}


def test_save_blocks_when_imap_check_fails(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    import src.validate_conn as validate_conn

    # Bestehender Agent hat bereits einen erkannten Provider (Edit-Fall) — sonst
    # greift die vorgelagerte „gültiger API-Key nötig"-Prüfung vor der IMAP-Probe.
    agents_io.write_env(
        "info", {"AGENT_ENABLED": "false", "LLM_PROVIDER": "anthropic", "LLM_API_KEY": "sk-ant-x"}
    )
    monkeypatch.setattr(
        validate_conn,
        "check_imap",
        lambda *a, **k: (_ for _ in ()).throw(
            validate_conn.ConnectionCheckError("IMAP-Anmeldung fehlgeschlagen — Benutzer/Passwort prüfen.")
        ),
    )

    r = authed_client.post(
        "/save",
        headers=_HTMX,
        data={
            "agent_id": "info",
            "imap_user": "u@example.com",
            "imap_password": "wrong",
            "privacy_consent": "on",
        },
    )
    assert r.status_code == 200
    assert "Nicht gespeichert" in r.text
    assert "IMAP-Anmeldung fehlgeschlagen" in r.text
    # Nichts persistiert: kein IMAP_USER geschrieben.
    assert (agents_io.read_env_raw("info").get("IMAP_USER") or "") == ""


def test_save_blocks_when_llm_check_fails(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    import src.validate_conn as validate_conn

    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
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
        "/save",
        headers=_HTMX,
        data={
            "agent_id": "info",
            "llm_api_key": "sk-ant-testkey",
            "privacy_consent": "on",
        },
    )
    assert r.status_code == 200
    assert "Nicht gespeichert" in r.text
    assert "api.anthropic.com" in r.text
    # LLM-Key NICHT persistiert.
    assert (agents_io.read_env_raw("info").get("LLM_API_KEY") or "") == ""


def test_save_succeeds_when_checks_pass(authed_client, tmp_path, monkeypatch):
    """Autouse-Stub lässt beide Prüfungen bestehen -> Creds werden persistiert."""
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", {"AGENT_ENABLED": "false"})

    r = authed_client.post(
        "/save",
        headers=_HTMX,
        data={
            "agent_id": "info",
            "imap_user": "u@example.com",
            "imap_password": "secret",
            "llm_api_key": "sk-ant-testkey",
            "privacy_consent": "on",
        },
    )
    assert r.status_code == 200
    assert "Nicht gespeichert" not in r.text
    env = agents_io.read_env_raw("info")
    assert env.get("IMAP_USER") == "u@example.com"
    assert env.get("LLM_PROVIDER") == "anthropic"
