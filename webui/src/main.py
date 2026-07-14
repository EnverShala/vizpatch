import os
import tempfile

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from pathlib import Path

from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import auth, config_io, docker_ctrl, llm_seed, state_reader
from .logging_setup import setup_logging

setup_logging(os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(title="Vizpatch WebUI", version="1.1.0")
templates = Jinja2Templates(directory="src/templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


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
    if action not in ("start", "stop", "restart"):
        raise HTTPException(status_code=400, detail="invalid action")
    missing = config_io.get_missing_config()
    if missing and action in ("start", "restart"):
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
def context_generate(
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


@app.post("/save")
def save(
    imap_user: str = Form(...),
    imap_password: str = Form(""),
    anthropic_api_key: str = Form(""),
    imap_drafts_folder: str = Form(""),
    autostart_enabled: str = Form("false"),
    context_md: str = Form(""),
    webui_user: str = Form(""),
    webui_password_current: str = Form(""),
    webui_password_new: str = Form(""),
    user: str = Depends(auth.require_auth),
):
    from urllib.parse import quote

    existing = config_io.read_env_raw()
    webui_user_new = webui_user.strip()
    existing_pw = existing.get("WEBUI_PASSWORD", "").strip()

    # Passwort-Logik
    hashed_new_pw: str | None = None
    if existing_pw:
        # Passwort bereits gesetzt — nur ändern wenn "Neues Passwort" ausgefüllt ist
        if webui_password_new and not webui_password_current:
            return RedirectResponse(
                f"/?error={quote('Zum Ändern des Passworts bitte das aktuelle Passwort ins Feld darüber eintragen.')}",
                status_code=303,
            )
        if webui_password_current and not webui_password_new:
            return RedirectResponse(
                f"/?error={quote('Aktuelles Passwort eingegeben, aber kein neues — bitte auch das Feld ‚Neues Passwort‘ ausfüllen (oder beide leer lassen um nichts zu ändern).')}",
                status_code=303,
            )
        if webui_password_new and webui_password_current:
            if not auth._verify_password(webui_password_current, existing_pw):
                return RedirectResponse(
                    f"/?error={quote('Aktuelles Passwort ist falsch.')}",
                    status_code=303,
                )
            hashed_new_pw = auth.hash_password(webui_password_new)
    else:
        # Kein Passwort gesetzt
        if webui_user_new and not webui_password_new:
            return RedirectResponse(
                f"/?error={quote('Beim ersten Setzen von WEBUI_USER muss auch ‚Neues Passwort‘ ausgefüllt sein (sonst wäre der Login unbrauchbar).')}",
                status_code=303,
            )
        if webui_password_new:
            hashed_new_pw = auth.hash_password(webui_password_new)

    updates: dict[str, str] = {
        "IMAP_USER": imap_user,
        # Own-Sender-Filter: IMAP_USER == OWN_EMAIL_ADDRESS für 99% aller Setups
        "OWN_EMAIL_ADDRESS": imap_user,
        "AUTOSTART_ENABLED": "true" if autostart_enabled in ("true", "on", "1") else "false",
    }
    if imap_drafts_folder.strip() != "":
        updates["IMAP_DRAFTS_FOLDER"] = imap_drafts_folder.strip()
    if imap_password.strip() != "":
        updates["IMAP_PASSWORD"] = imap_password
    if anthropic_api_key.strip() != "":
        updates["ANTHROPIC_API_KEY"] = anthropic_api_key
    if webui_user_new:
        updates["WEBUI_USER"] = webui_user_new
    if hashed_new_pw is not None:
        updates["WEBUI_PASSWORD"] = hashed_new_pw
    config_io.write_env(updates)
    config_io.write_context_md_atomic(context_md)
    return RedirectResponse("/?saved=1", status_code=303)


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
