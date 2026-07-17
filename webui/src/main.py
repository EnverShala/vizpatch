import logging
import os
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import agents_io, auth, chat, config_io, crypto, docker_ctrl, llm_detect, llm_seed, state_reader, style_extract
from .logging_setup import setup_logging

setup_logging(os.getenv("LOG_LEVEL", "INFO"))

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Vizpatch WebUI", version="1.2.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
templates = Jinja2Templates(directory="src/templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

PROVIDER_LABELS = {"anthropic": "Anthropic", "openai": "OpenAI", "google": "Google"}


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


def _build_agent_statuses() -> list[dict]:
    """Baut die Status-Übersicht ALLER Agenten (D-50): Flag + Heartbeat + letzter Poll + fehlende Config."""
    result: list[dict] = []
    for aid in agents_io.list_agent_ids():
        enabled = agents_io.get_agent_enabled(aid)
        status_json = state_reader.get_agent_status_json(aid)
        result.append(
            {
                "id": aid,
                "enabled": enabled,
                "running": state_reader.is_running(enabled, status_json),
                "last_poll": state_reader.get_last_poll(aid),
                "status_json": status_json,
                "missing": agents_io.get_missing_config(aid),
            }
        )
    return result


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    user: str = Depends(auth.require_auth),
    agent_id: str = "",
    saved: int = 0,
    reset: int = 0,
    error: str = "",
):
    agents = agents_io.list_agent_ids()
    active_id = agent_id or (agents[0] if agents else "")
    agent_statuses = _build_agent_statuses()

    if active_id and active_id in agents:
        env_vals = agents_io.read_env_masked(active_id)
        context_md = agents_io.read_context_md(active_id)
        style_md = agents_io.read_style_md(active_id)
        style_note = agents_io.read_style_note(active_id)
        drafts_status = state_reader.get_agent_status_json(active_id)
        missing = agents_io.get_missing_config(active_id)
    else:
        active_id = ""
        env_vals = {}
        context_md = ""
        style_md = ""
        style_note = ""
        drafts_status = {}
        missing = []

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "agent_id": active_id,
            "agents": agents,
            "agent_statuses": agent_statuses,
            "env": env_vals,
            "global_env": config_io.read_env_masked(),
            "context_md": context_md,
            "style_md": style_md,
            "style_note": style_note,
            "saved": saved,
            "reset": reset,
            "error": error,
            "service_status": docker_ctrl.get_agent_status(),
            "drafts_status": drafts_status,
            "configured": not missing,
            "missing": missing,
            "auth_enabled": auth.is_auth_enabled(),
            "password_configured": bool((config_io.read_env_raw().get("WEBUI_PASSWORD") or "").strip()),
        },
    )


@app.get("/agents/status", response_class=HTMLResponse)
def agents_status(request: Request, user: str = Depends(auth.require_auth)):
    return templates.TemplateResponse(
        request,
        "_status_card.html",
        {"agent_statuses": _build_agent_statuses(), "service_status": docker_ctrl.get_agent_status()},
    )


@app.post("/agents")
def create_agent(
    request: Request,
    name_or_email: str = Form(...),
    user: str = Depends(auth.require_auth),
):
    slug = agents_io.slugify(name_or_email)
    # Neuer Agent startet GESTOPPT (Einrichtungs-Flow: erst konfigurieren, dann Start-Klick).
    agents_io.write_env(slug, {"AGENT_ENABLED": "false"})
    return RedirectResponse(f"/?agent_id={slug}", status_code=303)


@app.post("/agents/{agent_id}/rename")
def rename_agent_endpoint(
    agent_id: str,
    new_name: str = Form(...),
    user: str = Depends(auth.require_auth),
):
    new_slug = agents_io.slugify(new_name)
    try:
        agents_io.rename_agent(agent_id, new_slug)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse(f"/?agent_id={new_slug}", status_code=303)


@app.post("/agents/{agent_id}/delete")
def delete_agent_endpoint(
    agent_id: str,
    confirmation: str = Form(""),
    user: str = Depends(auth.require_auth),
):
    if confirmation != "LÖSCHEN":
        return RedirectResponse(
            f"/?agent_id={agent_id}&error={quote('Löschen abgebrochen: Bestätigungswort war nicht ‚LÖSCHEN‘.')}",
            status_code=303,
        )
    try:
        agents_io.delete_agent(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return RedirectResponse("/", status_code=303)


@app.post("/agents/{agent_id}/{action}", response_class=HTMLResponse)
def agent_flag_toggle(
    request: Request,
    agent_id: str,
    action: str,
    user: str = Depends(auth.require_auth),
):
    if action not in ("start", "stop"):
        raise HTTPException(status_code=400, detail="invalid action")
    try:
        agents_io.set_agent_enabled(agent_id, action == "start")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return templates.TemplateResponse(
        request,
        "_status_card.html",
        {
            "agent_statuses": _build_agent_statuses(),
            "service_status": docker_ctrl.get_agent_status(),
            "action_result": "wirkt ab dem nächsten Poll-Zyklus",
        },
    )


@app.post("/agent/{action}", response_class=HTMLResponse)
def agent_action(request: Request, action: str, user: str = Depends(auth.require_auth)):
    """Globale Admin-Funktion (Phase-4-Umfang): steuert den EINEN agent-Service via Docker."""
    if action not in ("start", "stop"):
        raise HTTPException(status_code=400, detail="invalid action")
    result = docker_ctrl.control_agent(action)
    return templates.TemplateResponse(
        request,
        "_status_card.html",
        {
            "agent_statuses": _build_agent_statuses(),
            "service_status": docker_ctrl.get_agent_status(),
            "action_result": result,
        },
    )


@app.post("/context/generate")
@limiter.limit("10/minute")
def context_generate(
    request: Request,
    agent_id: str = Form(...),
    firma_input: str = Form(..., max_length=5000),
    user: str = Depends(auth.require_auth),
):
    try:
        env = agents_io.read_env_raw(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid agent_id")

    provider = (env.get("LLM_PROVIDER") or "").strip()
    if provider != "anthropic":
        raise HTTPException(
            status_code=400,
            detail=(
                "Der Context-Assistent nutzt Anthropic — dieser Agent verwendet "
                f"{provider or 'keinen erkannten Provider'}. context.md bitte manuell pflegen "
                "oder einen Anthropic-Key hinterlegen."
            ),
        )
    raw_key = (env.get("LLM_API_KEY") or "").strip()
    if not raw_key:
        raise HTTPException(status_code=400, detail="Kein API-Key für diesen Agenten gespeichert")

    try:
        api_key = crypto.decrypt_value(raw_key)
        seed_text = llm_seed.generate(firma_input, api_key=api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="LLM service error")
    return PlainTextResponse(seed_text)


STY05_HINT = (
    "Zu wenig verwertbares Mail-Material und kein Freitext — bitte Stil kurz im "
    "Feld beschreiben oder später erneut versuchen."
)


@app.post("/style/relearn")
@limiter.limit("5/minute")
def style_relearn(
    request: Request,
    agent_id: str = Form(...),
    style_note: str = Form("", max_length=5000),
    user: str = Depends(auth.require_auth),
):
    """Schreibstil neu lernen (STY-03). Provider-agnostisch (D-55) — bewusst KEIN
    Anthropic-only-Gate wie bei /context/generate. Persistiert style_note VOR der
    Extraktion, damit die manuelle Angabe auch bei einem Fehlschlag erhalten bleibt
    (überlebt Re-Learn laut D-54)."""
    try:
        agents_io.read_env_raw(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid agent_id")

    agents_io.write_style_note_atomic(agent_id, style_note)

    try:
        style_md = style_extract.extract_style(agent_id)
    except style_extract.StyleExtractionEmpty:
        raise HTTPException(status_code=400, detail=STY05_HINT)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Stil-Extraktion fehlgeschlagen")

    agents_io.write_style_md_atomic(agent_id, style_md)
    return PlainTextResponse(style_md)


@app.get("/chat/{agent_id}/embed", response_class=HTMLResponse)
def chat_embed(request: Request, agent_id: str, user: str = Depends(auth.require_auth)):
    """Chrome-loses, einbettbares Chat-Partial (D-61/CHAT-05) — eigener Rahmen,
    KEIN base.html-Erbe. Phase 8 (Outlook-Add-in) bindet dieselbe Route ein."""
    if agent_id not in agents_io.list_agent_ids():
        raise HTTPException(status_code=404, detail="agent not found")
    return templates.TemplateResponse(request, "chat.html", {"agent_id": agent_id})


def _sse_data_frame(text: str) -> str:
    """Kodiert einen Text-Chunk als SSE-`data:`-Frame — eingebettete Newlines
    werden zu mehreren `data:`-Fortsetzungszeilen desselben Events (SSE-Spec)."""
    body = "\n".join(f"data: {line}" for line in text.split("\n"))
    return f"{body}\n\n"


@app.post("/chat/{agent_id}/send")
def chat_send(
    agent_id: str,
    message: str = Form(...),
    user: str = Depends(auth.require_auth),
):
    """Streamt eine Chat-Antwort via SSE (D-62, Walking-Skeleton). Provider/Key/
    Modell werden GENAU für `agent_id` aufgelöst (D-59-Intent) — kein Anthropic-
    Sonderweg. Der System-Prompt injiziert context.md/style.md/Status (CHAT-02,
    D-64); Rate-Limit + echte Multi-Turn-History kommen erst in 07-03."""
    try:
        provider, api_key, model = chat.resolve_chat_target(agent_id)
        system_prompt = chat.build_system_prompt(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid agent_id")
    except chat.ChatConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))

    prompt = f"{system_prompt}\n\n# Nachricht des Betreibers\n\n{message}"

    def _stream():
        try:
            for piece in chat.stream_chat(
                provider=provider,
                api_key=api_key,
                model=model,
                prompt=prompt,
                max_tokens=2000,
                temperature=0.7,
            ):
                yield _sse_data_frame(piece)
            yield "event: done\ndata: \n\n"
        except Exception as e:
            logger.warning("chat_stream_error", extra={"agent_id": agent_id, "error": str(e)})
            yield f"event: error\ndata: {e}\n\n"

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _save_response(request: Request, is_htmx: bool, ok: bool, message: str, redirect_query: str) -> object:
    """Section-Save (HTMX) → inline HTML-Fragment.
    Full-Form-Save → Redirect zu / mit Query-Flag."""
    if is_htmx:
        css = "save-ok" if ok else "save-err"
        icon = "&#10003;" if ok else "&#9888;"
        return HTMLResponse(f'<span class="{css}">{icon} {message}</span>')
    return RedirectResponse(f"/?{redirect_query}={quote(message) if not ok else '1'}", status_code=303)


@app.post("/save")
@limiter.limit("20/minute")
def save(
    request: Request,
    agent_id: str = Form(""),
    imap_user: str | None = Form(None),
    imap_password: str | None = Form(None),
    llm_api_key: str | None = Form(None),
    imap_drafts_folder: str | None = Form(None),
    autostart_enabled: str | None = Form(None),
    context_md: str | None = Form(None),
    style_md: str | None = Form(None),
    style_note: str | None = Form(None),
    enable_style_adaption: str | None = Form(None),
    webui_user: str | None = Form(None),
    webui_password_current: str | None = Form(None),
    webui_password_new: str | None = Form(None),
    user: str = Depends(auth.require_auth),
):
    is_htmx = request.headers.get("HX-Request") == "true"
    existing = config_io.read_env_raw()

    # --- Cred-Transition-Erfassung (Esso-Guard, D-53/D-54/SC5): Ist-Zustand VOR
    # jeglichem Write dieses Requests. "style.md fehlt" ist BEWUSST NICHT der
    # Auto-Trigger unten — nur der echte Cred-Uebergang unvollstaendig->vollstaendig
    # durch DIESES Request-Delta. Ein migrierter Agent, dessen Creds schon vorher
    # komplett waren, kann diese Bedingung nie erfuellen (creds_before_complete=True).
    existing_agent_env: dict[str, str] = {}
    if agent_id:
        try:
            existing_agent_env = agents_io.read_env_raw(agent_id)
        except ValueError:
            existing_agent_env = {}
    creds_before_complete = all(
        (existing_agent_env.get(k) or "").strip() for k in ("IMAP_USER", "IMAP_PASSWORD", "LLM_API_KEY")
    )

    # --- WebUI-Login-Passwort-Change-Logik (global, Root-.env) ---
    hashed_new_pw: str | None = None
    webui_user_new = (webui_user or "").strip() if webui_user is not None else None
    pw_current = webui_password_current or ""
    pw_new = webui_password_new or ""
    existing_pw = existing.get("WEBUI_PASSWORD", "").strip()

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

    global_updates: dict[str, str] = {}
    if autostart_enabled is not None:
        global_updates["AUTOSTART_ENABLED"] = "true" if autostart_enabled in ("true", "on", "1") else "false"
    if webui_user_new:
        global_updates["WEBUI_USER"] = webui_user_new
    if hashed_new_pw is not None:
        global_updates["WEBUI_PASSWORD"] = hashed_new_pw
    if global_updates:
        config_io.write_env(global_updates)

    # --- Schreibstil-Section (STY-03): eigenes Fieldset, unabhaengig speicherbar ---
    style_fields_submitted = any(v is not None for v in (style_md, style_note, enable_style_adaption))
    if style_fields_submitted:
        if not agent_id:
            return _save_response(request, is_htmx, False, "Kein Agent ausgewählt.", "error")
        try:
            if style_md is not None:
                agents_io.write_style_md_atomic(agent_id, style_md)
            if style_note is not None:
                agents_io.write_style_note_atomic(agent_id, style_note)
            if enable_style_adaption is not None:
                agents_io.write_env(
                    agent_id,
                    {
                        "ENABLE_STYLE_ADAPTION": (
                            "true" if enable_style_adaption in ("true", "on", "1") else "false"
                        )
                    },
                )
        except ValueError:
            return _save_response(request, is_htmx, False, "Ungültiger Agent.", "error")

    # --- Agent-spezifische Updates (D-51: Provider-Autodetect aus llm_api_key) ---
    agent_fields_submitted = any(
        v is not None for v in (imap_user, imap_password, llm_api_key, imap_drafts_folder, context_md)
    )
    if agent_fields_submitted:
        if not agent_id:
            return _save_response(request, is_htmx, False, "Kein Agent ausgewählt.", "error")

        updates: dict[str, str] = {}
        if imap_user is not None:
            updates["IMAP_USER"] = imap_user
            # Own-Sender-Filter: IMAP_USER == OWN_EMAIL_ADDRESS für 99% aller Setups.
            # WR-05: eine BEWUSST abweichend gesetzte OWN_EMAIL_ADDRESS (z.B. Shared-
            # Alias statt Login) darf ein IMAP-Section-Save nicht stillschweigend
            # zurücksetzen — nur defaulten, wenn sie fehlt oder bisher an IMAP_USER
            # gekoppelt war.
            try:
                existing_env = agents_io.read_env_raw(agent_id)
            except ValueError:
                existing_env = {}  # ungültige agent_id -> Fehler kommt unten aus write_env
            existing_own = (existing_env.get("OWN_EMAIL_ADDRESS") or "").strip()
            existing_imap_user = (existing_env.get("IMAP_USER") or "").strip()
            if not existing_own or existing_own == existing_imap_user:
                updates["OWN_EMAIL_ADDRESS"] = imap_user
        if imap_drafts_folder is not None and imap_drafts_folder.strip() != "":
            updates["IMAP_DRAFTS_FOLDER"] = imap_drafts_folder.strip()
        if imap_password is not None and imap_password.strip() != "":
            updates["IMAP_PASSWORD"] = imap_password
        if llm_api_key is not None and llm_api_key.strip() != "" and llm_api_key != agents_io.MASKED:
            provider = llm_detect.detect_llm_provider(llm_api_key)
            if provider is None:
                return _save_response(
                    request, is_htmx, False,
                    "API-Key-Format nicht erkannt — erwartet sk-ant-… (Anthropic), sk-… (OpenAI) oder AIza… (Google)",
                    "error",
                )
            updates["LLM_API_KEY"] = llm_api_key
            updates["LLM_PROVIDER"] = provider

        try:
            if updates:
                agents_io.write_env(agent_id, updates)
            if context_md is not None:
                agents_io.write_context_md_atomic(agent_id, context_md)
        except ValueError:
            return _save_response(request, is_htmx, False, "Ungültiger Agent.", "error")

        # --- Auto-Extraktion bei Neuanlage-Transition (STY-01, Esso-Guard) ---
        # Feuert best-effort NUR wenn Creds durch DIESES Request-Delta von
        # unvollstaendig auf vollstaendig wechseln, noch kein style.md existiert
        # und ENABLE_STYLE_ADAPTION != "false". Vollstaendig in try/except (T-06-07,
        # graceful) — ein Fehlschlag der Extraktion darf den Save nie blockieren.
        try:
            agent_env_after = agents_io.read_env_raw(agent_id)
        except ValueError:
            agent_env_after = {}
        creds_after_complete = all(
            (agent_env_after.get(k) or "").strip() for k in ("IMAP_USER", "IMAP_PASSWORD", "LLM_API_KEY")
        )
        style_adaption_enabled = (agent_env_after.get("ENABLE_STYLE_ADAPTION") or "true").strip().lower() != "false"
        if (
            not creds_before_complete
            and creds_after_complete
            and not agents_io.read_style_md(agent_id)
            and style_adaption_enabled
        ):
            try:
                auto_style_md = style_extract.extract_style(agent_id)
                agents_io.write_style_md_atomic(agent_id, auto_style_md)
            except Exception as e:
                logger.warning("auto_style_extract_failed", extra={"agent_id": agent_id, "error": str(e)})

        if "LLM_PROVIDER" in updates:
            provider_label = PROVIDER_LABELS.get(updates["LLM_PROVIDER"], updates["LLM_PROVIDER"])
            return _save_response(request, is_htmx, True, f"Gespeichert — Provider erkannt: {provider_label}", "saved")

    return _save_response(request, is_htmx, True, "Gespeichert", "saved")


@app.post("/reset")
def reset_all_endpoint(
    confirmation: str = Form(""),
    user: str = Depends(auth.require_auth),
):
    if confirmation != "LÖSCHEN":
        return RedirectResponse(
            f"/?error={quote('Zero-Reset abgebrochen: Bestätigungswort war nicht ‚LÖSCHEN‘.')}",
            status_code=303,
        )
    # Alle Agenten (Config + State) entfernen (MA-01/D-50).
    for aid in agents_io.list_agent_ids():
        agents_io.delete_agent(aid)
    # Fernet-Key-Datei löschen (SEC-03: Zero-Reset löscht den Key mit).
    key_file = Path(os.getenv("VIZPATCH_SECRET_KEY_FILE", "/config/.secret_key"))
    key_file.unlink(missing_ok=True)
    # Den einen Agent-Container stoppen/entfernen (Phase-4-Signatur, parameterlos).
    docker_ctrl.stop_and_remove_agent()
    # Root-.env (WebUI-globale Settings) leeren.
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
