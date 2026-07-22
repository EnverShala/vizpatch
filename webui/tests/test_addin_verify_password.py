"""Tests für POST /addin/verify-password (Add-in-Einstellungs-Gate, Feature B).

Der Endpoint ist Session-Gate-ausgenommen (/addin/-Präfix), verlangt ein
gesetztes WEBUI_PASSWORD (`require_setup`) und prüft ein frisch eingegebenes
Passwort gegen den bcrypt-Hash. Add-in-Origins (Office/Outlook) sind erlaubt.
"""
from __future__ import annotations

import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))


def _with_password(monkeypatch):
    from src import auth

    monkeypatch.setenv("WEBUI_PASSWORD", auth.hash_password("geheim123"))


def test_verify_correct_password_returns_ok(client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _with_password(monkeypatch)
    r = client.post("/addin/verify-password", data={"password": "geheim123"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_verify_wrong_password_returns_401(client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    _with_password(monkeypatch)
    r = client.post("/addin/verify-password", data={"password": "falsch"})
    assert r.status_code == 401


def test_verify_addin_office_origin_allowed(client, tmp_path, monkeypatch):
    """CSRF: der Office-Origin (nicht same-origin) darf diesen Add-in-Pfad
    ansprechen — kein 403 durch enforce_same_origin."""
    _setup_env(tmp_path, monkeypatch)
    _with_password(monkeypatch)
    r = client.post(
        "/addin/verify-password",
        data={"password": "geheim123"},
        headers={"Origin": "https://outlook.office.com"},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_verify_foreign_origin_still_rejected(client, tmp_path, monkeypatch):
    """Ein fremder (nicht Add-in-)Origin bleibt geblockt (403)."""
    _setup_env(tmp_path, monkeypatch)
    _with_password(monkeypatch)
    r = client.post(
        "/addin/verify-password",
        data={"password": "geheim123"},
        headers={"Origin": "https://evil.example"},
    )
    assert r.status_code == 403


def test_verify_without_password_set_is_forbidden(client, tmp_path, monkeypatch):
    """Ohne gesetztes WEBUI_PASSWORD greift require_setup -> 403 (nichts zu prüfen)."""
    _setup_env(tmp_path, monkeypatch)
    monkeypatch.delenv("WEBUI_PASSWORD", raising=False)
    r = client.post("/addin/verify-password", data={"password": "egal"})
    assert r.status_code == 403
