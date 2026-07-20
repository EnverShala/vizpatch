import logging
import os
import secrets
import threading
import time
from pathlib import Path
from typing import Optional

import bcrypt
from dotenv import dotenv_values
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic(auto_error=False)
logger = logging.getLogger(__name__)

_LOGIN_MAX_FAILURES = 5
_LOGIN_WINDOW_SEC = 900
_LOGIN_LOCKOUT_SEC = 900

_login_lock = threading.Lock()
_login_failures: dict[str, list[float]] = {}
_login_lockouts: dict[str, float] = {}


def _client_ip(request: Optional[Request]) -> str:
    if request is None or request.client is None:
        return "unknown"
    return request.client.host or "unknown"


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


def _read_credentials() -> tuple[str, str]:
    env_path = Path(os.getenv("WEBUI_ENV_PATH", "/config/.env"))
    values = dotenv_values(env_path) if env_path.exists() else {}
    user = (values.get("WEBUI_USER") or os.environ.get("WEBUI_USER") or "").strip()
    password = (values.get("WEBUI_PASSWORD") or os.environ.get("WEBUI_PASSWORD") or "").strip()
    return user, password


def is_auth_enabled() -> bool:
    user, password = _read_credentials()
    return bool(user and password)


def _allow_no_auth() -> bool:
    return (os.getenv("VIZPATCH_ALLOW_NO_AUTH") or "").strip().lower() == "true"


# WR-07: Meldung bewusst als Modul-Konstante — Tests pruefen darauf, ohne den
# Text zu duplizieren.
NO_AUTH_SETUP_HINT = (
    "Bitte zuerst WebUI-Benutzer + Passwort setzen (oder VIZPATCH_ALLOW_NO_AUTH=true)."
)


def require_setup() -> None:
    """WR-07 (Setup-Zwang, Docker-Socket = Host-Root): solange KEIN WebUI-Passwort
    gesetzt ist UND VIZPATCH_ALLOW_NO_AUTH != true, werden gefaehrliche
    state-aendernde Routen (/reset, /agents*, /agent/*, /context/generate,
    /style/relearn, /chat/*/send) blockiert. `/save` haengt bewusst NICHT an dieser
    Dependency, damit der Zero-Config-Bootstrap (Passwort erstmalig setzen) nie
    bricht. Sobald ein Passwort gesetzt ist, greift die normale Basic-Auth;
    `VIZPATCH_ALLOW_NO_AUTH=true` ist der explizite Bypass fuer isolierte Setups."""
    if is_auth_enabled() or _allow_no_auth():
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=NO_AUTH_SETUP_HINT)


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


def require_auth(
    request: Request,
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
) -> str:
    webui_user, webui_password = _read_credentials()
    if not webui_user or not webui_password:
        return "anonymous"
    _check_login_lockout(request)
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    user_ok = secrets.compare_digest(credentials.username.encode(), webui_user.encode())
    pass_ok = _verify_password(credentials.password, webui_password)
    if not (user_ok and pass_ok):
        _record_login_failure(request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
