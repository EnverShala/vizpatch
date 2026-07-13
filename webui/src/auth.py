import os
import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

security = HTTPBasic()


def require_auth(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    webui_user = os.environ.get("WEBUI_USER")
    webui_password = os.environ.get("WEBUI_PASSWORD")
    if not webui_user or not webui_password:
        raise RuntimeError("WEBUI_USER and WEBUI_PASSWORD must be set in environment")
    user_ok = secrets.compare_digest(credentials.username.encode(), webui_user.encode())
    pass_ok = secrets.compare_digest(credentials.password.encode(), webui_password.encode())
    if not (user_ok and pass_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
