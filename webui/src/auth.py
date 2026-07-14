import logging
import os
import secrets
from pathlib import Path
from typing import Optional

import bcrypt
from dotenv import dotenv_values
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic(auto_error=False)
logger = logging.getLogger(__name__)


def _read_credentials() -> tuple[str, str]:
    env_path = Path(os.getenv("WEBUI_ENV_PATH", "/config/.env"))
    values = dotenv_values(env_path) if env_path.exists() else {}
    user = (values.get("WEBUI_USER") or os.environ.get("WEBUI_USER") or "").strip()
    password = (values.get("WEBUI_PASSWORD") or os.environ.get("WEBUI_PASSWORD") or "").strip()
    return user, password


def is_auth_enabled() -> bool:
    user, password = _read_credentials()
    return bool(user and password)


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


def require_auth(credentials: Optional[HTTPBasicCredentials] = Depends(security)) -> str:
    webui_user, webui_password = _read_credentials()
    if not webui_user or not webui_password:
        return "anonymous"
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    user_ok = secrets.compare_digest(credentials.username.encode(), webui_user.encode())
    pass_ok = _verify_password(credentials.password, webui_password)
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
