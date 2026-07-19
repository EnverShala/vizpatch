import json
import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from . import agents_io, auth, chat, chat_tools, config_io, crypto, docker_ctrl, llm_detect, llm_seed, state_reader, style_extract
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

# Datenschutz-Zustimmung (D-68): Stand der Bestimmungen, mit denen ein
# gegebenes PRIVACY_CONSENT_ACCEPTED=true korrespondiert (siehe _datenschutz.html).
PRIVACY_CONSENT_VERSION = "2026-07-17"
_CONSENT_TRUTHY = {"true", "on", "1"}

# Add-in-/Embed-Pfad-Klassifikation (Phase 8, D-66/T-08-02): NUR diese Pfade
# bekommen eine gelockerte CSP (Outlook muss die Taskpane + das darin
# geschachtelte Chat-Embed iframen können). Alle anderen Pfade bleiben strikt.
_ADDIN_EMBED_PATH_RE = re.compile(r"^/chat/[^/]+/embed$")

DEFAULT_ADDIN_FRAME_ANCESTORS = (
    "'self' https://outlook.office.com https://outlook.office365.com "
    "https://outlook.live.com https://outlook-sdf.office.com "
    "https://*.office.com https://*.office365.com"
)

# T-08-06: ADDIN_BASE_URL wird per Textreplace ins Manifest-XML eingesetzt —
# vor dem Einsetzen validiert (https://-Pflicht, keine XML-Sonderzeichen),
# sonst waere eine XML-Injection ueber einen fehlerhaft/boesartig gesetzten
# Env-Wert moeglich.
_XML_SPECIAL_CHARS_RE = re.compile(r'[<>"&]')
DEFAULT_ADDIN_BASE_URL = "https://CHANGE-ME.example"


def _is_addin_embeddable_path(path: str) -> bool:
    return path.startswith("/addin/") or bool(_ADDIN_EMBED_PATH_RE.match(path))


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"

    if _is_addin_embeddable_path(path):
        # Gelockerte Policy NUR für /addin/-Seiten + /chat/*/embed (T-08-01/T-08-02):
        # X-Frame-Options entfaellt komplett (kann nur DENY/SAMEORIGIN, wuerde
        # Cross-Origin-Framing durch Outlook blockieren) — die Kontrolle liegt bei
        # frame-ancestors, das per Default NUR 'self' + feste Office/Outlook-Origins
        # zulaesst (kein `*`-Wildcard, Clickjacking-Schutz).
        if "X-Frame-Options" in response.headers:
            del response.headers["X-Frame-Options"]
        frame_ancestors = os.getenv("ADDIN_FRAME_ANCESTORS", DEFAULT_ADDIN_FRAME_ANCESTORS)
        script_src = "'self' 'unsafe-inline'"
        frame_src_directive = ""
        if path.startswith("/addin/"):
            # Nur die Taskpane selbst darf office.js laden + das Embed schachteln;
            # /chat/*/embed bleibt ohne CDN-Freigabe (T-08-03).
            script_src += " https://appsforoffice.microsoft.com"
            frame_src_directive = "frame-src 'self'; "
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            f"script-src {script_src}; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            f"{frame_src_directive}"
            f"frame-ancestors {frame_ancestors}"
        )
    else:
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'"
        )
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
    root_env_raw = config_io.read_env_raw()
    privacy_consent_accepted = (root_env_raw.get("PRIVACY_CONSENT_ACCEPTED") or "").strip().lower() == "true"
    privacy_consent_at = root_env_raw.get("PRIVACY_CONSENT_AT") or ""

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
            "password_configured": bool((root_env_raw.get("WEBUI_PASSWORD") or "").strip()),
            "privacy_consent_accepted": privacy_consent_accepted,
            "privacy_consent_at": privacy_consent_at,
        },
    )


@app.get("/datenschutz", response_class=HTMLResponse)
def datenschutz(request: Request, user: str = Depends(auth.require_auth)):
    """Eigenständige Datenschutz-Seite (D-68) — dasselbe Fragment wie das
    aufklappbare Inline-Vorkommen in index.html, hier als Vollseite (z. B. zum
    Verlinken/Ausdrucken)."""
    return templates.TemplateResponse(request, "datenschutz.html", {})


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


@app.get("/addin/taskpane.html", response_class=HTMLResponse)
def addin_taskpane(request: Request, user: str = Depends(auth.require_auth)):
    """Outlook-Office.js-Taskpane (D-66/OUT-02): same-origin ausgeliefert, iframed
    das bestehende Chat-Embed. Kein 404-Guard nötig — die Seite listet nur die
    Agenten fürs Dropdown, der Existenz-Guard sitzt bereits in chat_embed()."""
    agents = agents_io.list_agent_ids()
    initial_agent = agents[0] if agents else ""
    return templates.TemplateResponse(
        request,
        "addin_taskpane.html",
        {"agents": agents, "initial_agent": initial_agent},
    )


@app.get("/addin/manifest.xml")
def addin_manifest(user: str = Depends(auth.require_auth)):
    """Klassisches XML-Add-in-Manifest (D-67/OUT-01), pro Installation über
    ADDIN_BASE_URL templatisiert. Wird als reine Textdatei geladen und per
    str.replace ersetzt (NICHT über TemplateResponse/Jinja2 gerendert) — kein
    Autoescape-Konflikt mit XML. ADDIN_BASE_URL wird VOR dem Einsetzen
    validiert (T-08-06): muss mit https:// beginnen und darf keine
    XML-Sonderzeichen enthalten, sonst 400 statt eines kaputten/injizierbaren
    Manifests."""
    base_url = os.getenv("ADDIN_BASE_URL", DEFAULT_ADDIN_BASE_URL).strip()
    if not base_url.startswith("https://") or _XML_SPECIAL_CHARS_RE.search(base_url):
        raise HTTPException(
            status_code=400,
            detail=(
                "ADDIN_BASE_URL ist ungültig — muss mit https:// beginnen und darf "
                'keine Zeichen <, >, " oder & enthalten.'
            ),
        )
    manifest_path = Path("src/templates/addin_manifest.xml")
    xml_text = manifest_path.read_text(encoding="utf-8").replace("{ADDIN_BASE_URL}", base_url)
    return PlainTextResponse(xml_text, media_type="application/xml")


def _sse_data_frame(text: str) -> str:
    """Kodiert einen Text-Chunk als SSE-`data:`-Frame — eingebettete Newlines
    werden zu mehreren `data:`-Fortsetzungszeilen desselben Events (SSE-Spec)."""
    body = "\n".join(f"data: {line}" for line in text.split("\n"))
    return f"{body}\n\n"


def _parse_chat_history(raw: str) -> list[dict]:
    """Parst den vom Browser gehaltenen Verlauf (D-58) defensiv aus dem
    JSON-Formfeld — bei Parse-Fehler oder falscher Struktur: leere Liste statt
    500 (T-07-09, manipulierte/kaputte history ist vollstaendig untrusted).
    Nur Turns mit str-role/str-content werden uebernommen, alles andere
    verworfen (kein Crash bei fremdartigen Einträgen)."""
    if not raw.strip():
        return []
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if not isinstance(data, list):
        return []
    parsed: list[dict] = []
    for turn in data:
        if not isinstance(turn, dict):
            continue
        role = turn.get("role")
        content = turn.get("content")
        if not isinstance(role, str) or not isinstance(content, str):
            continue
        parsed.append({"role": role, "content": content})
    return parsed


def _parse_mail_context(raw: str) -> dict | None:
    """Parst das optionale mail_context-Formfeld (D-65) defensiv — bei
    Parse-Fehler oder falscher Struktur: `None` (kein Mail-Block, kein Crash).
    In Phase 7 ungenutzt/leer; Phase 8 (OUT-03) fuellt es via Office.js."""
    if not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return {
        "subject": str(data.get("subject") or ""),
        "sender": str(data.get("sender") or ""),
        "body": str(data.get("body") or ""),
    }


@app.post("/chat/{agent_id}/send")
@limiter.limit(
    # Review IN-02: Default aus chat.CHAT_RATE_LIMIT_PER_MIN_DEFAULT statt
    # hier erneut hartkodiert — kein Konstanten-Drift zwischen den Modulen.
    lambda: f"{os.getenv('CHAT_RATE_LIMIT_PER_MIN', str(chat.CHAT_RATE_LIMIT_PER_MIN_DEFAULT))}/minute"
)
def chat_send(
    request: Request,
    agent_id: str,
    message: str = Form(...),
    history: str = Form(""),
    mail_context: str = Form(""),
    session_id: str = Form(""),
    user: str = Depends(auth.require_auth),
):
    """Streamt eine agentische Chat-Antwort via SSE (D-62/D-72/D-80). Provider/
    Key/Modell werden GENAU für `agent_id` aufgelöst (D-59-Intent) —
    `chat_tools.run_agentic_chat()` (CTOOL-01/02) läuft für Anthropic-Agenten
    die Tool-Use-Schleife (mit `mails_suchen`, D-74 Teil 1) und fällt für alle
    anderen Provider sauber auf den beratenden, werkzeuglosen Chat zurück
    (D-72/T-09-06, kein Absturz). Rate-Limit CHAT_RATE_LIMIT_PER_MIN (D-60, per
    Remote-Address) greift serverseitig weiter.

    `session_id` (Session-Autorisierung Papierkorb-Werkzeuge): vom Browser
    (`chat.js`) je Chat-Sitzung erzeugtes Formfeld, unverändert an
    `chat_tools.run_agentic_chat()` durchgereicht — dort entscheidet es, ob eine
    Verschiebung in den Papierkorb erneut bestätigt werden muss oder ob die
    Sitzung bereits (durch eine frühere bestätigte Verschiebung) autorisiert ist.

    PLAN-CHECKER-W1: `run_agentic_chat` ist ein Generator — dessen Rumpf läuft
    erst beim ersten `next()`, also NACH dem 200-Commit der StreamingResponse.
    Damit ein invalider `agent_id` (ValueError) oder ein fehlender Key
    (`ChatConfigError`) weiterhin EAGER als 400 ankommt (Phase-7-Regression,
    T-07-01), löst chat_send die Provider-Auflösung HIER — VOR dem Aufbau der
    StreamingResponse — bewusst noch einmal separat auf, bevor der Generator
    startet."""
    parsed_history = _parse_chat_history(history)
    parsed_mail_context = _parse_mail_context(mail_context)

    try:
        chat.resolve_chat_target(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid agent_id")
    except chat.ChatConfigError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        # Review WR-06: crypto.decrypt_value wirft bei falschem/rotiertem Key
        # (SEC-03-Fall) einen RuntimeError — als verstaendlicher 400 statt
        # generischem 500. ChatConfigError (Subklasse von RuntimeError) wird
        # oben bereits spezifischer behandelt.
        raise HTTPException(status_code=400, detail=f"Secret nicht entschlüsselbar: {e}")

    def _stream():
        try:
            for event in chat_tools.run_agentic_chat(
                agent_id, message, parsed_history, parsed_mail_context, session_id=session_id
            ):
                if event.get("type") == "tool":
                    yield f"event: tool\ndata: {event.get('label', '')}\n\n"
                else:
                    yield _sse_data_frame(event.get("text", ""))
            yield "event: done\ndata: \n\n"
        except Exception as e:
            logger.warning("chat_stream_error", extra={"agent_id": agent_id, "error": str(e)})
            # Review WR-05: str(e) kann Newlines enthalten (IMAP-/SDK-
            # Exceptions) — ohne `data:`-Fortsetzungszeilen wuerde der Client
            # die Folgezeilen stumm verwerfen bzw. Geister-Events sehen.
            yield "event: error\n" + _sse_data_frame(str(e))

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
    privacy_consent: str | None = Form(None),
    user: str = Depends(auth.require_auth),
):
    is_htmx = request.headers.get("HX-Request") == "true"
    existing = config_io.read_env_raw()

    # --- Datenschutz-Zustimmung (D-68): gated NUR den echten Agent-Konfig-Save
    # (IMAP-Creds/API-Key/context.md) — WebUI-Login-, Autostart- oder
    # Schreibstil-Section-Saves duerfen NIE daran scheitern. Ist der Consent
    # bereits im Root-.env persistiert, ist keine erneute Zustimmung noetig.
    consent_relevant_submitted = any(
        v is not None for v in (imap_user, imap_password, llm_api_key, context_md)
    )
    consent_already_persisted = (existing.get("PRIVACY_CONSENT_ACCEPTED") or "").strip().lower() == "true"
    consent_truthy_this_request = (privacy_consent or "").strip().lower() in _CONSENT_TRUTHY
    if consent_relevant_submitted and not consent_already_persisted:
        if not consent_truthy_this_request:
            return _save_response(
                request, is_htmx, False,
                "Bitte stimmen Sie den Datenschutzbestimmungen zu, bevor Sie Zugangsdaten speichern.",
                "error",
            )
        config_io.write_env(
            {
                "PRIVACY_CONSENT_ACCEPTED": "true",
                "PRIVACY_CONSENT_AT": datetime.now(timezone.utc).isoformat(),
                "PRIVACY_CONSENT_VERSION": PRIVACY_CONSENT_VERSION,
            }
        )
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
