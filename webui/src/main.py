import os
import tempfile

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from pathlib import Path

from fastapi.responses import HTMLResponse, RedirectResponse
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
):
    env_vals = config_io.read_env_masked()
    context_md = config_io.read_context_md()
    status = docker_ctrl.get_agent_status()
    last_poll = state_reader.get_last_poll()
    return templates.TemplateResponse(
        request,
        "index.html",
        {"env": env_vals, "context_md": context_md, "saved": saved, "status": status, "last_poll": last_poll},
    )


@app.get("/agent/status", response_class=HTMLResponse)
def agent_status(request: Request, user: str = Depends(auth.require_auth)):
    status = docker_ctrl.get_agent_status()
    last_poll = state_reader.get_last_poll()
    return templates.TemplateResponse(
        request, "_status_card.html", {"status": status, "last_poll": last_poll}
    )


@app.post("/agent/{action}", response_class=HTMLResponse)
def agent_action(request: Request, action: str, user: str = Depends(auth.require_auth)):
    if action not in ("start", "stop", "restart"):
        raise HTTPException(status_code=400, detail="invalid action")
    result = docker_ctrl.control_agent(action)
    status = docker_ctrl.get_agent_status()
    last_poll = state_reader.get_last_poll()
    return templates.TemplateResponse(
        request,
        "_status_card.html",
        {"status": status, "last_poll": last_poll, "action_result": result},
    )


@app.post("/context/generate", response_class=HTMLResponse)
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
    except Exception as e:
        raise HTTPException(status_code=500, detail="LLM service error")
    return templates.TemplateResponse(
        request, "_seed_output.html", {"seed_text": seed_text, "firma_input": firma_input}
    )


@app.post("/save")
def save(
    imap_user: str = Form(...),
    imap_password: str = Form(""),
    anthropic_api_key: str = Form(""),
    imap_drafts_folder: str = Form(...),
    own_email_address: str = Form(...),
    autostart_enabled: str = Form("false"),
    context_md: str = Form(""),
    user: str = Depends(auth.require_auth),
):
    updates: dict[str, str] = {
        "IMAP_USER": imap_user,
        "OWN_EMAIL_ADDRESS": own_email_address,
        "IMAP_DRAFTS_FOLDER": imap_drafts_folder,
        "AUTOSTART_ENABLED": "true" if autostart_enabled in ("true", "on", "1") else "false",
    }
    if imap_password.strip() != "":
        updates["IMAP_PASSWORD"] = imap_password
    if anthropic_api_key.strip() != "":
        updates["ANTHROPIC_API_KEY"] = anthropic_api_key
    config_io.write_env(updates)
    config_io.write_context_md_atomic(context_md)
    return RedirectResponse("/?saved=1", status_code=303)


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
