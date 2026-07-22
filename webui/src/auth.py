import logging
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Optional

import bcrypt
from dotenv import dotenv_values
from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# Session-Login (D-01/D-02, 260722-jrq): fester Benutzername, kein WEBUI_USER
# mehr. Einziges Credential ist WEBUI_PASSWORD (bcrypt-Hash).
ADMIN_USER = "admin"
SESSION_COOKIE_NAME = "vizpatch_session"

# Prozess-lokaler Session-Store — analog `chat_tools._authorized_move_sessions`.
# Container-Neustart leert den Store (gewollt = "Login pro Sitzung").
_sessions: set[str] = set()
_sessions_lock = threading.Lock()

_LOGIN_MAX_FAILURES = 5
_LOGIN_WINDOW_SEC = 900
_LOGIN_LOCKOUT_SEC = 900

_login_lock = threading.Lock()
_login_failures: dict[str, list[float]] = {}
_login_lockouts: dict[str, float] = {}


def _trusted_proxy() -> str:
    return (os.getenv("TRUSTED_PROXY") or "").strip()


def client_ip(request: Optional[Request]) -> str:
    """WR-05: ermittelt die effektive Client-IP fuer Login-Lockout UND Rate-Limit.
    `X-Forwarded-For` wird NUR ausgewertet, wenn `TRUSTED_PROXY` (neue Env, Default
    leer) gesetzt ist UND der direkte TCP-Peer GENAU dieser Proxy ist — dann gilt
    der erste XFF-Eintrag (die urspruengliche Client-IP) als Client. Ohne
    `TRUSTED_PROXY` oder bei abweichendem Peer bleibt es unveraendert bei
    `request.client.host`. XFF wird NIE blind vertraut (sonst koennte ein Client
    seine IP spoofen und den Lockout/das Limit umgehen)."""
    if request is None or request.client is None:
        return "unknown"
    peer = request.client.host or "unknown"
    trusted = _trusted_proxy()
    if trusted and peer == trusted:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            first = xff.split(",")[0].strip()
            if first:
                return first
    return peer


def _client_ip(request: Optional[Request]) -> str:
    # Beibehaltener interner Name (Login-Lockout) — delegiert an die
    # Trusted-Proxy-bewusste Logik (WR-05).
    return client_ip(request)


def _check_login_lockout(request: Optional[Request]) -> None:
    ip = _client_ip(request)
    now = time.monotonic()
    with _login_lock:
        until = _login_lockouts.get(ip)
        if until is not None:
            if until > now:
                remaining = int(until - now)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed logins, retry in {remaining}s",
                    headers={"Retry-After": str(remaining)},
                )
            _login_lockouts.pop(ip, None)


def _record_login_failure(request: Optional[Request]) -> None:
    ip = _client_ip(request)
    now = time.monotonic()
    with _login_lock:
        window = _login_failures.setdefault(ip, [])
        window[:] = [t for t in window if now - t < _LOGIN_WINDOW_SEC]
        window.append(now)
        if len(window) >= _LOGIN_MAX_FAILURES:
            _login_lockouts[ip] = now + _LOGIN_LOCKOUT_SEC
            window.clear()
            logger.warning("login_lockout ip=%s duration=%ds", ip, _LOGIN_LOCKOUT_SEC)


def _reset_login_tracking() -> None:
    with _login_lock:
        _login_failures.clear()
        _login_lockouts.clear()


# --- Session-Store (D-01, 260722-jrq) ---


def create_session() -> str:
    """Legt eine neue Session an (opaker 32-Byte-Token) und gibt sie zurueck."""
    token = secrets.token_urlsafe(32)
    with _sessions_lock:
        _sessions.add(token)
    return token


def destroy_session(token: Optional[str]) -> None:
    """Verwirft eine Session. `None`/unbekannte Token werden toleriert."""
    if not token:
        return
    with _sessions_lock:
        _sessions.discard(token)


def session_valid(token: Optional[str]) -> bool:
    """Prueft, ob `token` eine aktuell gueltige Session referenziert."""
    if not token:
        return False
    with _sessions_lock:
        return token in _sessions


def set_session_cookie(response, token: str) -> None:
    """Setzt den Session-Cookie. KEIN `max_age`/`expires` (echter Session-Cookie,
    endet beim Browser-Schliessen). Kein `secure`-Zwang (LAN-http-Betrieb, D-01)."""
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


# --- Passwort (WEBUI_PASSWORD, bcrypt) ---


def _read_password() -> str:
    env_path = Path(os.getenv("WEBUI_ENV_PATH", "/config/.env"))
    values = dotenv_values(env_path) if env_path.exists() else {}
    return (values.get("WEBUI_PASSWORD") or os.environ.get("WEBUI_PASSWORD") or "").strip()


def password_is_set() -> bool:
    return bool(_read_password())


def hash_password(plaintext: str) -> str:
    return bcrypt.hashpw(plaintext.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _verify_password(candidate: str, stored: str) -> bool:
    if stored.startswith("$2a$") or stored.startswith("$2b$") or stored.startswith("$2y$"):
        try:
            return bcrypt.checkpw(candidate.encode("utf-8"), stored.encode("ascii"))
        except (ValueError, TypeError):
            return False
    # Legacy-Klartext (Migration): akzeptieren, aber warnen — nächster Save schreibt Hash.
    logger.warning("plaintext_password_in_env — bitte über WebUI-Formular neu setzen, dann wird gehasht gespeichert")
    return secrets.compare_digest(candidate.encode("utf-8"), stored.encode("utf-8"))


def verify_password(candidate: str) -> bool:
    """Prueft `candidate` gegen das gespeicherte WEBUI_PASSWORD (bcrypt oder
    Legacy-Klartext)."""
    stored = _read_password()
    if not stored:
        return False
    return _verify_password(candidate, stored)


# WR-07: Meldung bewusst als Modul-Konstante — Tests pruefen darauf, ohne den
# Text zu duplizieren.
NO_AUTH_SETUP_HINT = "Bitte zuerst ein WebUI-Passwort setzen."


def require_setup() -> None:
    """Defense-in-Depth (WR-07/T-jrq-02): solange KEIN WebUI-Passwort gesetzt ist,
    werden gefaehrliche state-aendernde Routen (/reset, /agents*, /agent/*,
    /context/generate, /style/relearn, /chat/*/send) blockiert. Es gibt keinen
    Env-gesteuerten Bypass mehr — durch die `enforce_auth`-Middleware in
    `main.py` ohnehin unerreichbar ohne Passwort+Session, hier bewusst doppelt
    abgesichert."""
    if password_is_set():
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=NO_AUTH_SETUP_HINT)


def require_auth(request: Request) -> str:
    """Schlanke Dependency fuer bestehende Routen-Signaturen — wirft selbst NICHTS
    mehr. Die eigentliche Durchsetzung (Session-Gate) erfolgt in der
    `enforce_auth`-Middleware (main.py); diese Funktion bleibt nur als
    Kompatibilitaets-Anker fuer die bestehenden `Depends(auth.require_auth)`-
    Aufrufe (inkl. Add-in-Routen) erhalten und liefert schlicht den festen
    Benutzernamen zurueck."""
    return ADMIN_USER
