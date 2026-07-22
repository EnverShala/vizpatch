import json
import logging
import mimetypes
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlparse

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from . import agents_io, auth, chat, chat_tools, config_io, crypto, docker_ctrl, llm_detect, llm_seed, state_reader, style_extract, validate_conn
from .logging_setup import setup_logging

setup_logging(os.getenv("LOG_LEVEL", "INFO"))

logger = logging.getLogger(__name__)


def _rate_limit_key(request: Request) -> str:
    """WR-05: slowapi-Schluessel ueber die Trusted-Proxy-bewusste Client-IP statt
    `get_remote_address` (das blind `request.client.host` nimmt). Hinter einem
    konfigurierten `TRUSTED_PROXY` wird so die echte Client-IP aus X-Forwarded-For
    genutzt (sonst teilen sich alle Clients die Proxy-IP = Selbst-DoS)."""
    return auth.client_ip(request)


limiter = Limiter(key_func=_rate_limit_key)

app = FastAPI(title="Vizpatch WebUI", version="1.2.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
templates = Jinja2Templates(directory="src/templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

PROVIDER_LABELS = {"anthropic": "Anthropic", "openai": "OpenAI", "google": "Google"}

# Review IN-04: serverseitige Obergrenze fuer context.md/style.md ueber /save.
MAX_CONFIG_MD_BYTES = 64 * 1024

# Phase 12 (ATT-01, D-94): Default-Obergrenze fuer Chat-Datei-Uploads (Rohgroesse,
# NICHT die spaeter base64-aufgeblähte Anhang-Groesse — siehe 12-RESEARCH.md Pitfall 4).
# Ueberschreibbar via MAX_ATTACHMENT_MB (agent/docker-compose.yml, globales Muster wie
# CHAT_MAX_TOKENS, Assumption A1 — kein per-Agent-Wert).
MAX_ATTACHMENT_MB_DEFAULT = 15

# tmp-Zielverzeichnis fuer Chat-Uploads (Streaming-Ziel vor der Pending-Upload-
# Registrierung, chat_tools.register_pending_upload). Container-lokal, kein
# /data-Volume-Bezug (Assumption A3, Single-Container-Deployment).
_CHAT_UPLOAD_TMP_DIRNAME = "vizpatch-uploads"

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


# --- CSRF-/Same-Origin-Enforcement (Review CR-01) ---
# Session-lose, zu Basic-Auth (keine Cookies) passende Abwehr: fuer jede unsichere
# Methode muss die Anfrage same-origin sein (Origin bevorzugt, sonst Referer-Host
# == Host). Fehlen beide -> abgelehnt. Ein echter Browser sendet bei Form-POSTs
# (auch cross-site) IMMER Origin bzw. Referer — nur ein CSRF-Angriff von einer
# fremden Seite traegt eine fremde Origin/Referer.
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# Add-in-Chat-Pfade (Phase 8): NUR diese duerfen zusaetzlich von den
# konfigurierten Office/Outlook-Origins cross-origin angesprochen werden — sonst
# funktioniert das Outlook-Add-in (Taskpane iframed das Chat-Embed und postet
# nach /chat/{id}/send) nicht. Alle anderen state-aendernden Routen bleiben
# strikt same-origin.
_ADDIN_CHAT_PATH_RE = re.compile(r"^/chat/[^/]+/(send|embed)$")


def _addin_allowed_origins() -> list[str]:
    """Leitet die erlaubten Add-in-Origins aus ADDIN_FRAME_ANCESTORS (bzw. dem
    Default) ab — dieselben `https://…`-Hosts, die auch in der gelockerten CSP
    das Framing durch Outlook erlauben. `'self'` wird verworfen (Same-Origin ist
    ohnehin generell erlaubt)."""
    # Ein gesetzter, aber LEERER Env-Wert (z. B. `ADDIN_FRAME_ANCESTORS: ${...:-}`
    # aus der Compose) darf den Default NICHT überschreiben — sonst wären gar keine
    # Add-in-Origins erlaubt und jeder Add-in-Request liefe in 403. `or`-Fallback +
    # strip() fangen leere/whitespace-Werte ab.
    raw = (os.getenv("ADDIN_FRAME_ANCESTORS") or "").strip() or DEFAULT_ADDIN_FRAME_ANCESTORS
    return [tok for tok in raw.split() if tok.startswith("https://")]


def _origin_pattern_match(origin: str, pattern: str) -> bool:
    """Vergleicht eine Origin (`https://host`) gegen ein Frame-Ancestor-Pattern.
    Exakter Treffer oder Wildcard-Subdomain (`https://*.office.com` deckt jede
    echte Subdomain von office.com ab, NICHT office.com selbst)."""
    if origin == pattern:
        return True
    scheme, _, host = origin.partition("://")
    p_scheme, _, p_host = pattern.partition("://")
    if scheme != p_scheme or not host:
        return False
    if p_host.startswith("*."):
        suffix = p_host[1:]  # ".office.com"
        return host.endswith(suffix) and len(host) > len(suffix)
    return False


def _origin_allowed_for_addin(origin: str) -> bool:
    if not origin:
        return False
    return any(_origin_pattern_match(origin, pat) for pat in _addin_allowed_origins())


@app.middleware("http")
async def enforce_same_origin(request: Request, call_next):
    """Review CR-01: CSRF-Abwehr fuer alle zustandsaendernden Requests. Same-Origin
    ist fuer ALLE Pfade erlaubt; die konfigurierten Add-in-Origins zusaetzlich NUR
    fuer die Add-in-Chat-Pfade (`POST /chat/{id}/send` bzw. das Embed). Alle
    uebrigen state-aendernden Routen (`/save`, `/reset`, `/agents*`, `/agent/*`,
    `/context/generate`, `/style/relearn`) bleiben strikt same-origin."""
    if request.method not in _SAFE_METHODS:
        origin = request.headers.get("origin")
        host = request.headers.get("host")
        referer = request.headers.get("referer")
        ok = False
        if origin:
            ok = urlparse(origin).netloc == host
        elif referer:
            ok = urlparse(referer).netloc == host
        # Add-in-Ausnahme (Origin-basiert): fremde Office/Outlook-Origins duerfen
        # AUSSCHLIESSLICH den Add-in-Chat-Pfad ansprechen.
        if not ok and origin and (
            _ADDIN_CHAT_PATH_RE.match(request.url.path)
            or request.url.path == "/addin/verify-password"
        ):
            ok = _origin_allowed_for_addin(origin)
        if not ok:
            return PlainTextResponse("cross-origin request rejected", status_code=403)
    return await call_next(request)


_PUBLIC_PATHS = {"/login", "/logout", "/setup", "/healthz"}


def _is_public_path(path: str) -> bool:
    return path in _PUBLIC_PATHS or path.startswith("/static/")


def _is_addin_session_exempt_path(path: str) -> bool:
    """Add-in-Pfade (T-jrq-06, 260722-jrq): das VSTO-WebBrowser-Control kann per
    Design keinen SameSite=Strict-Session-Cookie tragen (kein geteilter Cookie-Jar
    mit dem Browser, in dem der Betreiber eingeloggt ist) -- deshalb vom
    Session-Gate ausgenommen. Rest-Schutz bleibt ueber `require_setup` (Passwort
    muss gesetzt sein, Route-Dependency) + `enforce_same_origin` (Office-Origin-
    Allowlist fuer `/chat/*/send`)."""
    return path.startswith("/addin/") or bool(_ADDIN_CHAT_PATH_RE.match(path))


@app.middleware("http")
async def enforce_auth(request: Request, call_next):
    """Session-Login-Gate (D-03, 260722-jrq): ersetzt die vormalige
    Basic-Auth-Durchsetzung in `auth.require_auth`. Oeffentliche Pfade sowie die
    Add-in-Session-Ausnahme laufen ungegatet durch die Middleware (dort greift
    `require_setup` als Route-Dependency); alle uebrigen Pfade brauchen ein
    gesetztes WEBUI_PASSWORD UND eine gueltige Session (Cookie
    `auth.SESSION_COOKIE_NAME`). Ohne Passwort: Redirect auf `/setup` (Erststart-
    Zwang). Mit Passwort, aber ohne gueltige Session: volle Seiten-GETs (kein
    `HX-Request`-Header) werden auf `/login` umgeleitet, alle uebrigen
    (HTMX/POST/API) erhalten 401 -- das bestehende
    `hx-on::response-error 401 -> location.reload()` in base.html fuehrt
    HTMX-Polls dann sauber zum Login."""
    path = request.url.path
    if _is_public_path(path) or _is_addin_session_exempt_path(path):
        return await call_next(request)

    if not auth.password_is_set():
        return RedirectResponse("/setup", status_code=303)

    token = request.cookies.get(auth.SESSION_COOKIE_NAME)
    if auth.session_valid(token):
        return await call_next(request)

    if request.method == "GET" and request.headers.get("HX-Request") != "true":
        return RedirectResponse("/login", status_code=303)
    return PlainTextResponse("Unauthorized", status_code=401)


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
        frame_ancestors = (os.getenv("ADDIN_FRAME_ANCESTORS") or "").strip() or DEFAULT_ADDIN_FRAME_ANCESTORS
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


# --- Session-Login: /setup /login /logout /password (260722-jrq) -----------


def _validate_new_password(password: str, password_confirm: str) -> str:
    """Gemeinsame Validierung fuer /setup und /password (neues Passwort): min. 8
    Zeichen UND beide Felder identisch. Gibt eine deutsche Fehlermeldung zurueck
    (leer = gueltig)."""
    errors: list[str] = []
    if len(password) < 8:
        errors.append("Das Passwort muss mindestens 8 Zeichen lang sein.")
    if password != password_confirm:
        errors.append("Die beiden Passwörter stimmen nicht überein.")
    return " ".join(errors)


@app.get("/setup", response_class=HTMLResponse)
def setup_get(request: Request):
    if auth.password_is_set():
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(request, "setup.html", {"error": ""})


@app.post("/setup", response_class=HTMLResponse)
def setup_post(
    request: Request,
    password: str = Form(...),
    password_confirm: str = Form(...),
):
    if auth.password_is_set():
        return RedirectResponse("/login", status_code=303)
    error = _validate_new_password(password, password_confirm)
    if error:
        return templates.TemplateResponse(
            request, "setup.html", {"error": error}, status_code=400
        )
    config_io.write_env({"WEBUI_PASSWORD": auth.hash_password(password)})
    token = auth.create_session()
    resp = RedirectResponse("/", status_code=303)
    auth.set_session_cookie(resp, token)
    return resp


@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    if not auth.password_is_set():
        return RedirectResponse("/setup", status_code=303)
    return templates.TemplateResponse(request, "login.html", {"error": ""})


@app.post("/login", response_class=HTMLResponse)
def login_post(request: Request, password: str = Form(...)):
    if not auth.password_is_set():
        return RedirectResponse("/setup", status_code=303)
    auth._check_login_lockout(request)
    if auth.verify_password(password):
        token = auth.create_session()
        resp = RedirectResponse("/", status_code=303)
        auth.set_session_cookie(resp, token)
        return resp
    auth._record_login_failure(request)
    return templates.TemplateResponse(
        request, "login.html", {"error": "Falsches Passwort."}, status_code=401
    )


@app.post("/logout")
def logout_post(request: Request):
    token = request.cookies.get(auth.SESSION_COOKIE_NAME)
    auth.destroy_session(token)
    resp = RedirectResponse("/login", status_code=303)
    auth.clear_session_cookie(resp)
    return resp


@app.get("/password", response_class=HTMLResponse)
def password_get(request: Request):
    """Passwort-aendern-Popup-Partial (fuer #agent-dialog-body) -- die Middleware
    verlangt hierfuer bereits eine gueltige Session (kein Public-Pfad)."""
    return templates.TemplateResponse(request, "_password_form.html", {})


def _password_response(ok: bool, message: str) -> HTMLResponse:
    """Kleines Ergebnis-Fragment fuer #password-change-result (analog
    `_save_response`). Bei Erfolg traegt die Antwort `HX-Trigger:
    vizpatch-password-changed`, auf den ein globaler Listener (index.html)
    reagiert und den #agent-dialog schliesst."""
    css = "save-ok" if ok else "save-err"
    icon = "&#10003;" if ok else "&#9888;"
    headers = {"HX-Trigger": "vizpatch-password-changed"} if ok else None
    return HTMLResponse(f'<span class="{css}">{icon} {message}</span>', headers=headers)


@app.post("/password", response_class=HTMLResponse)
def password_post(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
):
    if not auth.verify_password(current_password):
        return _password_response(False, "Aktuelles Passwort ist falsch.")
    error = _validate_new_password(new_password, new_password_confirm)
    if error:
        return _password_response(False, error)
    config_io.write_env({"WEBUI_PASSWORD": auth.hash_password(new_password)})
    return _password_response(True, "Passwort geändert.")


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


def _privacy_consent_state() -> tuple[bool, str]:
    """Datenschutz-Zustimmung (D-68) lebt GLOBAL im Root-.env, nicht per Agent —
    wird sowohl von index() als auch von den neuen Popup-Partial-Routen
    (agent_edit/agent_new) benoetigt."""
    root_env_raw = config_io.read_env_raw()
    accepted = (root_env_raw.get("PRIVACY_CONSENT_ACCEPTED") or "").strip().lower() == "true"
    at = root_env_raw.get("PRIVACY_CONSENT_AT") or ""
    return accepted, at


def _autostart_enabled() -> bool:
    """Autostart-Flag (global, Root-.env). Wird in die Agenten-Uebersicht
    (_status_card.html) gerendert — daher an allen Render-Stellen der Card
    (index, /agents/status, Start/Stop, /agent/*) mitzugeben."""
    return (config_io.read_env_raw().get("AUTOSTART_ENABLED") or "").strip().lower() == "true"


def _agent_form_ctx(agent_id: str) -> dict:
    """Baut den per-Agent-Kontext fuers Config-Formular (Task 1, UMBAU-Plan
    260722-h9e): aus `index()` extrahiert, damit die neue `agent_edit`-Route
    (Popup-Partial) dieselbe Zusammenstellung wiederverwenden kann statt sie zu
    duplizieren. Secrets bleiben maskiert (`agents_io.read_env_masked`)."""
    return {
        "env": agents_io.read_env_masked(agent_id),
        "context_md": agents_io.read_context_md(agent_id),
        "style_md": agents_io.read_style_md(agent_id),
        "style_note": agents_io.read_style_note(agent_id),
        "drafts_status": state_reader.get_agent_status_json(agent_id),
        "missing": agents_io.get_missing_config(agent_id),
    }


@app.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    user: str = Depends(auth.require_auth),
    agent_id: str = "",
    new: int = 0,
    saved: int = 0,
    reset: int = 0,
    error: str = "",
):
    agents = agents_io.list_agent_ids()
    # `new=1` (Dropdown „-- Neuen Agent anlegen --") erzwingt die Anlege-Maske
    # statt automatisch agents[0] auszuwählen — sonst ist das Anlegen eines
    # zweiten Agenten unerreichbar, weil `/` ohne agent_id immer den ersten
    # Agenten selektiert.
    if new:
        active_id = ""
    else:
        active_id = agent_id or (agents[0] if agents else "")
    agent_statuses = _build_agent_statuses()
    privacy_consent_accepted, privacy_consent_at = _privacy_consent_state()

    if active_id and active_id in agents:
        form_ctx = _agent_form_ctx(active_id)
        env_vals = form_ctx["env"]
        context_md = form_ctx["context_md"]
        style_md = form_ctx["style_md"]
        style_note = form_ctx["style_note"]
        drafts_status = form_ctx["drafts_status"]
        missing = form_ctx["missing"]
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
            "autostart_enabled": _autostart_enabled(),
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
        {
            "agent_statuses": _build_agent_statuses(),
            "service_status": docker_ctrl.get_agent_status(),
            "autostart_enabled": _autostart_enabled(),
        },
    )


@app.get("/agents/{agent_id}/edit", response_class=HTMLResponse)
def agent_edit(request: Request, agent_id: str, user: str = Depends(auth.require_auth)):
    """Bearbeiten-Popup-Partial (UMBAU-D3): lazy per hx-get geladen, NUR fuer den
    angeklickten Agenten (kein Vorab-Rendern aller Agenten-Formulare — T-h9e-01).
    Secrets bleiben maskiert (`_agent_form_ctx` -> `read_env_masked`)."""
    if agent_id not in agents_io.list_agent_ids():
        raise HTTPException(status_code=404, detail="agent not found")
    privacy_consent_accepted, privacy_consent_at = _privacy_consent_state()
    return templates.TemplateResponse(
        request,
        "_agent_form.html",
        {
            "mode": "edit",
            "agent_id": agent_id,
            **_agent_form_ctx(agent_id),
            "privacy_consent_accepted": privacy_consent_accepted,
            "privacy_consent_at": privacy_consent_at,
        },
    )


@app.get("/agents/new", response_class=HTMLResponse)
def agent_new(request: Request, user: str = Depends(auth.require_auth)):
    """Anlege-Popup-Partial (UMBAU-D5): dasselbe Formular wie `agent_edit`, aber
    leer + mit Namensfeld — der eigentliche Agent wird erst beim Speichern
    (POST /save mit new_agent_name) angelegt."""
    privacy_consent_accepted, privacy_consent_at = _privacy_consent_state()
    return templates.TemplateResponse(
        request,
        "_agent_form.html",
        {
            "mode": "create",
            "agent_id": "",
            "env": {},
            "context_md": "",
            "style_md": "",
            "style_note": "",
            "drafts_status": {},
            "missing": [],
            "privacy_consent_accepted": privacy_consent_accepted,
            "privacy_consent_at": privacy_consent_at,
        },
    )


@app.post("/agents", dependencies=[Depends(auth.require_setup)])
@limiter.limit("30/minute")
def create_agent(
    request: Request,
    name_or_email: str = Form(...),
    user: str = Depends(auth.require_auth),
):
    slug = agents_io.slugify(name_or_email)
    # Neuer Agent startet GESTOPPT (Einrichtungs-Flow: erst konfigurieren, dann Start-Klick).
    agents_io.write_env(slug, {"AGENT_ENABLED": "false"})
    return RedirectResponse(f"/?agent_id={slug}", status_code=303)


@app.post("/agents/{agent_id}/rename", dependencies=[Depends(auth.require_setup)])
@limiter.limit("30/minute")
def rename_agent_endpoint(
    request: Request,
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


@app.post("/agents/{agent_id}/delete", dependencies=[Depends(auth.require_setup)])
@limiter.limit("30/minute")
def delete_agent_endpoint(
    request: Request,
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


@app.post(
    "/agents/{agent_id}/{action}",
    response_class=HTMLResponse,
    dependencies=[Depends(auth.require_setup)],
)
@limiter.limit("30/minute")
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
            "autostart_enabled": _autostart_enabled(),
            "action_result": "wirkt ab dem nächsten Poll-Zyklus",
        },
    )


@app.post(
    "/agent/{action}",
    response_class=HTMLResponse,
    dependencies=[Depends(auth.require_setup)],
)
@limiter.limit("30/minute")
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
            "autostart_enabled": _autostart_enabled(),
            "action_result": result,
        },
    )


@app.post("/context/generate", dependencies=[Depends(auth.require_setup)])
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
        # Review WR-06: generische Meldung nach außen, Details nur serverseitig.
        logger.warning("context_generate_value_error", extra={"agent_id": agent_id, "error": str(e)})
        raise HTTPException(status_code=400, detail="Anfrage ungültig oder Secret nicht entschlüsselbar.")
    except RuntimeError as e:
        logger.warning("context_generate_runtime_error", extra={"agent_id": agent_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="LLM-Dienst nicht erreichbar.")
    except Exception as e:
        logger.warning("context_generate_failed", extra={"agent_id": agent_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="Interner Fehler.")
    return PlainTextResponse(seed_text)


STY05_HINT = (
    "Zu wenig verwertbares Mail-Material und kein Freitext — bitte Stil kurz im "
    "Feld beschreiben oder später erneut versuchen."
)


@app.post("/style/relearn", dependencies=[Depends(auth.require_setup)])
@limiter.limit("10/minute")
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
        # Review WR-06: generische Meldung nach außen, Details nur serverseitig.
        logger.warning("style_relearn_value_error", extra={"agent_id": agent_id, "error": str(e)})
        raise HTTPException(status_code=400, detail="Anfrage ungültig.")
    except RuntimeError as e:
        logger.warning("style_relearn_runtime_error", extra={"agent_id": agent_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="LLM-Dienst nicht erreichbar.")
    except Exception as e:
        logger.warning("style_relearn_failed", extra={"agent_id": agent_id, "error": str(e)})
        raise HTTPException(status_code=500, detail="Stil-Extraktion fehlgeschlagen.")

    agents_io.write_style_md_atomic(agent_id, style_md)
    return PlainTextResponse(style_md)


@app.get(
    "/chat/{agent_id}/embed",
    response_class=HTMLResponse,
    dependencies=[Depends(auth.require_setup)],
)
def chat_embed(request: Request, agent_id: str, user: str = Depends(auth.require_auth)):
    """Chrome-loses, einbettbares Chat-Partial (D-61/CHAT-05) — eigener Rahmen,
    KEIN base.html-Erbe. Phase 8 (Outlook-Add-in) bindet dieselbe Route ein.
    T-jrq-06 (260722-jrq): Session-Gate-Ausnahme (Add-in-Pfad) — `require_setup`
    bleibt hier als Rest-Schutz (Passwort muss trotzdem gesetzt sein)."""
    if agent_id not in agents_io.list_agent_ids():
        raise HTTPException(status_code=404, detail="agent not found")
    return templates.TemplateResponse(request, "chat.html", {"agent_id": agent_id})


@app.get("/chat/{agent_id}/panel", response_class=HTMLResponse)
def chat_panel(request: Request, agent_id: str, user: str = Depends(auth.require_auth)):
    """Chat-Swap-Partial (UMBAU-D2): wird per hx-get in #chat-panel geladen, wenn
    der Betreiber das Radio einer anderen Agenten-Zeile klickt — derselbe
    404-Guard wie `chat_embed`."""
    if agent_id not in agents_io.list_agent_ids():
        raise HTTPException(status_code=404, detail="agent not found")
    return templates.TemplateResponse(request, "_chat_panel.html", {"agent_id": agent_id})


@app.get(
    "/addin/taskpane.html",
    response_class=HTMLResponse,
    dependencies=[Depends(auth.require_setup)],
)
def addin_taskpane(request: Request, user: str = Depends(auth.require_auth)):
    """Outlook-Office.js-Taskpane (D-66/OUT-02): same-origin ausgeliefert, iframed
    das bestehende Chat-Embed. Kein 404-Guard nötig — die Seite listet nur die
    Agenten fürs Dropdown, der Existenz-Guard sitzt bereits in chat_embed().
    T-jrq-06 (260722-jrq): Session-Gate-Ausnahme (/addin/*) — `require_setup`
    bleibt hier als Rest-Schutz (Passwort muss trotzdem gesetzt sein)."""
    agents = agents_io.list_agent_ids()
    initial_agent = agents[0] if agents else ""
    return templates.TemplateResponse(
        request,
        "addin_taskpane.html",
        {"agents": agents, "initial_agent": initial_agent},
    )


@app.get("/addin/manifest.xml", dependencies=[Depends(auth.require_setup)])
def addin_manifest(user: str = Depends(auth.require_auth)):
    """Klassisches XML-Add-in-Manifest (D-67/OUT-01), pro Installation über
    ADDIN_BASE_URL templatisiert. Wird als reine Textdatei geladen und per
    str.replace ersetzt (NICHT über TemplateResponse/Jinja2 gerendert) — kein
    Autoescape-Konflikt mit XML. ADDIN_BASE_URL wird VOR dem Einsetzen
    validiert (T-08-06): muss mit https:// beginnen und darf keine
    XML-Sonderzeichen enthalten, sonst 400 statt eines kaputten/injizierbaren
    Manifests.
    T-jrq-06 (260722-jrq): Session-Gate-Ausnahme (/addin/*) — `require_setup`
    bleibt hier als Rest-Schutz (Passwort muss trotzdem gesetzt sein)."""
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


@app.post("/addin/verify-password", dependencies=[Depends(auth.require_setup)])
@limiter.limit("10/minute")
def addin_verify_password(request: Request, password: str = Form("")):
    """Add-in-Einstellungs-Gate: prüft ein FRISCH eingegebenes WebUI-Passwort
    gegen `WEBUI_PASSWORD` (bcrypt). 200 `{ok:true}` bei korrekt, sonst 401. Das
    Add-in ruft dies vor dem Öffnen des Einstellungsdialogs auf und gibt die
    Felder nur bei 200 frei.

    Session-Gate-Ausnahme über den `/addin/`-Präfix (das VSTO-WebBrowser-Control
    trägt keinen Session-Cookie); Origin über die Add-in-Allowlist erlaubt (siehe
    `enforce_same_origin`). `require_setup` stellt sicher, dass überhaupt ein
    Passwort gesetzt ist. Das Passwort wird NIE geloggt; Rate-Limit gegen
    Brute-Force."""
    if auth.verify_password((password or "").strip()):
        return {"ok": True}
    raise HTTPException(status_code=401, detail="Falsches Passwort.")


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


def _parse_attachment_meta(raw: str) -> dict | None:
    """Parst das optionale attachment_meta-Formfeld (Phase 12, ATT-03) defensiv —
    streng nach dem Muster von `_parse_mail_context`: bei Parse-Fehler oder
    falscher Struktur `None` (kein DATEN-Block, kein Crash, Rueckwaertskompat).
    Traegt NUR Metadaten (Dateiname/Groesse/Mimetyp) einer zuvor per
    `/chat/{agent_id}/upload` hochgeladenen Datei — NIE den Dateiinhalt (D-96)."""
    if not raw.strip():
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    try:
        groesse = int(data.get("groesse") or 0)
    except (TypeError, ValueError):
        groesse = 0
    return {
        "dateiname": str(data.get("dateiname") or ""),
        "groesse": groesse,
        "mimetyp": str(data.get("mimetyp") or ""),
    }


@app.post("/chat/{agent_id}/send", dependencies=[Depends(auth.require_setup)])
@limiter.limit(
    # Review IN-02: Default aus chat.CHAT_RATE_LIMIT_PER_MIN_DEFAULT statt
    # hier erneut hartkodiert — kein Konstanten-Drift zwischen den Modulen.
    lambda: f"{os.getenv('CHAT_RATE_LIMIT_PER_MIN', str(chat.CHAT_RATE_LIMIT_PER_MIN_DEFAULT))}/minute"
)
def chat_send(
    request: Request,
    agent_id: str,
    # Review WR-03: Groessen-Limits gegen Kosten-/Speicher-DoS (analog
    # firma_input/style_note). message zusaetzlich in chat_tools hart gekappt.
    message: str = Form(..., max_length=8000),
    history: str = Form("", max_length=200_000),
    mail_context: str = Form(""),
    session_id: str = Form(""),
    attachment_meta: str = Form(""),
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

    `attachment_meta` (Phase 12, ATT-03): optionales JSON-Formfeld mit den
    Metadaten ({"dateiname", "groesse", "mimetyp"}) einer zuvor per
    `/chat/{agent_id}/upload` hochgeladenen Datei. Defensiv über
    `_parse_attachment_meta` geparst (analog `_parse_mail_context`) und
    unverändert als `attachment_meta=` an `chat_tools.run_agentic_chat()`
    durchgereicht — NIE der Dateiinhalt (D-96).

    PLAN-CHECKER-W1: `run_agentic_chat` ist ein Generator — dessen Rumpf läuft
    erst beim ersten `next()`, also NACH dem 200-Commit der StreamingResponse.
    Damit ein invalider `agent_id` (ValueError) oder ein fehlender Key
    (`ChatConfigError`) weiterhin EAGER als 400 ankommt (Phase-7-Regression,
    T-07-01), löst chat_send die Provider-Auflösung HIER — VOR dem Aufbau der
    StreamingResponse — bewusst noch einmal separat auf, bevor der Generator
    startet."""
    parsed_history = _parse_chat_history(history)
    parsed_mail_context = _parse_mail_context(mail_context)
    parsed_attachment_meta = _parse_attachment_meta(attachment_meta)

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
        # oben bereits spezifischer behandelt. Detail nur serverseitig loggen,
        # nach außen generisch (kein roher Exception-Text).
        logger.warning("chat_send_secret_error", extra={"agent_id": agent_id, "error": str(e)})
        raise HTTPException(status_code=400, detail="Secret nicht entschlüsselbar.")

    def _stream():
        try:
            for event in chat_tools.run_agentic_chat(
                agent_id,
                message,
                parsed_history,
                parsed_mail_context,
                session_id=session_id,
                attachment_meta=parsed_attachment_meta,
            ):
                if event.get("type") == "tool":
                    yield f"event: tool\ndata: {event.get('label', '')}\n\n"
                else:
                    yield _sse_data_frame(event.get("text", ""))
            yield "event: done\ndata: \n\n"
        except Exception as e:
            logger.warning("chat_stream_error", extra={"agent_id": agent_id, "error": str(e)})
            # Review WR-06: keinen rohen Exception-Text (Hostnamen/Server-
            # Antworten) an den Client streamen — generische Meldung, Details
            # nur serverseitig via logger.warning oben. _sse_data_frame bleibt
            # (robust auch bei mehrzeiligem Text).
            yield "event: error\n" + _sse_data_frame("Interner Fehler bei der Verarbeitung.")

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat/{agent_id}/upload", dependencies=[Depends(auth.require_setup)])
@limiter.limit(
    # Dieselbe Rate-Limit-Konstruktion wie chat_send (T-12-06, DoS-Schutz).
    lambda: f"{os.getenv('CHAT_RATE_LIMIT_PER_MIN', str(chat.CHAT_RATE_LIMIT_PER_MIN_DEFAULT))}/minute"
)
def chat_upload(
    request: Request,
    agent_id: str,
    file: UploadFile = File(...),
    session_id: str = Form(""),
    user: str = Depends(auth.require_auth),
):
    """Streaming-Datei-Upload für den Chat-Tool-Loop (ATT-01, D-92/94/96): legt die
    hochgeladene Datei server-generiert benannt in einem tmp-Verzeichnis ab und
    registriert sie im Pending-Upload-Store (`chat_tools.register_pending_upload`) —
    das eigentliche MIME-/IMAP-APPEND übernimmt `entwurf_mit_anhang` (Plan 12-01) im
    nächsten Chat-Turn.

    Dieselbe Auth-Kombination wie `chat_send` (`auth.require_setup` +
    `auth.require_auth`, D-95/ASVS V2). `agent_id` läuft durch denselben
    Existenz-Guard wie `chat_embed` (ASVS V4). Der Client-Dateiname wird NUR über
    `os.path.basename()` sanitized für Anzeige/Content-Disposition genutzt — das
    tmp-File selbst bekommt einen server-generierten Namen via `tempfile.mkstemp`
    (T-12-07/ASVS V5, Path-Traversal ausgeschlossen).

    Streaming: `file.file.read(1 MB)`-Chunks (KEIN `file.read()` — Full-Memory-Load,
    verletzt D-96) mit einem Live-Byte-Zähler gegen `MAX_ATTACHMENT_MB` (Default 15,
    T-12-06/Pitfall 4 aus 12-RESEARCH.md: Prüfung gegen die ROHE Byte-Anzahl, nicht
    die spätere base64-aufgeblähte Größe). Bei Überschreitung: 413 + tmp-Cleanup."""
    if agent_id not in agents_io.list_agent_ids():
        raise HTTPException(status_code=404, detail="agent not found")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id fehlt")

    max_bytes = chat._int_env("MAX_ATTACHMENT_MB", MAX_ATTACHMENT_MB_DEFAULT) * 1024 * 1024
    filename = os.path.basename(file.filename or "anhang")

    tmp_dir = Path(tempfile.gettempdir()) / _CHAT_UPLOAD_TMP_DIRNAME
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_name = tempfile.mkstemp(dir=tmp_dir, suffix=".upload")
    tmp_path = Path(tmp_name)
    os.close(tmp_fd)

    written = 0
    try:
        with tmp_path.open("wb") as out:
            while chunk := file.file.read(1024 * 1024):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Datei überschreitet das Limit von {max_bytes // (1024 * 1024)} MB.",
                    )
                out.write(chunk)
    except HTTPException:
        tmp_path.unlink(missing_ok=True)
        raise
    except Exception as e:
        tmp_path.unlink(missing_ok=True)
        logger.warning("chat_upload_failed", extra={"agent_id": agent_id, "error": str(e)})
        raise HTTPException(status_code=400, detail="Upload fehlgeschlagen.")

    mimetyp, _ = mimetypes.guess_type(filename)
    mimetyp = mimetyp or "application/octet-stream"
    chat_tools.register_pending_upload(agent_id, session_id, tmp_path, filename, written, mimetyp)
    return {"ok": True, "dateiname": filename, "groesse": written, "mimetyp": mimetyp}


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
    privacy_consent: str | None = Form(None),
    new_agent_name: str | None = Form(None),
    user: str = Depends(auth.require_auth),
):
    is_htmx = request.headers.get("HX-Request") == "true"

    # UMBAU-D5: „Neuer Agent"-Popup schickt beim ersten Speichern KEINE agent_id
    # mit (der Agent existiert ja noch nicht) — stattdessen new_agent_name. VOR
    # jeglicher weiteren Verarbeitung (Consent-Gate, agent-spezifische Updates)
    # wird der Agent hier angelegt und agent_id gesetzt, damit der restliche
    # Handler unveraendert mit einem echten agent_id weiterlaeuft (fuehlt sich fuer
    # den Nutzer wie EIN Submit an — die Zweistufigkeit des Backends bleibt intern).
    if not agent_id and (new_agent_name or "").strip():
        agent_id = agents_io.slugify(new_agent_name)
        agents_io.write_env(agent_id, {"AGENT_ENABLED": "false"})

    # Review IN-04: context_md/style_md serverseitig auf 64 KB begrenzen
    # (Disk-DoS + spaeter voller Inhalt in jedem Prompt). VOR jeglichem Write
    # dieses Requests geprueft -> kein Teil-Schreiben ueber dem Limit.
    for field_label, field_val in (("context.md", context_md), ("style.md", style_md)):
        if field_val is not None and len(field_val.encode("utf-8")) > MAX_CONFIG_MD_BYTES:
            return _save_response(
                request, is_htmx, False,
                f"{field_label} ist zu groß (max. 64 KB) — nicht gespeichert.",
                "error",
            )

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

    # WebUI-Login-Passwort lebt seit 260722-jrq exklusiv in POST /setup bzw.
    # POST /password — /save entschlackt (D-09), kein WEBUI_USER/WEBUI_PASSWORD
    # mehr in dieser Route.
    global_updates: dict[str, str] = {}
    if autostart_enabled is not None:
        global_updates["AUTOSTART_ENABLED"] = "true" if autostart_enabled in ("true", "on", "1") else "false"
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

        # API-Key-Pflicht (beide Popup-Modi, Bearbeiten UND Erstellen): der Agent
        # MUSS am Ende einen erkannten Provider haben. Ein in DIESEM Request neu
        # gesetzter Key wurde oben validiert (provider != None). Wird KEIN neuer Key
        # geschickt (Feld leer/maskiert), muss bereits ein erkannter Provider
        # vorliegen — sonst (z. B. „Neuer Agent" ohne/mit unerkanntem Key) Fehler.
        effective_provider = updates.get("LLM_PROVIDER") or (existing_agent_env.get("LLM_PROVIDER") or "").strip()
        if effective_provider not in ("anthropic", "openai", "google"):
            return _save_response(
                request, is_htmx, False,
                "Bitte einen gültigen API-Key hinterlegen — erwartet sk-ant-… (Anthropic), "
                "sk-… (OpenAI) oder AIza… (Google).",
                "error",
            )

        # --- Live-Verbindungsprüfung VOR dem Persistieren (Betreiber-Wunsch: kein
        # kaputter Agent). Geprüft wird NUR, was DIESES Request tatsächlich
        # ändert; bei Fehlschlag wird hart geblockt (nichts geschrieben). Die
        # effektive Konfig = bestehende (entschlüsselte) Agent-.env + Request-Delta.
        imap_changed = imap_user is not None or (imap_password is not None and imap_password.strip() != "")
        llm_key_changed = (
            llm_api_key is not None and llm_api_key.strip() != "" and llm_api_key != agents_io.MASKED
        )
        if imap_changed:
            enc_existing_pw = existing_agent_env.get("IMAP_PASSWORD", "") or ""
            try:
                existing_pw_plain = crypto.decrypt_value(enc_existing_pw) if enc_existing_pw else ""
            except Exception:
                existing_pw_plain = ""
            probe_env = {
                "IMAP_HOST": existing_agent_env.get("IMAP_HOST", ""),
                "IMAP_PORT": existing_agent_env.get("IMAP_PORT", ""),
                "IMAP_USE_SSL": existing_agent_env.get("IMAP_USE_SSL", ""),
                "IMAP_USER": updates.get("IMAP_USER") or (existing_agent_env.get("IMAP_USER") or ""),
                "IMAP_PASSWORD": (
                    imap_password
                    if (imap_password is not None and imap_password.strip() != "")
                    else existing_pw_plain
                ),
            }
            try:
                validate_conn.check_imap(probe_env)
            except validate_conn.ConnectionCheckError as e:
                return _save_response(request, is_htmx, False, f"Nicht gespeichert — {e}", "error")
        if llm_key_changed:
            effective_provider_for_check = updates.get("LLM_PROVIDER") or (
                existing_agent_env.get("LLM_PROVIDER") or ""
            )
            try:
                validate_conn.check_llm(effective_provider_for_check, llm_api_key)
            except validate_conn.ConnectionCheckError as e:
                return _save_response(request, is_htmx, False, f"Nicht gespeichert — {e}", "error")

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
            return _save_response(request, is_htmx, True, f"Gespeichert — LLM-Provider erkannt: {provider_label}", "saved")

    return _save_response(request, is_htmx, True, "Gespeichert", "saved")


@app.post("/reset", dependencies=[Depends(auth.require_setup)])
@limiter.limit("3/minute")
def reset_all_endpoint(
    request: Request,
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
