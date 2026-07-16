# Phase 5: Multi-LLM, Multi-Agent & Verschlüsselung (v1.2) - Pattern Map

> ## ⚠ Addendum 2026-07-16 — Architektur-Korrektur (neues D-46)
>
> Neues D-46 (05-CONTEXT.md): EIN Agent-Container mit Multi-Account-Loop + `AGENT_ENABLED`-Flag —
> KEIN Container pro Agent. Damit sind in dieser Pattern-Map **obsolet**: die Zeile/Sektion
> `webui/tests/test_docker_ctrl_multi_agent.py`, die docker_ctrl.py-Erweiterungs-Sektion
> (Self-Inspection/`create_or_replace_agent_container`/Update-Flow-Umbau) und alle Verweise auf
> RESEARCH.md Zeilen 268-346. `webui/src/docker_ctrl.py` bleibt auf Phase-4-Stand (globales
> Start/Stop/Restart/Update des einen agent-Service).
>
> **Weiterhin gültig:** alle übrigen Pattern-Zuweisungen (llm.py, crypto.py, agents_io.py,
> migration.py, state_reader.py, main.py-Routen, Templates, Test-Idiome). Neu hinzu kommt der
> Multi-Account-Loop in `agent/src/main.py` (Analog: bestehende `_poll_once`/`_wait_for_config`-Struktur,
> außen ergänzt um Agenten-Discovery + Fehler-Isolation — siehe Plan 05.02-agent-multi-account-loop)
> sowie `agents_io.set_agent_enabled` (Analog: write_env-Line-Parser).


**Mapped:** 2026-07-15
**Files analyzed:** 22 (11 neu, 11 geändert)
**Analogs found:** 20 / 22

## File Classification

| Neue/geänderte Datei | Rolle | Data Flow | Nächster Analog | Match-Qualität |
|---|---|---|---|---|
| `agent/src/llm.py` (neu) | service (Dispatcher) | request-response | `agent/src/provider_config.py` (Dispatch-Tabelle) + `agent/src/classify.py` (Anthropic-Call-Shape) | role-match |
| `agent/src/crypto.py` (neu) | utility (Secret-Handling) | transform | `webui/src/auth.py` (bcrypt-Hash/Verify als Secret-Pattern) | role-match |
| `webui/src/crypto.py` (neu) | utility (Secret-Handling) | transform | `webui/src/auth.py` | role-match |
| `webui/src/agents_io.py` (neu, Claude's Discretion) | service/config-io | CRUD (Datei-I/O) | `webui/src/config_io.py` (read/write .env + context.md) | exact (wird direkt daraus erweitert) |
| `webui/src/migration.py` (neu, Claude's Discretion — oder Funktion in `agents_io.py`) | service (Startup-Hook) | batch/file-I/O | `webui/docker-entrypoint.sh` (Zero-Config-Seeding) + `webui/src/config_io.reset_all()` (Datei-Operationen-Stil) | role-match |
| `agent/tests/test_llm.py` (neu) | test | request-response | `agent/tests/test_classify.py` (mock_config + mock_anthropic-Fixtures) | exact |
| `agent/tests/test_crypto.py` (neu) | test | transform | `webui/tests/test_config_io.py` (tmp_path + monkeypatch-Stil) | role-match |
| `webui/tests/test_crypto.py` (neu) | test | transform | `webui/tests/test_config_io.py` | exact |
| `webui/tests/test_agents_io.py` (neu) | test | CRUD | `webui/tests/test_config_io.py` | exact |
| `webui/tests/test_docker_ctrl_multi_agent.py` (neu) | test | event-driven (Docker-SDK) | `webui/tests/test_docker_ctrl.py` (MagicMock-Client-Pattern) | exact |
| `webui/tests/test_migration.py` (neu) | test | batch/file-I/O | `webui/tests/test_config_io.py` (reset_all-artige Tests) | role-match |
| `agent/src/classify.py` (geändert) | service | request-response | sich selbst (Ist-Zustand als Ausgangspunkt) | exact |
| `agent/src/generate.py` (geändert) | service | request-response | sich selbst | exact |
| `agent/src/config.py` (geändert) | config/loader | CRUD (Datei-Read) | sich selbst | exact |
| `agent/src/main.py` (geändert) | controller (Polling-Loop) | event-driven | sich selbst | exact |
| `agent/pyproject.toml` (geändert) | config | — | sich selbst | exact |
| `agent/docker-compose.yml` (geändert) | config | — | sich selbst | exact |
| `webui/src/config_io.py` (geändert/abgelöst durch `agents_io.py`) | service | CRUD | sich selbst | exact |
| `webui/src/docker_ctrl.py` (geändert) | service (Docker-SDK-Wrapper) | event-driven | sich selbst | exact |
| `webui/src/state_reader.py` (geändert) | service (Ro-Reader) | CRUD (Read-only) | sich selbst | exact |
| `webui/src/main.py` (geändert) | controller (FastAPI-Routes) | request-response | sich selbst | exact |
| `webui/src/templates/index.html` + `_status_card.html` (geändert) | component (Jinja2/HTMX) | request-response | sich selbst | exact |
| `webui/docker-entrypoint.sh` (geändert) | config/bootstrap | file-I/O | sich selbst | exact |

## Pattern Assignments

### `agent/src/llm.py` (service, request-response)

**Analog:** `agent/src/classify.py` (Anthropic-Call-Shape, Logging) + `agent/src/provider_config.py` (Dispatch-über-Dict-Pattern) + `agent/src/config.py` (Env-Var-Default-Pattern für `MODEL_CLASSIFY`/`MODEL_DRAFT`)

**Bestehendes Anthropic-Call-Pattern** (`agent/src/classify.py` Zeilen 44-60, `agent/src/generate.py` Zeilen 73-79):
```python
client = client or Anthropic(api_key=config.anthropic_api_key)
response = client.messages.create(
    model=config.model_classify,
    max_tokens=20,
    temperature=0.0,
    messages=[{"role": "user", "content": prompt}],
)
text = response.content[0].text if response.content else ""
```
→ Wird zu einer der drei `_call_anthropic/_call_openai/_call_google`-Funktionen in `llm.py`, mit identischer Signatur (siehe RESEARCH.md "Primary Recommendation").

**Bestehendes Provider-Dispatch-Pattern** (`agent/src/provider_config.py` Zeilen 46-60, `resolve_imap_config`): Lookup über Dict + Fallback-Kette. Gleiches Idiom für `llm_call(provider, ...)`: Dict-Dispatch auf `_call_<provider>`, KeyError/unbekannter Provider → Fallback auf Anthropic-Default (analog zu `MODEL_DEFAULTS.get(provider, MODEL_DEFAULTS["anthropic"])` aus RESEARCH.md Zeile 160).

**Fehlerklassen-Logging-Pattern** (aus `classify.py` Zeilen 63-71, `generate.py` Zeilen 81-88) — beibehalten:
```python
logger.info(
    "classified",
    extra={"from": from_address, "subject": subject[:100], "classification": classification, "raw_response": text[:50]},
)
```
Wichtig laut RESEARCH.md Security-Domain: `api_key` NIE in `extra={...}` einbetten.

**Lazy-Import-Pattern** (RESEARCH.md Zeile 69, neu — kein direkter Codebase-Analog, aber konsistent mit bestehendem `from anthropic import Anthropic`-Modul-Top-Level-Import, den `classify.py`/`generate.py` heute nutzen — für die zwei neuen SDKs wird stattdessen **innerhalb** der `_call_openai`/`_call_google`-Funktion importiert):
```python
def _call_openai(prompt: str, model: str, max_tokens: int, temperature: float, api_key: str) -> str:
    from openai import OpenAI  # lazy import
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model, messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens, temperature=temperature,
    )
    return resp.choices[0].message.content or ""
```

**Integration in `classify.py`/`generate.py`** — Austausch-Pattern (NIEDRIG-Risiko laut RESEARCH.md Erweiterungspunkte-Tabelle): Die Zeilen `client = client or Anthropic(api_key=config.anthropic_api_key)` + `client.messages.create(...)` werden durch einen einzigen `llm.llm_call(...)`-Aufruf ersetzt; Rest der Funktion (Prompt-Bau via `.format()`, Logging, `_parse_response`) bleibt unverändert.

---

### `agent/src/crypto.py` + `webui/src/crypto.py` (utility, transform)

**Kein direkter 1:1-Analog** (Fernet ist neu im Projekt). Nächstliegendes bestehendes Muster ist `webui/src/auth.py` als "Secret-Handling im selben Projekt"-Referenz:

**Legacy-Klartext-Erkennung + graceful Migration** (`webui/src/auth.py` Zeilen 84-92, `_verify_password`):
```python
def _verify_password(candidate: str, stored: str) -> bool:
    if stored.startswith("$2a$") or stored.startswith("$2b$") or stored.startswith("$2y$"):
        try:
            return bcrypt.checkpw(candidate.encode("utf-8"), stored.encode("ascii"))
        except (ValueError, TypeError):
            return False
    # Legacy-Klartext (Migration): akzeptieren, aber warnen — nächster Save schreibt Hash.
    logger.warning("plaintext_password_in_env — bitte über WebUI-Formular neu setzen, dann wird gehasht gespeichert")
    return secrets.compare_digest(candidate.encode("utf-8"), stored.encode("utf-8"))
```
Dieses Prefix-Erkennungs-Idiom (`$2a$`/`$2b$`/`$2y$` als Marker für "bereits gehasht") ist exakt das Vorbild für `enc:`-Prefix-Erkennung in `crypto.is_encrypted()`/`decrypt_value()` — **Klartext ohne Prefix wird unverändert durchgereicht statt Fehler zu werfen**, identisch zur `_verify_password`-Fallback-Logik.

**chmod-600-Pattern** (bereits etabliert in `webui/src/config_io.py` Zeilen 64-67, `write_env`):
```python
try:
    os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
except PermissionError as e:
    logger.warning("chmod_failed", extra={"path": str(env_path), "error": str(e)})
```
→ 1:1 wiederverwendbar für `_load_or_create_key()` beim Anlegen von `/config/.secret_key` (siehe RESEARCH.md Code-Block Zeilen 202-213 — dort bereits mit identischem `try/except PermissionError: pass`-Idiom vorformuliert).

**Konkrete Modul-Vorlage:** Der vollständige `crypto.py`-Code (~35 LOC) ist bereits in RESEARCH.md Zeilen 187-239 lauffähig vorformuliert (inkl. `ENC_PREFIX`, `_load_or_create_key`, `encrypt_value`, `decrypt_value`, `is_encrypted`) — 1:1 in beide Services duplizieren (kein Shared-Import zwischen `agent/` und `webui/`, analog zur bestehenden Trennung, siehe `provider_config.py`, das ebenfalls nur in `agent/src/` existiert und nicht von `webui/` importiert wird).

**Fehlerklasse `DecryptionError`** (RESEARCH.md Zeile 249, Pitfall 5) — Vorbild für eigene Exception-Hierarchie ist bereits im Projekt etabliert: `agent/src/config.py` wirft ein simples `RuntimeError(f"Missing required env vars: ...")` (Zeile 79 in `config.py`), das der `_wait_for_config`-Loop in `main.py` (Zeilen 193-205) abfängt. Die neue `DecryptionError(RuntimeError)` muss NICHT von diesem `except RuntimeError`-Handler gefangen werden — hier ist ein gezielter Type-Check statt eines bloßen `except RuntimeError` nötig:
```python
# agent/src/main.py — _wait_for_config, Diff-Ansatz
while not _shutdown:
    try:
        return load_config()
    except DecryptionError:
        raise  # NICHT stillschweigend retry — sofort sichtbarer Fehler
    except RuntimeError as e:
        logger.info("waiting_for_config", extra={"reason": str(e), ...})
        ...
```

---

### `webui/src/agents_io.py` (service, CRUD — Ablösung/Erweiterung von `config_io.py`)

**Analog:** `webui/src/config_io.py` (komplett, alle Funktionen)

**Read-Masked-Pattern** (`config_io.py` Zeilen 19-25):
```python
def read_env_masked() -> dict[str, str]:
    env_path = Path(os.getenv("WEBUI_ENV_PATH", "/config/.env"))
    values = dotenv_values(env_path)
    return {
        k: (MASKED if k in SECRET_KEYS and v else v or "")
        for k, v in values.items()
    }
```
→ Wird zu `read_env_masked(agent_id: str)`, Pfad wird **nicht mehr aus Env-Var** sondern aus `agent_id` gebaut: `Path(f"/config/agents/{agent_id}/.env")`. `SECRET_KEYS` erweitert sich um `LLM_API_KEY` (ersetzt `ANTHROPIC_API_KEY`) — `WEBUI_PASSWORD` bleibt (globale Datei, siehe unten).

**Write-Env-Line-Parser-Pattern** (`config_io.py` Zeilen 35-67, `write_env`) — Kommentar-erhaltender Line-Parser bleibt strukturell unverändert, bekommt zusätzlich `agent_id`-Parameter UND den Encrypt-Hook vor dem Schreiben (siehe RESEARCH.md Zeile 241: "In `write_env(updates)` vor dem Line-Parser-Write: `IMAP_PASSWORD` und `LLM_API_KEY`-Werte ... durch `crypto.encrypt_value(...)` schicken").

**chmod-600 + Path-Traversal-Guard NEU:** Da `agent_id` jetzt Teil der Pfad-Konstruktion ist (anders als bisher, wo der Pfad rein aus Env-Var kam), MUSS laut RESEARCH.md Security-Domain (V5 Input Validation) vor jeder Pfadnutzung ein Whitelist-Check erfolgen:
```python
import re
AGENT_ID_PATTERN = re.compile(r"^[a-z0-9-]{1,64}$")

def _agent_dir(agent_id: str) -> Path:
    if not AGENT_ID_PATTERN.match(agent_id):
        raise ValueError(f"invalid agent_id: {agent_id!r}")
    return Path(f"/config/agents/{agent_id}")
```
Kein Analog im Bestandscode nötig — das ist reines neues Sicherheits-Gate, aber die `raise ValueError`-Konvention passt zu `docker_ctrl.control_agent()` (Zeile 56: `raise ValueError(f"invalid action: {action}")`).

**`get_missing_config()`-Pattern** (`config_io.py` Zeilen 84-91) bleibt strukturell gleich, nur `REQUIRED_ENV_KEYS` wird `ANTHROPIC_API_KEY` → `LLM_API_KEY` umbenannt, Funktion bekommt `agent_id`-Parameter.

**`reset_all()`-Pattern** (`config_io.py` Zeilen 98-119) ist die Vorlage für die Zwei-Stufen-Bestätigungs-Lösch-Funktion aus D-50 (Agent löschen = Config-Verzeichnis + Container + State entfernen):
```python
def reset_all() -> dict:
    result: dict[str, str] = {}
    ...
    if env_path.exists():
        env_path.write_text("", encoding="utf-8")
        result["env"] = "cleared"
    ...
    if state_db.exists():
        try:
            state_db.unlink()
            result["state_db"] = "deleted"
        except PermissionError as e:
            result["state_db_error"] = str(e)
    return result
```
→ `delete_agent(agent_id)` verwendet dasselbe Result-Dict-Muster, aber löscht das ganze `/config/agents/<id>/`-Verzeichnis (`shutil.rmtree`) statt einzelne Dateien zu leeren, UND ruft zusätzlich `docker_ctrl.stop_and_remove_agent(agent_id)` (analog zu `main.py` Route `/reset`, Zeile 254: `docker_ctrl.stop_and_remove_agent()` VOR `config_io.reset_all()`).

---

### `webui/src/docker_ctrl.py` (service, event-driven — Docker-SDK)

**Analog:** sich selbst (bestehende Single-Container-Funktionen als direkte Vorlage für die N-Container-Erweiterung)

**Bestehendes Get-Status-Pattern** (Zeilen 24-35, `get_agent_status`):
```python
def get_agent_status() -> dict:
    try:
        container = _get_client().containers.get(AGENT_CONTAINER_NAME)
        return {"state": container.status, "started_at": container.attrs["State"]["StartedAt"], "container_name": AGENT_CONTAINER_NAME}
    except NotFound:
        return {"state": "not_created", "started_at": None, "container_name": AGENT_CONTAINER_NAME}
    except APIError as e:
        return {"state": "error", "started_at": None, "container_name": AGENT_CONTAINER_NAME, "error": str(e)}
```
→ Wird zu `get_agent_status(agent_id: str)`, Container-Name wird `f"vizpatch-agent-{agent_id}"` statt Modul-Konstante `AGENT_CONTAINER_NAME`. Exakt dasselbe Try/Except-NotFound/APIError-Gerüst bleibt.

**Neue Self-Inspection- und Create-Funktionen:** Voll ausformulierter Code bereits in RESEARCH.md Zeilen 268-346 vorhanden (`_self_mounts`, `_resolve_mount_ref`, `create_or_replace_agent_container`, `list_agent_containers`) — direkt übernehmbar, folgt demselben `_get_client()`-Singleton-Pattern (Zeilen 17-21 im Bestandscode) und derselben Label-Konvention wie bereits für `container_name` genutzt.

**Update-Flow-Bruch (Pitfall 4):** Bestehender `pull_and_restart()` (Zeilen 79-108) endet mit Compose-Subprocess-Call:
```python
result = subprocess.run(["docker", "compose", "up", "-d", "agent"], cwd=COMPOSE_DIR, capture_output=True, text=True, check=False)
```
Dieser Teil MUSS ersetzt werden durch einen Loop über `list_agent_containers()` + `create_or_replace_agent_container(agent_id)` (siehe RESEARCH.md Zeile 356) — Rest der Funktion (Pull-Progress-Log-Sammlung Zeilen 82-89) bleibt unverändert als Vorbild für den Log-Aufbau.

**Test-Analog:** `webui/tests/test_docker_ctrl.py` — `_make_mock_container`-Helper (Zeilen 7-11) + `mocker.patch("docker.from_env", return_value=mock_client)`-Pattern (durchgängig in allen Tests) ist 1:1-Vorlage für neue Multi-Agent-Tests, inkl. `NotFound`-Import aus `docker.errors` (Zeile 4).

---

### `webui/src/state_reader.py` (service, Read-only CRUD)

**Analog:** sich selbst

**Bestehendes Env-Var-Default-Pfad-Pattern** (Zeilen 15, 26):
```python
path = Path(os.getenv("AGENT_STATUS_FILE", "/data/agent_status.json"))
...
db_path = Path(os.getenv("WEBUI_STATE_DB", "/data/state.db"))
```
→ Wird zu `Path(f"/data/agents/{agent_id}/agent_status.json")` bzw. `.../state.db"`. Das `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`-Read-Only-Öffnen (Zeile 31) bleibt exakt gleich — nur der Pfad wird `agent_id`-parametrisiert. Try/Except-Logging-Fallback (Zeilen 36-38, 20-22) bleibt identisches Idiom.

**Test-Analog:** `webui/tests/test_state_reader.py` (nicht vollständig gelesen, aber Namenskonvention/Fixture-Stil konsistent mit `test_config_io.py` — `tmp_path`/`monkeypatch.setenv`).

---

### `webui/src/main.py` (controller, request-response)

**Analog:** sich selbst

**Bestehendes Section-Save-HTMX-Response-Pattern** (Zeilen 155-163, `_save_response`):
```python
def _save_response(request: Request, is_htmx: bool, ok: bool, message: str, redirect_query: str) -> object:
    if is_htmx:
        css = "save-ok" if ok else "save-err"
        icon = "&#10003;" if ok else "&#9888;"
        return HTMLResponse(f'<span class="{css}">{icon} {message}</span>')
    from urllib.parse import quote
    return RedirectResponse(f"/?{redirect_query}={quote(message) if not ok else '1'}", status_code=303)
```
Bleibt unverändert als Rückgabe-Helper — wird von neuen Agent-CRUD-Routen (`POST /agents`, `POST /agents/{agent_id}/rename`, `POST /agents/{agent_id}/delete`) wiederverwendet.

**Bestehende Route-Struktur für Save + Action** (Zeilen 166-240 `save()`, 101-134 `agent_action()`) ist direkte Vorlage:
```python
@app.post("/agent/{action}", response_class=HTMLResponse)
def agent_action(request: Request, action: str, user: str = Depends(auth.require_auth)):
    if action not in ("start", "stop"):
        raise HTTPException(status_code=400, detail="invalid action")
    ...
```
→ Wird zu `@app.post("/agents/{agent_id}/{action}")`, mit zusätzlichem `agent_id`-Pfadparameter, der VOR jeder Weiterverwendung gegen das Slug-Whitelist-Pattern validiert wird (siehe `agents_io._agent_dir`-Guard oben).

**Index-Route-Datenaufbau** (Zeilen 55-86, `index()`) — bestehendes Muster: alle Lese-Calls (`config_io.read_env_masked()`, `docker_ctrl.get_agent_status()`, `state_reader.get_last_poll()`) werden in ein Template-Context-Dict gesammelt. → Wird erweitert um eine `agent_id`-Auswahl (Query-Param oder Session, siehe D-50) und eine `agents: list[str]`-Liste für das Dropdown (`agents_io.list_agent_ids()`, neue Funktion nach demselben Discovery-Prinzip wie `docker_ctrl.list_agent_containers()`).

**Rate-Limiting-Pattern** (Zeile 138, `@limiter.limit("10/minute")` auf `/context/generate`) — als Vorbild für ggf. neue Rate-Limits auf `/agents` (Create) falls der Plan das für nötig hält (kein Pflicht-Analog, aber konsistentes Idiom im selben File).

---

### `webui/src/templates/index.html` + `_status_card.html` (component, request-response)

**Analog:** sich selbst

**Bestehendes Section-Save-Fieldset-Muster** (`index.html` Zeilen 87-96, Anthropic-API-Fieldset):
```html
<fieldset>
  <legend>Anthropic API</legend>
  <p class="password-hint">&#9432; API-Key leer lassen um bestehenden Wert zu behalten. Neuen Wert eintragen um zu überschreiben.</p>
  <label for="anthropic_api_key">API-Key (ANTHROPIC_API_KEY)</label>
  <input type="password" id="anthropic_api_key" name="anthropic_api_key" value="" placeholder="**** (leer lassen = unverändert)">
  <div class="section-save">
    <button type="button" class="btn-section-save" hx-post="/save" hx-include="closest fieldset" hx-target="#save-msg-anthropic" hx-swap="innerHTML">Diesen Abschnitt übernehmen</button>
    <span id="save-msg-anthropic" class="save-inline-msg"></span>
  </div>
</fieldset>
```
→ Direkte Vorlage für das neue "LLM-API-Key"-Fieldset — **Addendum Revision 3 (D-51, 2026-07-16): KEIN `<select name="llm_provider">` mehr.** Stattdessen nur das generische `llm_api_key`-Passwort-Feld mit Label „API-Key (Anthropic / OpenAI / Google)", gleiches `hx-post="/save"`/`hx-include="closest fieldset"`-Idiom; der Provider wird serverseitig per `llm_detect.detect_llm_provider()` aus dem Key-Prefix erkannt und als `LLM_PROVIDER` mitgeschrieben. AVV-Hinweistext (LLM-04) als `<p class="hint">`, dynamisch zum ERKANNTEN Provider (Inline-Script mit demselben Prefix-Matching; siehe RESEARCH.md DSGVO-Tabelle).

**Status-Kachel-Liste** (`_status_card.html` komplett, 32 Zeilen) — bestehende EINE-Kachel-Struktur (`<div id="status-card" hx-get="/agent/status" hx-trigger="every 30s" hx-swap="outerHTML">`) wird zur Vorlage für `{% for agent in agents %}`-Schleife (Specifics-Abschnitt CONTEXT.md: "Status-Bereich: eine Status-Kachel pro Agent (Liste)"). Buttons-Pattern (Zeilen 28-31) bleibt pro Kachel identisch, nur `hx-post="/agent/start"` → `hx-post="/agents/{{ agent.id }}/start"`.

**Neues Agent-Dropdown (D-50):** Kein Analog im Bestandscode (aktuell nur ein einzelnes Formular ohne Auswahl) — orientiert sich am bestehenden `<select>`-losen HTMX-Partial-Reload-Muster: `hx-get`/`hx-target` auf das gesamte Formular-`<div>`, analog zum bestehenden `_status_card.html`-Polling-Reload-Mechanismus (`hx-trigger="every 30s" hx-swap="outerHTML"` als Vorbild für "wechsle Agent → lade Partial neu").

---

### `agent/src/config.py` (config/loader, CRUD)

**Analog:** sich selbst

**Bestehendes Required-Vars + Decrypt-Einfügepunkt** (Zeilen 13-18, 77-79, 120):
```python
REQUIRED_ENV_VARS = ["IMAP_USER", "IMAP_PASSWORD", "OWN_EMAIL_ADDRESS", "ANTHROPIC_API_KEY"]
...
missing = [k for k in REQUIRED_ENV_VARS if not os.getenv(k)]
if missing:
    raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")
...
anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
```
→ `ANTHROPIC_API_KEY` → `LLM_API_KEY` (Rename in `REQUIRED_ENV_VARS` + Dataclass-Feld), Decrypt-Call direkt nach `os.environ[...]`-Zugriff einfügen (siehe RESEARCH.md Zeilen 243-248). Neues Dataclass-Feld `llm_provider: str = os.getenv("LLM_PROVIDER", "anthropic")`.

**Bestehendes Env-Var-Default-Pattern für Modell-IDs** (Zeilen 121-122) bleibt strukturell erhalten, wird nur um Provider-Abhängigkeit erweitert (RESEARCH.md `MODEL_DEFAULTS`-Dict-Code Zeilen 154-163) — identisches `os.getenv("MODEL_CLASSIFY", <default>)`-Idiom, nur `<default>` wird jetzt provider-abhängig aus dem Dict gezogen statt hartkodiert.

**Bereits vorhandene Pfad-Overrides (KEINE Änderung nötig):** `context_file`, `state_db` (Zeilen 98-100) sind bereits Env-Var-basiert (`CONTEXT_FILE`, `STATE_DB`) — genau diese vier Variablen (`AGENT_ENV_FILE`, `CONTEXT_FILE`, `STATE_DB`, `AGENT_STATUS_FILE`) werden von `docker_ctrl.create_or_replace_agent_container()` pro Agent unterschiedlich gesetzt (siehe RESEARCH.md Zeile 348). Wichtiger Hinweis für den Planner: **hier ist explizit KEIN Pfad-Code-Diff nötig**, nur Doku im Plan.

---

### Tests

**`agent/tests/test_llm.py`** — Analog `agent/tests/test_classify.py` (komplett gelesen). Fixture-Nutzungs-Pattern:
```python
def test_classify_customer_question_returns_reply_needed(mock_config, mock_anthropic_classify_reply_needed):
    result = classify_email(..., config=mock_config, client=mock_anthropic_classify_reply_needed)
    assert result == "REPLY_NEEDED"
```
→ Neue Tests für `llm.llm_call(provider="openai", ...)` etc. mocken `OpenAI`/`genai.Client` analog über `mocker.patch(...)` (Pattern aus `webui/tests/test_docker_ctrl.py`, `mocker.patch("docker.from_env", return_value=mock_client)`), da `agent/tests/conftest.py` bereits `mock_config`/`mock_anthropic_*`-Fixtures für Anthropic bereitstellt (siehe `agent/tests/conftest.py`, nicht vollständig gelesen aber referenziert in `test_classify.py`/`test_generate.py`).

**`webui/tests/test_crypto.py`, `test_agents_io.py`** — Analog `webui/tests/test_config_io.py` (komplett gelesen). Kern-Idiom: `tmp_path` + `monkeypatch.setenv(...)` + `import src.config_io as config_io` (Re-Import nach Env-Var-Setzen, da Modul-Level-Konstanten sonst gecacht wären):
```python
def test_write_env_chmod_600(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("IMAP_USER=u@x.de\n", encoding="utf-8")
    monkeypatch.setenv("WEBUI_ENV_PATH", str(env_file))
    import src.config_io as config_io
    config_io.write_env({"IMAP_USER": "new@x.de"})
    mode = os.stat(env_file).st_mode & 0o777
    assert mode == 0o600
```
Der `@pytest.mark.skipif(sys.platform == "win32", ...)`-Guard (Zeile 61) ist wichtig für neue chmod-Tests in `crypto.py` (Windows-Dev-Umgebung des Nutzers, siehe `env`-Hinweis Windows 11).

**`webui/tests/test_docker_ctrl_multi_agent.py`** — Analog `webui/tests/test_docker_ctrl.py` komplett. `_make_mock_container`-Helper + `mocker.patch("docker.from_env", ...)` 1:1 wiederverwendbar; neue Tests für `create_or_replace_agent_container`/`list_agent_containers`/Self-Inspection brauchen zusätzlich einen gemockten `client.containers.get(socket.gethostname())`-Call mit `attrs["Mounts"]`-Fixture-Daten.

---

## Shared Patterns

### Secret-Masking bei Anzeige
**Quelle:** `webui/src/config_io.py` Zeilen 8-9, 19-25 (`MASKED = "****"`, `SECRET_KEYS`)
**Anwenden auf:** `agents_io.py` (ersetzt `config_io.py`), alle Save-Routen in `main.py`
```python
MASKED = "****"
SECRET_KEYS = {"IMAP_PASSWORD", "ANTHROPIC_API_KEY", "WEBUI_PASSWORD"}  # → LLM_API_KEY statt ANTHROPIC_API_KEY
```
**Wichtig (RESEARCH.md Zeile 241):** Maskierung erfolgt IMMER unabhängig davon ob der `.env`-Wert bereits `enc:`-verschlüsselt ist oder noch Klartext-Legacy — kein Decrypt beim reinen Anzeigen nötig, das minimiert `InvalidToken`-Risiko beim Rendern.

### chmod-600-Pattern für Secret-Dateien
**Quelle:** `webui/src/config_io.py` Zeilen 64-67 (`write_env`)
**Anwenden auf:** `crypto.py` (beide Services) für `/config/.secret_key`, `agents_io.write_env()` für alle Agent-`.env`-Dateien
```python
try:
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
except PermissionError as e:
    logger.warning("chmod_failed", extra={"path": str(path), "error": str(e)})
```

### Try/Except-NotFound/APIError-Gerüst für Docker-SDK-Calls
**Quelle:** `webui/src/docker_ctrl.py` Zeilen 24-51 (`get_agent_status`, `stop_and_remove_agent`)
**Anwenden auf:** Alle neuen Multi-Container-Funktionen (`create_or_replace_agent_container`, `list_agent_containers`)
```python
try:
    container = _get_client().containers.get(AGENT_CONTAINER_NAME)
except NotFound:
    return {"state": "not_created", ...}
except APIError as e:
    return {"state": "error", ..., "error": str(e)}
```

### Line-Parser-basiertes `.env`-Schreiben (Kommentar-erhaltend)
**Quelle:** `webui/src/config_io.py` Zeilen 35-67 (`write_env`)
**Anwenden auf:** `agents_io.write_env(agent_id, updates)`, Migration-Modul (Key-Rename `ANTHROPIC_API_KEY`→`LLM_API_KEY` MUSS über denselben Line-Parser laufen, NICHT über `dotenv.set_key`, siehe RESEARCH.md Zeile 378: "per Line-Parser ... NICHT `dotenv.set_key` — Kommentare bleiben erhalten").

### HTMX Section-Save-Idiom
**Quelle:** `webui/src/templates/index.html` (jedes `<fieldset>`, z. B. Zeilen 92-95) + `webui/src/main.py` Zeilen 155-163 (`_save_response`)
**Anwenden auf:** Neues LLM-Provider-Fieldset, neues Agent-Verwaltungs-Fieldset
```html
<div class="section-save">
  <button type="button" class="btn-section-save" hx-post="/save" hx-include="closest fieldset" hx-target="#save-msg-X" hx-swap="innerHTML">Diesen Abschnitt übernehmen</button>
  <span id="save-msg-X" class="save-inline-msg"></span>
</div>
```

### Auth-Dependency auf allen Routen
**Quelle:** `webui/src/auth.py` `require_auth` + Verwendung in `webui/src/main.py` (jede Route: `user: str = Depends(auth.require_auth)`)
**Anwenden auf:** Alle neuen `/agents/*`-Routen — keine Ausnahme, exakt gleiches Dependency-Pattern wie bestehende Routen.

### Test-Fixture-Idiom `tmp_path` + `monkeypatch.setenv` + Re-Import
**Quelle:** `webui/tests/test_config_io.py` (durchgängig, z. B. Zeilen 8-21)
**Anwenden auf:** Alle neuen WebUI-Tests (`test_crypto.py`, `test_agents_io.py`, `test_migration.py`)

---

## No Analog Found

Dateien ohne engen Bestandscode-Match (Planner soll hier stärker auf RESEARCH.md-Codebeispiele zurückgreifen):

| Datei | Rolle | Data Flow | Grund |
|---|---|---|---|
| `agent/src/crypto.py` / `webui/src/crypto.py` | utility | transform | Keine Fernet-/Verschlüsselungslogik existiert bisher im Projekt — `auth.py` (bcrypt) ist nur strukturelles Vorbild (Prefix-Erkennung, Legacy-Fallback), nicht funktional identisch. Vollständiger Code bereits in RESEARCH.md Zeilen 187-239 vorformuliert. |
| `webui/src/migration.py` (Startup-Hook) | service | batch/file-I/O | Kein bestehender "verschiebe alte Struktur in neue"-Code im Projekt; `docker-entrypoint.sh` deckt nur Zero-Config-Seeding (Datei-Anlegen), nicht Datei-Migration ab. Ablauf ist in RESEARCH.md Zeilen 371-385 Schritt-für-Schritt vorgegeben. |
| Docker-SDK Self-Inspection (`_self_mounts`, `_resolve_mount_ref`) | utility (Teil von `docker_ctrl.py`) | event-driven | Neues Docker-API-Muster (`client.containers.get(socket.gethostname())`), kein Vorläufer im Bestandscode — vollständig in RESEARCH.md Zeilen 268-285 vorformuliert, MEDIUM-Confidence laut Assumptions Log A3. |

## Metadata

**Analog-Suchbereich:** `agent/src/*`, `agent/tests/*`, `webui/src/*`, `webui/src/templates/*`, `webui/tests/*`, `agent/pyproject.toml`, `webui/pyproject.toml`, `agent/docker-compose.yml`, `webui/docker-entrypoint.sh`
**Gescannte Dateien:** ~28 (alle in `agent/src/`, `webui/src/`, Templates, ausgewählte Tests je Kategorie)
**Pattern-Extraktionsdatum:** 2026-07-15
