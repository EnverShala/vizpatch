import os
import tempfile

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from pathlib import Path

from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import auth, config_io, docker_ctrl, llm_seed, state_reader
from .logging_setup import setup_logging

setup_logging(os.getenv("LOG_LEVEL", "INFO"))

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Vizpatch WebUI", version="1.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
templates = Jinja2Templates(directory="src/templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/_auth_check", dependencies=[Depends(auth.require_auth)])
def auth_check() -> dict:
    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    user: str = Depends(auth.require_auth),
    saved: int = 0,
    reset: int = 0,
    error: str = "",
):
    env_vals = config_io.read_env_masked()
    context_md = config_io.read_context_md()
    status = docker_ctrl.get_agent_status()
    last_poll = state_reader.get_last_poll()
    drafts_status = state_reader.get_drafts_folder_status()
    missing = config_io.get_missing_config()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "env": env_vals,
            "context_md": context_md,
            "saved": saved,
            "reset": reset,
            "error": error,
            "status": status,
            "last_poll": last_poll,
            "drafts_status": drafts_status,
            "configured": not missing,
            "missing": missing,
            "auth_enabled": auth.is_auth_enabled(),
            "password_configured": bool((config_io.read_env_raw().get("WEBUI_PASSWORD") or "").strip()),
        },
    )


@app.get("/agent/status", response_class=HTMLResponse)
def agent_status(request: Request, user: str = Depends(auth.require_auth)):
    status = docker_ctrl.get_agent_status()
    last_poll = state_reader.get_last_poll()
    missing = config_io.get_missing_config()
    return templates.TemplateResponse(
        request,
        "_status_card.html",
        {"status": status, "last_poll": last_poll, "configured": not missing, "missing": missing},
    )


@app.post("/agent/{action}", response_class=HTMLResponse)
def agent_action(request: Request, action: str, user: str = Depends(auth.require_auth)):
    if action not in ("start", "stop"):
        raise HTTPException(status_code=400, detail="invalid action")
    missing = config_io.get_missing_config()
    if missing and action == "start":
        status = docker_ctrl.get_agent_status()
        last_poll = state_reader.get_last_poll()
        return templates.TemplateResponse(
            request,
            "_status_card.html",
            {
                "status": status,
                "last_poll": last_poll,
                "action_result": f"Konfiguration unvollständig — fehlt: {', '.join(missing)}",
                "configured": False,
                "missing": missing,
            },
            status_code=400,
        )
    result = docker_ctrl.control_agent(action)
    status = docker_ctrl.get_agent_status()
    last_poll = state_reader.get_last_poll()
    return templates.TemplateResponse(
        request,
        "_status_card.html",
        {
            "status": status,
            "last_poll": last_poll,
            "action_result": result,
            "configured": not missing,
            "missing": missing,
        },
    )


@app.post("/context/generate")
@limiter.limit("10/minute")
def context_generate(
    request: Request,
    firma_input: str = Form(..., max_length=5000),
    user: str = Depends(auth.require_auth),
):
    try:
        seed_text = llm_seed.generate(firma_input)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="LLM service error")
    return PlainTextResponse(seed_text)


def _save_response(request: Request, is_htmx: bool, ok: bool, message: str, redirect_query: str) -> object:
    """Section-Save (HTMX) → inline HTML-Fragment.
    Full-Form-Save → Redirect zu / mit Query-Flag."""
    if is_htmx:
        css = "save-ok" if ok else "save-err"
        icon = "&#10003;" if ok else "&#9888;"
        return HTMLResponse(f'<span class="{css}">{icon} {message}</span>')
    from urllib.parse import quote
    return RedirectResponse(f"/?{redirect_query}={quote(message) if not ok else '1'}", status_code=303)


@app.post("/save")
@limiter.limit("20/minute")
def save(
    request: Request,
    imap_user: str | None = Form(None),
    imap_password: str | None = Form(None),
    anthropic_api_key: str | None = Form(None),
    imap_drafts_folder: str | None = Form(None),
    autostart_enabled: str | None = Form(None),
    context_md: str | None = Form(None),
    webui_user: str | None = Form(None),
    webui_password_current: str | None = Form(None),
    webui_password_new: str | None = Form(None),
    user: str = Depends(auth.require_auth),
):
    is_htmx = request.headers.get("HX-Request") == "true"
    existing = config_io.read_env_raw()

    # Passwort-Change-Logik — nur wenn WebUI-Login-Felder tatsächlich mitgesendet wurden
    hashed_new_pw: str | None = None
    webui_user_new = (webui_user or "").strip() if webui_user is not None else None
    pw_current = webui_password_current or ""
    pw_new = webui_password_new or ""
    existing_pw = existing.get("WEBUI_PASSWORD", "").strip()

    # Nur validieren wenn WebUI-Login-Felder überhaupt Teil der Submission sind
    webui_section_submitted = (
        webui_user is not None
        or webui_password_current is not None
        or webui_password_new is not None
    )
    if webui_section_submitted:
        if existing_pw:
            if pw_new and not pw_current:
                return _save_response(request, is_htmx, False,
                    "Zum Ändern des Passworts bitte das aktuelle Passwort eintragen.", "error")
            if pw_current and not pw_new:
                return _save_response(request, is_htmx, False,
                    "Aktuelles Passwort eingegeben, aber kein neues — bitte auch ‚Neues Passwort‘ ausfüllen.", "error")
            if pw_new and pw_current:
                if not auth._verify_password(pw_current, existing_pw):
                    return _save_response(request, is_htmx, False,
                        "Aktuelles Passwort ist falsch.", "error")
                hashed_new_pw = auth.hash_password(pw_new)
        else:
            if webui_user_new and not pw_new:
                return _save_response(request, is_htmx, False,
                    "Beim ersten Setzen von WEBUI_USER muss auch ‚Neues Passwort‘ ausgefüllt sein.", "error")
            if pw_new:
                hashed_new_pw = auth.hash_password(pw_new)

    updates: dict[str, str] = {}
    if imap_user is not None:
        updates["IMAP_USER"] = imap_user
        # Own-Sender-Filter: IMAP_USER == OWN_EMAIL_ADDRESS für 99% aller Setups
        updates["OWN_EMAIL_ADDRESS"] = imap_user
    if autostart_enabled is not None:
        updates["AUTOSTART_ENABLED"] = "true" if autostart_enabled in ("true", "on", "1") else "false"
    if imap_drafts_folder is not None and imap_drafts_folder.strip() != "":
        updates["IMAP_DRAFTS_FOLDER"] = imap_drafts_folder.strip()
    if imap_password is not None and imap_password.strip() != "":
        updates["IMAP_PASSWORD"] = imap_password
    if anthropic_api_key is not None and anthropic_api_key.strip() != "":
        updates["ANTHROPIC_API_KEY"] = anthropic_api_key
    if webui_user_new:
        updates["WEBUI_USER"] = webui_user_new
    if hashed_new_pw is not None:
        updates["WEBUI_PASSWORD"] = hashed_new_pw

    if updates:
        config_io.write_env(updates)
    if context_md is not None:
        config_io.write_context_md_atomic(context_md)

    return _save_response(request, is_htmx, True, "Gespeichert", "saved")


@app.post("/reset")
def reset_all_endpoint(
    confirmation: str = Form(""),
    user: str = Depends(auth.require_auth),
):
    from urllib.parse import quote
    if confirmation != "LÖSCHEN":
        return RedirectResponse(
            f"/?error={quote('Zero-Reset abgebrochen: Bestätigungswort war nicht ‚LÖSCHEN‘.')}",
            status_code=303,
        )
    docker_ctrl.stop_and_remove_agent()
    config_io.reset_all()
    return RedirectResponse("/?reset=1", status_code=303)


@app.post("/update/pull", response_class=HTMLResponse)
def update_pull(request: Request, user: str = Depends(auth.require_auth)):
    image_ref = os.getenv("WEBUI_UPDATE_IMAGE_REF", "ghcr.io/EnverShala/vizpatch:latest")
    log = docker_ctrl.pull_and_restart(image_ref)
    return templates.TemplateResponse(
        request, "_update_log.html", {"log": log, "source": "pull", "image_ref": image_ref}
    )


@app.post("/update/upload", response_class=HTMLResponse)
def update_upload(
    request: Request,
    tarball: UploadFile = File(...),
    user: str = Depends(auth.require_auth),
):
    if not tarball.filename or not tarball.filename.endswith(".tar"):
        raise HTTPException(status_code=400, detail="Nur .tar-Files erlaubt")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".tar", dir=tempfile.gettempdir()) as tmp:
        while chunk := tarball.file.read(1024 * 1024):
            tmp.write(chunk)
        tmp_path = Path(tmp.name)
    try:
        log = docker_ctrl.load_and_restart(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return templates.TemplateResponse(
        request, "_update_log.html", {"log": log, "source": "upload", "filename": tarball.filename}
    )
