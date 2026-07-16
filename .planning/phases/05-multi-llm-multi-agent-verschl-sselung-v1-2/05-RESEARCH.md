# Phase 5: Multi-LLM, Multi-Agent & Verschlüsselung (v1.2) — Research

> ## ⚠ Addendum 2026-07-16 — Architektur-Korrektur (neues D-46)
>
> Der Nutzer hat "ein Container pro Agent" ausdrücklich abgelehnt. Neues D-46 (siehe 05-CONTEXT.md):
> **EIN Agent-Container** (bestehender Compose-Service) mit **Multi-Account-Poll-Loop** und
> **Aktiv-Flag `AGENT_ENABLED`** pro Agent. Damit sind folgende Abschnitte dieses Dokuments **OBSOLET
> und dürfen NICHT mehr referenziert werden**:
>
> - Sektion "Docker-SDK: dynamische Agent-Container (MA-01…05)" komplett (Self-Inspection,
>   `_self_mounts`/`_resolve_mount_ref`, `create_or_replace_agent_container`, `list_agent_containers`,
>   Labels `vizpatch.managed`/`vizpatch.agent-id`)
> - "Kollision mit Compose-verwaltetem agent-Service — Empfehlung: entfernen" (der Service BLEIBT)
> - "Update-Flow muss umgebaut werden" (Update bleibt Compose-basiert wie Phase 4)
> - Migrations-Schritte 5+6 (alten Container stoppen / neuen SDK-Container erzeugen) — Migration ist
>   jetzt docker-frei; stattdessen wird `AGENT_ENABLED=true` in `agents/default/.env` gesetzt
> - Pitfalls 1 (Volume-Namespacing) und 4 (pull_and_restart-Umbau) sowie Assumptions A3/A5
>
> **Weiterhin gültig:** LLM-SDKs/Modell-Defaults, Fernet-Sektion, DSGVO/AVV-Tabelle, Pitfalls 2/3/5/6/7,
> Erweiterungspunkte-Tabelle für webui (config_io/state_reader/main.py/Templates), Migrations-Schritte 1–4
> inkl. Backup. Die Env-Var-Overrides (`AGENT_ENV_FILE`, `CONTEXT_FILE`, `STATE_DB`, `AGENT_STATUS_FILE`)
> werden nicht mehr per Container gesetzt, sondern als loop-interne Parameter genutzt: `load_agent_config
> (agent_id, agent_dir)` liest via `dotenv_values` (KEINE os.environ-Mutation) und leitet Pfade aus
> agent_id/agent_dir ab (siehe Plan 05.02-agent-multi-account-loop).


**Researched:** 2026-07-15
**Domain:** Multi-Provider-LLM-Adapter (Anthropic/OpenAI/Google) + dynamische Docker-SDK-Container-Orchestrierung + Fernet-Secrets-Verschlüsselung + Config/State-Migration
**Confidence:** MEDIUM-HIGH (Stack/Crypto/Docker-SDK-Patterns HIGH verifiziert; LLM-Modell-IDs für OpenAI/Google LOW-MEDIUM — Web-Recherche zu aktuellen Modellnamen liefert widersprüchliche Ergebnisse, siehe Assumptions Log)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-46 — Ein Container pro Agent:** Agent-Code bleibt Single-Account. WebUI orchestriert pro gespeichertem Agenten einen eigenen Container `vizpatch-agent-<agent-id>` via Docker-SDK. `restart_policy: unless-stopped` via SDK, Container-Labels (`vizpatch.agent-id=<id>`) für Zuordnung und Aufräumen.

**D-47 — Config-Layout `/config/agents/<agent-id>/`:** Pro Agent ein Verzeichnis mit eigener `.env` + `context.md`. Agent-ID ist ein Slug (aus Name oder E-Mail-Adresse abgeleitet, kollisionssicher). Beim ersten Start der neuen WebUI wird ein vorhandenes Single-Agent-Layout (`/config/.env` + `/config/context.md`) automatisch und verlustfrei als Agent `default` migriert. State analog unter `/data/agents/<agent-id>/` (SQLite `state.db` + `agent_status.json`).

**D-48 — Fernet + Key-Datei, kein Master-Passwort:** Symmetrische Verschlüsselung mit `cryptography.fernet`. Secret-Werte stehen als `enc:<token>` in der `.env`. Key-Datei (z. B. `/config/.secret_key`) wird beim ersten Start generiert, `chmod 600`, liegt im selben Config-Bind-Mount. WebUI verschlüsselt beim Save, Agent entschlüsselt beim Config-Load. Klartext-Legacy-Werte werden erkannt und beim nächsten Save verschlüsselt. Kein Master-Passwort-Prompt.

**D-49 — LLM-Provider pro Agent, Modell-Defaults hart verdrahtet:** `LLM_PROVIDER` + `LLM_API_KEY` sind Felder der Agent-`.env` (pro Agent unabhängig). Kein Modell-Auswahlfeld im UI — pro Provider ein fest verdrahtetes Classify+Draft-Modellpaar (Anthropic → Haiku 4.5 / Sonnet 4.6; OpenAI/Google-Äquivalente im Research verifizieren). Adapter-Modul im Agent (`llm.py` o. ä.), `classify.py`/`generate.py` rufen nur noch den Adapter.

**D-50 — Dropdown-Semantik:** Agent-Dropdown leer bei frischer Installation → Formular startet im "Neuen Agent anlegen"-Modus. Auswahl eines Agenten lädt dessen Formular (HTMX, ohne Full-Reload passend zum Section-Save-Muster). Löschen mit Zwei-Stufen-Bestätigung (wie Zero-Reset aus UI-08) entfernt Config-Verzeichnis, Container und State.

### Claude's Discretion
- Exakte Slug-Regeln für Agent-IDs, Kollisionshandling
- HTMX-Detailverhalten (Partial-Templates, Reload-Grenzen) beim Agent-Wechsel
- Aufteilung/Benennung der neuen Module (z. B. `agent/src/llm.py`, `webui/src/agents_io.py`, `webui/src/crypto.py`)
- Wie der Agent-Container sein Config-Verzeichnis erhält (Bind-Mount-Subpfad vs. Env-Var `AGENT_ID` + gemeinsamer Mount) — im Research geklärt, siehe Sektion "Docker-SDK: dynamische Agent-Container"
- Umgang mit WebUI-eigenen Einstellungen (Login-Hash bleibt global in `/config/.env` oder eigener Datei)
- Fehlerbilder bei ungültigem/fehlendem Key (Key gelöscht, `.env` noch verschlüsselt): klare Fehlermeldung + Reset-Pfad

### Specifics (aus dem Auftrag)
- Dropdown-Reihenfolge Provider: Anthropic (Default) | OpenAI | Google
- `enc:`-Prefix als Erkennungsmerkmal verschlüsselter Werte (Klartext ohne Prefix = Legacy, wird migriert)
- AVV-Hinweistext im WebUI abhängig vom gewählten Provider (ein Satz, kein Rechtstext)
- Status-Bereich: eine Status-Kachel pro Agent (Liste), nicht nur eine globale
- `install-autostart.sh`/systemd muss weiterhin funktionieren — WebUI-Container startet via Compose, Agent-Container hängen an Docker-`restart_policy` (überleben Reboot ohne systemd-Änderung; im Research verifiziert)

### Deferred Ideas (OUT OF SCOPE)
- Modell-Auswahl pro Agent im UI (v2)
- Azure-OpenAI-/Mistral-/Ollama-Support (v2)
- Master-Passwort / Hardware-Key für Secrets (v2, bricht Zero-Config)
- Multi-Tenant (Logins pro Kunde, Mandanten-Trennung) — bleibt out of scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Beschreibung | Research-Support |
|----|-------------|-------------------|
| LLM-01 | `LLM_PROVIDER`-Dropdown + generisches `LLM_API_KEY`-Feld | Sektion "LLM-Adapter", Formular-Erweiterung in "Bestehende Struktur" |
| LLM-02 | Interner `llm_call(...)`-Adapter, `classify.py`/`generate.py` nutzen nur noch Adapter | Sektion "LLM-Adapter" mit lauffähigem Code |
| LLM-03 | Hart verdrahtete Modell-Defaults pro Provider | Sektion "LLM-SDKs & Modell-Defaults" — Anthropic HIGH, OpenAI/Google LOW-MEDIUM (Assumptions Log A1/A2) |
| LLM-04 | Pre-Deployment-Fixtures je Provider erneut durchlaufen, AVV-Hinweis | Sektion "DSGVO/AVV je Provider" |
| MA-01 | Config-Layout `/config/agents/<id>/`, Migration Single→`default` | Sektion "Migration Single-Agent → `agents/default`", "Runtime State Inventory" |
| MA-02 | Agent-Dropdown, Anlegen/Umbenennen/Löschen | Sektion "Bestehende Struktur: Erweiterungspunkte" |
| MA-03 | Ein Container pro Agent via Docker-SDK | Sektion "Docker-SDK: dynamische Agent-Container" |
| MA-04 | Getrennter State pro Agent | Sektion "Docker-SDK: dynamische Agent-Container" (Env-Var-Routing STATE_DB/AGENT_STATUS_FILE) |
| MA-05 | Paralleler Betrieb, keine Cross-Kontamination | Sektion "Docker-SDK: dynamische Agent-Container" + "Common Pitfalls" |
| SEC-01 | Fernet-Verschlüsselung, `enc:`-Prefix, Key-Datei | Sektion "Fernet-Verschlüsselung" |
| SEC-02 | Transparente Ver-/Entschlüsselung, sanfte Legacy-Migration | Sektion "Fernet-Verschlüsselung" + Code-Beispiel `crypto.py` |
| SEC-03 | Key-Handling dokumentiert, Schutzumfang ehrlich | Sektion "Fernet-Verschlüsselung: Schutzumfang" |
</phase_requirements>

## Summary

Diese Phase ist überwiegend eine **Orchestrierungs- und Adapter-Aufgabe**, kein Rewrite. Drei weitgehend unabhängige Bausteine kommen zusammen: (1) ein dünner LLM-Adapter im Agent-Code, der die bestehenden Single-Prompt-Aufrufe (`classify.py`/`generate.py` senden heute je einen kompletten Prompt-String als einzige User-Message an Anthropic) auf drei SDKs routet — `anthropic` (bereits im Einsatz), `openai` (aktuell 2.45.0) und `google-genai` (aktuell 2.11.0); (2) eine Fernet-Verschlüsselungsschicht (`cryptography` 49.0.0) für zwei Secret-Felder in der `.env`, mit einer einzigen globalen Key-Datei unter `/config/.secret_key`, die für alle Agenten gemeinsam gilt; (3) eine Docker-SDK-Erweiterung, die aus dem laufenden `webui`-Container heraus beliebig viele `vizpatch-agent-<id>`-Container erzeugt — der Schlüssel-Trick dafür ist **Self-Inspection**: der `webui`-Container liest seine eigenen `Mounts` (`/config`, `/data`, `/app/prompts`) über die Docker-API aus, um die tatsächlichen Host-Pfade (bei Bind-Mounts) bzw. Volume-Namen (bei Named Volumes) zu ermitteln, und reicht **exakt dieselben** Mounts an jeden neuen Agent-Container weiter. Die Pfad-Differenzierung zwischen Agenten passiert NICHT über unterschiedliche Mounts, sondern über vier bereits vorhandene, überschreibbare Env-Vars im Agent (`AGENT_ENV_FILE`, `CONTEXT_FILE`, `STATE_DB`, `AGENT_STATUS_FILE`) — dadurch sind an `agent/src/config.py` **keine Pfad-Änderungen nötig**, nur der neue LLM-Adapter und die Fernet-Entschlüsselung beim Load.

Die größte Unsicherheit liegt NICHT in der Architektur, sondern in den **konkreten Modell-ID-Strings für OpenAI und Google** (LLM-03). Web-Recherche zu "aktuellen" Modellnamen für Juli 2026 lieferte für OpenAI widersprüchliche/spekulativ wirkende Ergebnisse (Codenamen "Sol/Terra/Luna" für GPT-5.6-Varianten, teils nur auf Preisvergleichs-Aggregator-Seiten belegt, nicht konsistent auf offiziellen OpenAI-Docs-Seiten). Für Google ist die Lage klarer (offizielle `ai.google.dev`-Doku bestätigt `gemini-2.5-flash-lite` und `gemini-2.5-pro` mit Code-Beispielen), aber auch dort tauchen bereits `gemini-3.x`-Referenzen auf. **Empfehlung:** Modell-Defaults als Konstante in `llm.py` hart verdrahten (erfüllt D-49), aber zusätzlich über die bereits existierenden Env-Var-Overrides `MODEL_CLASSIFY`/`MODEL_DRAFT` korrigierbar halten (kein UI, nur `.env`) — und vor dem produktiven LLM-04-Fixture-Durchlauf einen echten `client.models.list()`-Check pro Provider als Verifikations-Task einplanen, bevor die Modell-IDs final eingefroren werden.

**Primary Recommendation:** Baue `llm.py` als reinen Dispatcher mit drei privaten `_call_<provider>()`-Funktionen, alle mit identischer Signatur (`prompt: str, model: str, max_tokens: int, temperature: float, api_key: str) -> str`). Halte die drei Provider-SDKs als **lazy imports** innerhalb der jeweiligen `_call_*`-Funktion (nicht Modul-Top-Level), damit ein Kunde, der nur Anthropic nutzt, keine ungenutzten SDK-Importfehler riskiert und das Docker-Image nur die tatsächlich installierten Pakete lädt (alle drei sind aber ohnehin im `pyproject.toml` als harte Deps vorgesehen, da Kunden den Provider jederzeit per WebUI wechseln können).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| LLM-Provider-Auswahl (Dropdown) | Frontend-Server (WebUI-Formular) | — | Reines Config-Feld, kein Runtime-Verhalten in der WebUI selbst |
| LLM-Call-Routing (`llm_call`) | Agent-Container (`agent/src/llm.py`) | — | Läuft im Agent-Prozess, nicht in der WebUI — WebUI kennt nur `LLM_PROVIDER`-String, ruft nie selbst OpenAI/Google auf (Ausnahme: `llm_seed.py` bleibt fest auf Anthropic Sonnet, siehe Pitfall 6) |
| Secrets-Verschlüsselung (Encrypt beim Save) | Frontend-Server (WebUI `crypto.py`) | — | Nur WebUI schreibt `.env`, also nur WebUI verschlüsselt |
| Secrets-Entschlüsselung (Decrypt beim Load) | Agent-Container (`agent/src/crypto.py`, dupliziertes Mini-Modul) | Frontend-Server (WebUI liest zur Anzeige/Masking auch, aber zeigt nie Klartext) | Agent braucht Klartext für SDK-Calls; WebUI braucht nur Boolean "ist gesetzt" |
| Container-Lifecycle (Create/Start/Stop/Remove pro Agent) | Frontend-Server (WebUI `docker_ctrl.py` via Docker-Socket) | Host (Docker-Daemon) | Bereits etablierter Tier aus Phase 4, jetzt N-fach statt 1-fach |
| Config-/State-Migration (Single→`agents/default`) | Frontend-Server (WebUI-Startup-Hook, analog `docker-entrypoint.sh`) | — | Einmaliger, idempotenter Schritt beim WebUI-Boot, bevor die erste Anfrage bedient wird |
| Persistenter State pro Agent | Named Volume `agent-data` (voll gemountet, Pfad-Trennung via Env-Var) | — | Kein Kubernetes-artiges Subpath-Mounting nötig — Docker kennt das nicht, daher Trennung auf Anwendungsebene |

## LLM-SDKs & Modell-Defaults

### Verifizierte SDK-Versionen (PyPI, 2026-07-15, via `slopcheck` [OK] für alle 5 Pakete)

| Paket | Version | Registry-Alter | slopcheck | Zweck |
|-------|---------|----------------|-----------|-------|
| `anthropic` | 0.116.0 [VERIFIED: PyPI + bereits produktiv im Projekt] | mehrjährig, aktiv gepflegt | OK | bereits im Einsatz, Model-IDs `claude-haiku-4-5`/`claude-sonnet-4-6` bleiben unverändert (Produktionscode) |
| `openai` | 2.45.0 [VERIFIED: PyPI-Registry, offizielle Docs-Domain `developers.openai.com`] | offizielles SDK, mehrjährig | OK | Chat-Completions- und Responses-API |
| `google-genai` | 2.11.0 [VERIFIED: PyPI-Registry + offizielles GitHub `googleapis/python-genai`] | offizielles SDK (Nachfolger von `google-generativeai`) | OK | Gemini-API-Zugriff |
| `cryptography` | 49.0.0 [VERIFIED: PyPI-Registry, offizielle Docs `cryptography.io`] | Kern-Python-Sicherheitspaket, seit >10 Jahren | OK | Fernet-Verschlüsselung |
| `docker` | 7.2.0 [VERIFIED: bereits im Projekt seit Phase 4] | — | OK | bereits im Einsatz, keine Änderung nötig |

**Wichtig zum Paketnamen `google-genai`:** Das ist das aktuelle, offizielle Google-SDK (Nachfolger des älteren, mittlerweile in Wartungsmodus befindlichen `google-generativeai`). Import-Pfad ist `from google import genai` (Namespace-Package `google.*`), NICHT `import google_genai`. Verwechslungsgefahr mit dem alten Paket ist eine bekannte Stolperfalle (siehe Common Pitfalls).

### Call-Pattern pro Provider (verifiziert via offizielle Docs/GitHub-READMEs)

**Anthropic** (Bestandscode, unverändert — Referenz `agent/src/classify.py`/`generate.py`):
```python
from anthropic import Anthropic
client = Anthropic(api_key=api_key)
msg = client.messages.create(
    model=model, max_tokens=max_tokens, temperature=temperature,
    messages=[{"role": "user", "content": prompt}],
)
text = "".join(b.text for b in msg.content if b.type == "text")
```
Fehlerklassen: `anthropic.APIError` (Basis), `anthropic.RateLimitError`, `anthropic.APIConnectionError`.

**OpenAI** [CITED: github.com/openai/openai-python] — Chat-Completions-API bleibt unterstützt (bestätigt in offiziellem README), einfacher direkter Ersatz für das bestehende Single-Prompt-Pattern:
```python
from openai import OpenAI
client = OpenAI(api_key=api_key)
resp = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    max_tokens=max_tokens,
    temperature=temperature,
)
text = resp.choices[0].message.content or ""
```
Fehlerklassen (alle von `openai.APIError` abgeleitet): `openai.APIConnectionError`, `openai.RateLimitError` (HTTP 429), `openai.APIStatusError` (sonstige 4xx/5xx), `openai.APITimeoutError`.

**Google Gemini** [CITED: github.com/googleapis/python-genai, ai.google.dev/gemini-api/docs/models]:
```python
from google import genai
from google.genai import types
client = genai.Client(api_key=api_key)
resp = client.models.generate_content(
    model=model,
    contents=prompt,
    config=types.GenerateContentConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
    ),
)
text = resp.text or ""
```
Fehlerklassen: `google.genai.errors.APIError` mit `.code` (HTTP-Status) und `.message`.

**Design-Entscheidung (alle 3 Provider einheitlich):** Da die bestehenden Prompt-Templates (`classify.txt`, `generate.txt`) EIN zusammenhängender Text-Block sind (keine System/User-Trennung, siehe gelesener Inhalt der beiden Dateien), wird für alle drei Provider **eine einzige User-Message** ohne System-Prompt gesendet. Das minimiert den Diff — keine Prompt-Datei-Änderung nötig, nur der Transport wechselt.

### Modell-Defaults — Confidence-Bewertung

| Provider | Classify (schnell/billig) | Draft (Qualität) | Confidence | Quelle |
|----------|---------------------------|-------------------|------------|--------|
| Anthropic | `claude-haiku-4-5` | `claude-sonnet-4-6` | HIGH | bereits produktiv, unverändert (agent/src/config.py Zeilen 121-122) |
| OpenAI | `gpt-5-mini` | `gpt-5.4` | LOW-MEDIUM [ASSUMED] | `gpt-5-mini` hat eine eigene offizielle Docs-Seite (`developers.openai.com/api/docs/models/gpt-5-mini`, in Suchergebnissen bestätigt) — `gpt-5.4` als Draft-Modell ist eine plausible, aber NICHT durch eine offizielle Docs-Seite direkt bestätigte Wahl. Konkurrierende Recherche-Ergebnisse nennen eine "GPT-5.6"-Familie mit Codenamen "Sol/Terra/Luna" — deren tatsächliche API-Model-ID-Strings blieben in der Recherche uneinheitlich (teils `gpt-5.6-sol`, teils Alias `gpt-5.6`). **Siehe Assumptions Log A1 — MUSS vor Produktiv-Einsatz per `client.models.list()` verifiziert werden.** |
| Google | `gemini-2.5-flash-lite` | `gemini-2.5-pro` | MEDIUM-HIGH | [CITED: ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite mit Code-Beispiel]. Eine neuere `gemini-3.x`-Familie existiert laut Recherche bereits parallel — 2.5er-Reihe ist aber als "Stable" dokumentiert und low-risk. **Siehe Assumptions Log A2.** |

**Resilienz-Empfehlung:** `agent/src/config.py` liest Modell-IDs bereits heute über `os.getenv("MODEL_CLASSIFY", <default>)` — dieses Muster bleibt erhalten und wird nur um Provider-Abhängigkeit des Defaults erweitert:
```python
MODEL_DEFAULTS = {
    "anthropic": {"classify": "claude-haiku-4-5", "draft": "claude-sonnet-4-6"},
    "openai":    {"classify": "gpt-5-mini",         "draft": "gpt-5.4"},
    "google":    {"classify": "gemini-2.5-flash-lite", "draft": "gemini-2.5-pro"},
}
provider = os.getenv("LLM_PROVIDER", "anthropic").strip().lower()
defaults = MODEL_DEFAULTS.get(provider, MODEL_DEFAULTS["anthropic"])
model_classify = os.getenv("MODEL_CLASSIFY", defaults["classify"])
model_draft = os.getenv("MODEL_DRAFT", defaults["draft"])
```
Das erfüllt D-49 (kein UI-Feld) und lässt trotzdem eine Notfall-Korrektur per `.env`-Handbearbeitung zu, falls sich ein Modell-Name als ungültig herausstellt (ohne Code-Redeploy).

### DSGVO/AVV-Hinweistext je Provider (LLM-04)

| Provider | Ein-Satz-Hinweis für WebUI | Confidence |
|----------|----------------------------|------------|
| Anthropic | "Für Anthropic ist ein Auftragsverarbeitungsvertrag (AVV) nötig; nach Möglichkeit Zero-Data-Retention mit Anthropic vereinbaren." | HIGH — bereits Projekt-Praxis (CLAUDE.md Punkt 4/5) |
| OpenAI | "Für OpenAI ist ein Data Processing Addendum (DPA) über den OpenAI-Account abzuschließen; API-Daten werden standardmäßig bis zu 30 Tage zur Missbrauchserkennung gespeichert, echte Zero-Data-Retention ist nur für qualifizierte Enterprise-Accounts verfügbar." | MEDIUM [CITED: openai.com/policies/data-processing-addendum, openai.com/enterprise-privacy] |
| Google | "Für Google Gemini ist ein AVV/DPA nötig; **nur der kostenpflichtige API-Tier** garantiert, dass Prompts nicht zu Trainingszwecken verwendet werden — der kostenlose AI-Studio-Tier tut dies NICHT." | MEDIUM [CITED: ai.google.dev/gemini-api/terms, ai.google.dev/gemini-api/docs/logs-policy] — **wichtig für die Doku: Betreiber muss zwingend den bezahlten API-Key nutzen, nicht den kostenlosen AI-Studio-Key** |

Diese drei Sätze sind Kurzhinweise für die UI, kein Rechtstext — Formulierung im Plan ggf. von Vizionists final abgestimmt.

## Fernet-Verschlüsselung (SEC-01/02/03)

### Best Practices [CITED: cryptography.io/en/latest/fernet/]

- `Fernet.generate_key()` liefert einen URL-safe-base64-kodierten 32-Byte-Schlüssel als `bytes`.
- `Fernet(key).encrypt(plaintext_bytes)` → URL-safe-base64-Token (`bytes`), enthält Timestamp + HMAC (Authentizität, nicht nur Vertraulichkeit).
- `Fernet(key).decrypt(token_bytes)` → Klartext-`bytes`, wirft `cryptography.fernet.InvalidToken` bei Manipulation, falschem Key oder (falls `ttl` gesetzt) Ablauf. **Kein TTL setzen** — Secrets sollen unbegrenzt gültig bleiben, solange der Key existiert.
- Fernet ist symmetrisch — derselbe Key ver- und entschlüsselt. Für dieses Projekt: **eine einzige globale Key-Datei** `/config/.secret_key`, die für ALLE Agenten gilt (nicht pro Agent), weil sie im selben Bind-Mount liegt, der ohnehin komplett gebackupt wird (SEC-03 verlangt genau das: "Backup-Hinweis: Config-Backup enthält Key + verschlüsselte .envs zusammen").

### Empfohlenes Modul (dupliziert in `agent/src/crypto.py` UND `webui/src/crypto.py`, da beide Services unabhängige Python-Packages ohne Shared-Import sind — Konsistenz mit Phase-4-Empfehlung "nichts wird von `agent/src/` importiert")

```python
# {agent,webui}/src/crypto.py — ~35 LOC, identisch in beiden Services
import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

ENC_PREFIX = "enc:"


def _key_file() -> Path:
    return Path(os.getenv("VIZPATCH_SECRET_KEY_FILE", "/config/.secret_key"))


def _load_or_create_key() -> bytes:
    path = _key_file()
    if path.exists():
        return path.read_bytes()
    key = Fernet.generate_key()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except PermissionError:
        pass
    return key


def encrypt_value(plaintext: str) -> str:
    if not plaintext or plaintext.startswith(ENC_PREFIX):
        return plaintext
    token = Fernet(_load_or_create_key()).encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"{ENC_PREFIX}{token}"


def decrypt_value(value: str) -> str:
    if not value or not value.startswith(ENC_PREFIX):
        return value  # Klartext-Legacy oder leer — unverändert zurückgeben
    token = value[len(ENC_PREFIX):]
    try:
        return Fernet(_load_or_create_key()).decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise RuntimeError(
            "Secret konnte nicht entschlüsselt werden (InvalidToken). "
            "Ursache meist: Key-Datei /config/.secret_key fehlt oder wurde ersetzt, "
            "oder der .env-Wert wurde manuell verändert. Siehe SEC-03-Doku (Reset-Pfad)."
        ) from e


def is_encrypted(value: str) -> bool:
    return bool(value) and value.startswith(ENC_PREFIX)
```

**Integration WebUI (`config_io.py`):** In `write_env(updates)` vor dem Line-Parser-Write: `IMAP_PASSWORD` und `LLM_API_KEY`-Werte (nur wenn nicht `""`/nicht `"****"`) durch `crypto.encrypt_value(...)` schicken, bevor sie in die Zeile geschrieben werden. In `read_env_masked()`: Maskierung bleibt unverändert (Secret-Keys werden bei vorhandenem Wert IMMER als `****` angezeigt, unabhängig davon ob verschlüsselt oder Klartext) — **kein Decrypt nötig, um zu maskieren**, das spart eine potenzielle `InvalidToken`-Fehlerquelle beim reinen Seiten-Rendern.

**Integration Agent (`config.py`):** Direkt nach `load_dotenv(...)`, vor der `Config`-Dataclass-Konstruktion:
```python
from .crypto import decrypt_value
imap_password = decrypt_value(os.environ["IMAP_PASSWORD"])
llm_api_key = decrypt_value(os.environ["LLM_API_KEY"])
```
**Fail-Fast-Pitfall:** Wenn `decrypt_value` eine `RuntimeError` wirft (Key fehlt/falsch), MUSS `load_config()` das durchreichen — der bestehende `_wait_for_config`-Loop in `main.py` fängt aktuell nur `RuntimeError` ab, die durch fehlende Env-Vars entsteht ("Missing required env vars"), und würde eine `InvalidToken`-`RuntimeError` fälschlich als "noch nicht konfiguriert, bitte warten" interpretieren → **Endlosschleife statt klarem Fehler**. Empfehlung: eigene Exception-Klasse `DecryptionError(RuntimeError)` einführen, die im Wait-Loop **nicht** stillschweigend wiederholt, sondern nach 1 Fehlversuch geloggt + im `agent_status.json` als `error` vermerkt wird (Status-Kachel zeigt es der WebUI an).

### Schutzumfang — ehrlich dokumentiert (SEC-03)

> **Was Fernet schützt:** Ein Datei-Leak der `.env` allein (z. B. versehentlich gepushtes Backup, Screenshot, Cloud-Sync-Fehlkonfiguration) legt KEINE Secrets im Klartext offen — der Angreifer sieht nur `enc:<token>`.
>
> **Was Fernet NICHT schützt:** Root-Zugriff auf den Host. Wer `/config/.secret_key` UND `/config/agents/*/.env` gemeinsam abgreift (z. B. komplettes Volume-Backup, Root-Shell auf dem Server), kann alles entschlüsseln — das ist bei symmetrischer Verschlüsselung ohne Master-Passwort systembedingt so (D-48 akzeptiert das bewusst gegen Zero-Config-Anspruch). Der Docker-Socket-Mount der WebUI ist ohnehin schon root-äquivalent (Phase-4-Doku) — Fernet erhöht die Sicherheit gegen **Datei-Exfiltration ohne vollen Host-Zugriff**, nicht gegen einen bereits kompromittierten Host.

## Docker-SDK: dynamische Agent-Container (MA-01…05)

### Kernproblem: Docker-SDK-Aufrufe aus dem `webui`-Container brauchen HOST-Pfade

`client.containers.run(volumes={...})` wird vom Docker-**Daemon** ausgeführt, der nur Host-Pfade (bei Bind-Mounts) oder Volume-Namen (bei Named Volumes) kennt — NICHT die Pfad-Sicht des `webui`-Containers selbst (`/config` im `webui`-Container ist ein Container-interner Pfad, der Daemon weiß nichts davon). Für dynamisch erzeugte Container muss die WebUI also den **tatsächlichen Host-Pfad** ihres eigenen `/config`-Bind-Mounts kennen.

### Lösung: Self-Inspection über die eigenen Container-Mounts [CITED: docker-py.readthedocs.io/en/stable/containers.html, github.com/docker/docker-py Issue #1903]

Docker setzt `HOSTNAME` im Container standardmäßig auf die (kurze) Container-ID, sofern nicht überschrieben — `socket.gethostname()` liefert damit die eigene Container-ID, mit der man sich selbst über die Docker-API abfragen kann [Community-Standard-Pattern, MEDIUM confidence — nicht in offizieller Docker-Doku explizit als Feature dokumentiert, aber breit etabliert und funktioniert konsistent mit dem `-h`/`hostname`-Verhalten, das offiziell dokumentiert ist].

```python
# webui/src/docker_ctrl.py — Erweiterung für Multi-Agent
import socket

def _self_mounts() -> dict[str, dict]:
    """Destination -> Mount-Dict des EIGENEN webui-Containers (z.B. '/config', '/data', '/app/prompts')."""
    client = _get_client()
    self_container = client.containers.get(socket.gethostname())
    return {m["Destination"]: m for m in self_container.attrs.get("Mounts", [])}


def _resolve_mount_ref(destination: str) -> str:
    """Liefert Host-Pfad (bei 'bind') oder Volume-Namen (bei 'volume') für einen eigenen Mount-Punkt."""
    mounts = _self_mounts()
    m = mounts.get(destination)
    if not m:
        raise RuntimeError(f"Kein eigener Mount für '{destination}' gefunden — Compose-Setup prüfen.")
    return m["Source"] if m["Type"] == "bind" else m["Name"]
```

**Wichtig — Named Volumes brauchen KEINE Host-Pfad-Auflösung:** Für Named Volumes akzeptiert die Docker-Engine-API den **Volume-Namen direkt** als Bind-Quelle (`volumes={"agent-data": {"bind": "/data", "mode": "rw"}}`), unabhängig vom Host-Dateisystempfad. Der `_resolve_mount_ref`-Trick liefert für `Type == "volume"` daher einfach `m["Name"]` — das ist der von Compose ggf. projekt-präfixierte tatsächliche Name (z. B. `vizpatch_agent-data` statt nur `agent-data`), was **exakt der Name ist, den man für neue Container wiederverwenden muss.** Wer stattdessen den Namen aus dem Compose-File hardcoded (`"agent-data"`), trifft bei Compose-V2-Default-Namespacing ins Leere (siehe Common Pitfalls).

### Container-Erzeugung pro Agent

```python
from docker.errors import NotFound
from docker.types import LogConfig

AGENT_LABEL_MANAGED = "vizpatch.managed"
AGENT_LABEL_ID = "vizpatch.agent-id"


def create_or_replace_agent_container(agent_id: str) -> dict:
    client = _get_client()
    image_ref = os.getenv("AGENT_IMAGE_REF", "vizpatch:v1.1.0")
    container_name = f"vizpatch-agent-{agent_id}"

    volumes = {
        _resolve_mount_ref("/config"): {"bind": "/config", "mode": "ro"},
        _resolve_mount_ref("/data"):   {"bind": "/data",   "mode": "rw"},
    }
    if "/app/prompts" in _self_mounts():
        volumes[_resolve_mount_ref("/app/prompts")] = {"bind": "/app/prompts", "mode": "ro"}

    try:
        client.containers.get(container_name).remove(force=True)
    except NotFound:
        pass

    container = client.containers.run(
        image_ref,
        name=container_name,
        detach=True,
        restart_policy={"Name": "unless-stopped"},
        labels={AGENT_LABEL_MANAGED: "true", AGENT_LABEL_ID: agent_id},
        environment={
            "AGENT_ENV_FILE": f"/config/agents/{agent_id}/.env",
            "CONTEXT_FILE": f"/config/agents/{agent_id}/context.md",
            "STATE_DB": f"/data/agents/{agent_id}/state.db",
            "AGENT_STATUS_FILE": f"/data/agents/{agent_id}/agent_status.json",
        },
        volumes=volumes,
        log_config=LogConfig(type="json-file", config={"max-size": "10m", "max-file": "3"}),
    )
    return {"ok": True, "container_id": container.id, "name": container_name}


def list_agent_containers() -> list[dict]:
    client = _get_client()
    containers = client.containers.list(all=True, filters={"label": AGENT_LABEL_MANAGED})
    return [
        {
            "agent_id": c.labels.get(AGENT_LABEL_ID, "?"),
            "name": c.name,
            "state": c.status,
            "started_at": c.attrs["State"].get("StartedAt"),
        }
        for c in containers
    ]
```

**Warum das Zero-Config-Verhalten NICHT gebrochen wird:** `AGENT_ENV_FILE`/`CONTEXT_FILE`/`STATE_DB`/`AGENT_STATUS_FILE` sind bereits heute überschreibbare Env-Vars in `agent/src/config.py` bzw. `agent/src/status_writer.py` (`os.getenv("STATE_DB", "/data/state.db")` usw.) — es sind **keine Code-Änderungen an den Pfad-Konstanten nötig**, nur diese vier Env-Vars werden beim `containers.run()`-Aufruf pro Agent unterschiedlich gesetzt. Der bestehende `Wait-for-Config-Loop` in `main.py` funktioniert unverändert weiter, weil er ohnehin nur `AGENT_ENV_FILE` (default `/config/.env`) konsultiert.

**Wichtig — `/config`-Mode bleibt `ro` für Agent-Container:** Genau wie im bestehenden Single-Agent-Setup (`agent/docker-compose.yml` Zeile 10: `./config:/config:ro`) bleibt der Mount für alle dynamisch erzeugten Agent-Container read-only. Nur die WebUI schreibt.

### Kollision mit Compose-verwaltetem `agent`-Service — Empfehlung: entfernen

Der bisherige `agent/docker-compose.yml` enthält einen statischen `agent:`-Service-Block. **Empfehlung: diesen Block komplett aus der Compose-Datei entfernen.** Ab Phase 5 existiert kein Compose-verwalteter Agent-Container mehr — jeder Agent-Container wird ausschließlich per Docker-SDK von der WebUI erzeugt/gestartet/gestoppt/entfernt. Die Compose-Datei behält nur noch `webui` + das `agent-data`-Volume (und idealerweise ein explizites `name:` für das Volume, siehe Pitfall unten). **Reboot-Verhalten bleibt erhalten:** SDK-erzeugte Container mit `restart_policy: unless-stopped` werden vom Docker-Daemon selbst nach einem Host-Reboot neu gestartet — unabhängig von Compose oder systemd. Nur `webui` selbst braucht weiterhin den bestehenden `vizpatch.service`-Autostart-Pfad aus Phase 4 (unverändert).

**Update-Flow muss umgebaut werden:** Der bestehende `docker_ctrl.pull_and_restart()`/`control_agent()`-Code ruft aktuell `subprocess.run(["docker","compose","up","-d","agent"])` als Fallback bzw. nach Pull — das funktioniert nicht mehr, sobald der `agent`-Service aus der Compose-Datei verschwindet. **Empfehlung für den Plan:** Nach `pull_and_restart(image_ref)` iteriert die Funktion über `list_agent_containers()` und ruft für jeden gefundenen Agenten `create_or_replace_agent_container(agent_id)` mit dem neuen Image erneut auf (statt `docker compose up -d agent`). Das ist ein Breaking Change gegenüber dem Phase-4-Code und sollte als eigener Task geplant werden.

## Bestehende Struktur — Erweiterungspunkte und Bruchgefahr

| Datei | Heutiger Zustand | Erweiterungspunkt für Phase 5 | Bruchgefahr |
|-------|-------------------|-------------------------------|-------------|
| `webui/src/config_io.py` | Hartkodierte Pfade `WEBUI_ENV_PATH` (default `/config/.env`), `WEBUI_CONTEXT_PATH` (default `/config/context.md`), `WEBUI_STATE_DB` (default `/data/state.db`) via `os.getenv(...)` | Alle drei Env-Var-Defaults müssen **pro Request** parametrisiert werden (aktueller Agent aus Session/Query-Param), nicht mehr global über Env-Var beim Prozessstart. **Empfehlung:** Funktionen bekommen einen `agent_id: str`-Parameter, der Pfade selbst baut (`Path(f"/config/agents/{agent_id}/.env")`), statt sich auf Env-Vars zu verlassen — WebUI-Prozess läuft für ALLE Agenten gleichzeitig, kann also keine prozessweiten Env-Var-Defaults pro Agent haben. | HOCH — jede Funktion, die aktuell `os.getenv("WEBUI_ENV_PATH", ...)` nutzt, muss umgebaut werden. Größter Diff der ganzen Phase. |
| `webui/src/docker_ctrl.py` | `AGENT_CONTAINER_NAME = "vizpatch-agent"` als Modul-Konstante, alle Funktionen (`get_agent_status`, `control_agent`, `stop_and_remove_agent`) arbeiten mit genau diesem einen Namen | Alle Funktionen brauchen `agent_id`-Parameter, Container-Name wird `f"vizpatch-agent-{agent_id}"` gebaut | MITTEL — Funktionssignaturen ändern sich, aber Kernlogik (containers.get/start/stop) bleibt |
| `webui/src/state_reader.py` | `AGENT_STATUS_FILE`/`WEBUI_STATE_DB` Env-Var-Defaults, identisches Problem wie `config_io.py` | Analog: `agent_id`-Parameter statt globaler Env-Var | HOCH — gleiche Ursache wie `config_io.py` |
| `webui/src/templates/index.html` | EIN Formular für EINEN Agenten, kein Auswahl-Mechanismus | Neues Dropdown `<select name="agent_id">` + Query-Param/Hidden-Field, das bei jedem Save/Status-Call mitgeschickt wird; `_status_card.html` wird zur Liste (`{% for agent in agents %}`) | MITTEL — additive Änderung, aber alle `hx-post`/`hx-get`-Targets müssen `agent_id` mitschicken |
| `webui/src/main.py` | Routen kennen keinen `agent_id`-Pfadparameter | Alle Routen (`/save`, `/agent/{action}`, `/agent/status`, `/context/generate`) brauchen `/agents/{agent_id}/...`-Präfix oder Query-Param `?agent_id=...`. **Neue Routen:** `POST /agents` (create), `POST /agents/{agent_id}/rename`, `POST /agents/{agent_id}/delete` | HOCH — Routing-Schema ändert sich grundlegend, größter strukturell riskanter Teil neben `config_io.py` |
| `agent/src/config.py` | `REQUIRED_ENV_VARS` enthält `ANTHROPIC_API_KEY` hart | Umbenennen zu `LLM_API_KEY`, Decrypt-Call einfügen, `Config`-Dataclass um `llm_provider: str` erweitern | MITTEL — Rename ist überall im Agent-Code zu verfolgen (`classify.py`/`generate.py` referenzieren `config.anthropic_api_key` direkt) |
| `agent/src/classify.py`, `agent/src/generate.py` | Instanziieren `Anthropic(api_key=config.anthropic_api_key)` direkt im Funktionskörper | Ersetzen durch `llm.llm_call(provider=config.llm_provider, api_key=config.llm_api_key, model=..., prompt=prompt, ...)` | NIEDRIG — reiner Austausch der LLM-Call-Zeilen, Rest der Funktion (Prompt-Bau, Logging) bleibt gleich |
| `agent/docker-compose.yml` | Enthält statischen `agent:`-Service | Service-Block entfernen, nur `webui` + `agent-data`-Volume (mit explizitem `name:`) bleiben | HOCH (strukturell, aber einmalig) |

## Migration: Single-Agent → `agents/default` (MA-01)

### Ablauf (idempotent, beim WebUI-Startup vor der ersten Route)

1. **Erkennung:** Existiert `/config/.env` (alte Root-Datei) UND existiert `/config/agents/default/.env` NOCH NICHT? → Migration nötig. Wenn `/config/agents/` bereits existiert (egal mit wie vielen Agenten) → Migration bereits durchgeführt oder Neuinstallation, **nichts tun** (Idempotenz-Kriterium: Anwesenheit von `/config/agents/` als Ganzes, nicht nur von `default/`).
2. **Verzeichnis anlegen:** `mkdir -p /config/agents/default`
3. **Dateien verschieben (nicht kopieren, um Doppel-Config zu vermeiden):**
   - `/config/.env` → `/config/agents/default/.env`, dabei Key `ANTHROPIC_API_KEY` → `LLM_API_KEY` umbenennen und `LLM_PROVIDER=anthropic` Zeile ergänzen (per Line-Parser, analog `config_io.write_env`, NICHT `dotenv.set_key` — Kommentare bleiben erhalten)
   - `/config/context.md` → `/config/agents/default/context.md` (reines `Path.rename()`, kein Parsing nötig)
4. **State verschieben:** `/data/state.db` → `/data/agents/default/state.db`, `/data/agent_status.json` → `/data/agents/default/agent_status.json` (`mkdir -p /data/agents/default` zuerst)
5. **Alten Container aufräumen:** Falls ein Container `vizpatch-agent` (alter, Compose-verwalteter Name ohne Suffix) noch existiert und läuft → stoppen + entfernen (kurze Downtime von Sekunden, akzeptabel laut ROADMAP.md "Depends on: Esso-Rollout abgeschlossen — Migration wird gegen Kopie des Live-Layouts getestet, kein Regressions-Risiko" — die Migration läuft NIE gegen einen live bedienten Kunden ohne vorherige Testkopie).
6. **Neuen Container erzeugen:** `create_or_replace_agent_container("default")` mit den frisch migrierten Pfaden.
7. **NICHT Teil der Migration:** Verschlüsselung der migrierten `IMAP_PASSWORD`/`LLM_API_KEY`-Werte. Das bleibt bewusst dem bestehenden SEC-02-Mechanismus überlassen ("Klartext-Legacy-Werte werden beim nächsten Save verschlüsselt") — Migration und Verschlüsselung sind zwei unabhängige Sorgen, die NICHT im selben Task vermischt werden sollten (reduziert Testaufwand und Rollback-Komplexität pro Task).

**Rollback:** Da Schritt 3/4 mit `rename()` statt `copy()` arbeitet, ist ein manuelles Rollback nur durch Zurückspielen eines Config-Backups möglich (kein automatischer Rollback-Mechanismus geplant, passend zu ROADMAP-Risiko "Rollback = altes Image + unverändertes Config-Backup"). **Empfehlung für den Plan:** Vor Schritt 3 einen Kopier-Schritt einfügen, der `/config/.env` + `/config/context.md` zusätzlich nach `/config/.migration-backup-<timestamp>/` sichert, BEVOR verschoben wird — kostet nur wenige KB, macht die Migration strikt sicherer ohne Zusatzkomplexität.

## Runtime State Inventory

| Kategorie | Gefundene Items | Aktion nötig |
|-----------|-----------------|--------------|
| Gespeicherte Daten | SQLite `/data/state.db` (Tabelle `processed_emails`) + `/data/agent_status.json` — beide EINMALIG pro Installation vorhanden (Single-Agent-Ära) | **Daten-Migration:** physisch nach `/data/agents/default/{state.db,agent_status.json}` verschieben (Schritt 4 oben). Kein Schema-Change nötig — SQLite-Struktur bleibt identisch, nur der Pfad ändert sich. |
| Live-Service-Config | `/config/.env` (Root, Single-Agent) + `/config/context.md` — je EINMALIG pro Installation | **Daten-Migration + Code-Edit:** verschieben nach `/config/agents/default/`, zusätzlich Key-Rename `ANTHROPIC_API_KEY`→`LLM_API_KEY` (Code-seitig muss `agent/src/config.py` fortan `LLM_API_KEY` statt `ANTHROPIC_API_KEY` lesen). |
| OS-registrierter State | Laufender Docker-Container `vizpatch-agent` (Compose-verwaltet, `restart_policy: unless-stopped` via Compose-YAML) | **Ersetzen:** Container stoppen + entfernen, durch SDK-erzeugten `vizpatch-agent-default` (gleicher Restart-Policy-Effekt, jetzt aber SDK-nativ statt Compose-nativ) ersetzen. `install-autostart.sh`/`vizpatch.service` selbst bleibt UNVERÄNDERT (betrifft nur `webui` + Docker-Daemon-Start, nicht einzelne Agent-Container). |
| Secrets/Env-Vars | `ANTHROPIC_API_KEY`, `IMAP_PASSWORD` in `/config/.env` (Klartext, Stand heute) | **Key-Rename bei Migration** (`ANTHROPIC_API_KEY`→`LLM_API_KEY`, Wert unverändert Klartext übernommen — Fernet-Verschlüsselung erfolgt separat und lazy beim nächsten WebUI-Save, siehe SEC-02). `WEBUI_USER`/`WEBUI_PASSWORD` (bcrypt-Hash, unabhängig von dieser Migration) bleiben unangetastet in derselben `/config/.env`-Root-Datei — **wichtig: WebUI-eigene Login-Credentials ziehen NICHT nach `agents/default/` um**, sie sind kein Agent-spezifisches Secret (Claude's Discretion aus CONTEXT.md — Empfehlung: globale WebUI-Settings bleiben in einer separaten Datei `/config/webui.env` oder bleiben schlicht am `/config/.env`-Root liegen, das NICHT migriert/gelöscht wird, sondern nach der Migration nur noch WebUI-globale Keys enthält). |
| Build-Artefakte | `vizpatch:v1.0.0`/`v1.1.0`-Images (bestehend), kein neues Artefakt-Format | Neues Docker-Image-Tag für den erweiterten Agent-Code (`llm.py`, `crypto.py`) — Versionsbump z. B. `v1.2.0`, `AGENT_IMAGE_REF`-Default in `docker_ctrl.py` entsprechend anpassen. `webui`-Image ebenfalls neu bauen (Fernet-Krypto + Multi-Agent-Routing). `scripts/build-deployment-package.sh` muss entsprechend erweitert werden (analog Phase-4-Diff). |

## Common Pitfalls

### Pitfall 1: Compose-Volume-Namespacing bricht `_resolve_mount_ref` für Named Volumes
**Was schief geht:** Der Code verlässt sich auf `_resolve_mount_ref("/data")`, das den vom Daemon tatsächlich verwendeten (ggf. projekt-präfixierten) Volume-Namen liefert — WENN aber irgendwo im Code stattdessen der Name `"agent-data"` hartkodiert wird (z. B. in einem Test-Fixture oder einer Doku-Zeile), bricht das bei jedem Compose-Setup, dessen Verzeichnisname vom ursprünglichen Vizionists-Dev-Setup abweicht.
**Prevention:** Compose-Top-Level-Volume-Eintrag um `name: agent-data` (explizit) ergänzen, damit der Name IMMER exakt `agent-data` ist, unabhängig vom Verzeichnisnamen des Compose-Projekts. Trotzdem den Self-Inspection-Code verwenden (robuster gegenüber künftigen Compose-Änderungen), nicht hartkodieren.
**Warnzeichen:** `docker.errors.NotFound: No such volume: agent-data` beim ersten `create_or_replace_agent_container`-Aufruf nach einem frischen `git clone` auf einem neuen Host.

### Pitfall 2: `google-generativeai` (alt) vs. `google-genai` (neu) verwechselt
**Was schief geht:** `pip install google-generativeai` statt `google-genai` installiert das ALTE SDK (anderes API-Shape, `import google.generativeai as genai` statt `from google import genai`), Code kompiliert nicht oder ruft falsche Methoden auf.
**Prevention:** `pyproject.toml` explizit `google-genai>=2.11,<3.0` (Bindestrich, nicht Unterstrich), Import immer `from google import genai`.
**Warnzeichen:** `ModuleNotFoundError` oder `AttributeError: module 'google.generativeai' has no attribute ...` bei Copy-Paste aus veralteten Tutorials.

### Pitfall 3: WebUI-Prozess ist jetzt Multi-Agent — globale Env-Var-Defaults in `config_io.py`/`state_reader.py` sind ein Bug-Magnet
**Was schief geht:** Alter Code liest `WEBUI_ENV_PATH` einmal beim Prozessstart als globalen Default. Bei Multi-Agent-Support MUSS jeder Request seinen eigenen `agent_id` mitbringen — wird das übersehen, zeigt die WebUI für Agent B versehentlich die Daten von Agent A (Cross-Kontamination, exakt das was MA-05 explizit ausschließt).
**Prevention:** Alle Lese/Schreib-Funktionen bekommen `agent_id: str` als PFLICHT-Parameter (kein Default-Fallback auf eine globale Konstante). Tests decken explizit "2 Agenten gleichzeitig, unterschiedliche Werte" ab (siehe MA-05).
**Warnzeichen:** Ein manueller Test mit 2 Agenten zeigt in einem der beiden Formulare plötzlich die E-Mail-Adresse des jeweils anderen.

### Pitfall 4: `docker_ctrl.pull_and_restart()`/Update-Flow bricht nach Entfernen des `agent`-Compose-Service
**Was schief geht:** Bestehender Code ruft nach Pull `subprocess.run(["docker","compose","up","-d","agent"])` — sobald der `agent`-Service aus der Compose-Datei entfernt ist (empfohlen, siehe oben), liefert dieser Befehl "service agent not found" und das Update bleibt wirkungslos, OHNE dass ein Fehler im UI sichtbar wird (weil der aktuelle Code `check=False` verwendet und nur stdout/stderr loggt).
**Prevention:** Update-Flow explizit umbauen auf Loop über `list_agent_containers()` + `create_or_replace_agent_container(agent_id)` je Agent (siehe Sektion Docker-SDK). Als eigener Plan-Task einplanen, NICHT nebenbei mit-erledigen.
**Warnzeichen:** Nach einem "Update"-Klick zeigt die Status-Kachel weiterhin die alte Image-Version, obwohl der Pull-Log "erfolgreich" meldet.

### Pitfall 5: `InvalidToken` beim Decrypt wird vom Wait-for-Config-Loop verschluckt
**Was schief geht:** Siehe Fernet-Sektion — eine `RuntimeError` aus `decrypt_value()` sieht für den bestehenden `_wait_for_config`-Except-Handler identisch aus wie "Config noch nicht vollständig", der Agent wartet endlos in einer Retry-Schleife statt einen sichtbaren Fehler zu zeigen.
**Prevention:** Eigene Exception-Klasse `DecryptionError`, die NICHT im Wait-Loop gefangen wird, sondern zum Prozess-Exit mit klarer Logzeile führt (Docker `restart_policy` startet dann neu — aber der Fehler bleibt in den Logs sichtbar statt in einer stillen Endlosschleife zu verschwinden).
**Warnzeichen:** Agent-Container läuft (Status "running"), aber es entstehen seit Tagen keine Drafts, Logs zeigen wiederholt `waiting_for_config`.

### Pitfall 6: `llm_seed.py` (Context-KI-Assistent aus Phase 4) bleibt fest auf Anthropic — Verwechslungsgefahr
**Was schief geht:** Jemand nimmt an, `webui/src/llm_seed.py` (Context.md-Generierung aus Phase 4) müsse jetzt auch den gewählten `LLM_PROVIDER` des jeweiligen Agenten nutzen — das ist explizit NICHT gefordert (Phase-5-Scope ist `classify.py`/`generate.py` im Agent, nicht der WebUI-eigene Context-Seed-Assistent). `llm_seed.py` bleibt unverändert auf Anthropic Sonnet fest verdrahtet, weil es ein WebUI-internes Komfort-Feature ist, kein Kern-Agent-Feature.
**Prevention:** Im Plan explizit dokumentieren, dass `llm_seed.py` NICHT Teil des Multi-LLM-Scopes ist.
**Warnzeichen:** Ein Task versucht, `llm_seed.py` zu einem Adapter-Aufruf umzubauen, obwohl das nicht in LLM-01…04 gefordert ist — unnötige Scope-Erweiterung.

### Pitfall 7: `LLM_API_KEY` mit falschem Provider kombiniert
**Was schief geht:** Betreiber wechselt `LLM_PROVIDER` per Dropdown von Anthropic auf OpenAI, vergisst aber `LLM_API_KEY` zu ändern (der Feldinhalt ist maskiert `****`, sieht "gespeichert" aus) — der alte Anthropic-Key wird an die OpenAI-API geschickt und liefert einen 401.
**Prevention:** Beim Save: wenn `LLM_PROVIDER` geändert wird UND `LLM_API_KEY`-Feld auf `****` (unverändert) steht, im UI eine Warnung zeigen ("Provider gewechselt — bitte auch den API-Key für den neuen Provider eintragen"). Kein Blocker, nur ein Hinweis (Betreiber ist non-technical, Prinzip aus CLAUDE.md: nichts blockieren, nur warnen).
**Warnzeichen:** `classify_email` wirft `openai.AuthenticationError` (401) direkt nach einem Provider-Wechsel.

## Don't Hand-Roll

| Problem | Nicht bauen | Stattdessen | Warum |
|---------|-------------|-------------|-------|
| Symmetrische Verschlüsselung | Eigener AES-CBC-Wrapper mit manuellem IV-Handling | `cryptography.fernet.Fernet` | Fernet kombiniert AES-128-CBC + HMAC-SHA256 + Timestamp korrekt, inkl. Padding-Handling — Eigenbau ist die klassische Quelle von Padding-Oracle-Bugs |
| Multi-Provider-LLM-Abstraktion | Generisches "LLM-Framework" (LangChain, LiteLLM) | Eigener ~60-LOC-Dispatcher `llm.py` mit drei `_call_*`-Funktionen | Nur 3 Provider, 1 Aufruf-Pattern (Single-Prompt, kein Streaming/Tools/Function-Calling nötig) — ein Framework wäre massiver Overhead für einen derart schmalen Use-Case (passt zu CLAUDE.md "kein Framework") |
| Docker-Host-Pfad-Ermittlung | Env-Var `HOST_CONFIG_PATH` manuell in `.env` pflegen, die der Betreiber selbst korrekt setzen muss | Self-Inspection via `client.containers.get(socket.gethostname())` | Betreiber ist non-technical (CLAUDE.md), ein manuell zu pflegender Host-Pfad wäre eine garantierte Fehlerquelle bei jedem Server-Umzug/Neuinstallation |
| Agent-ID-Slug-Erzeugung | Eigene Regex-Kaskade für Sonderzeichen/Umlaute | `python-slugify` ODER minimaler Eigenbau mit `re.sub(r"[^a-z0-9-]", "-", ...)` + Kollisions-Suffix (`-2`, `-3`) | Bei nur 2 Eingabefeldern (E-Mail oder Name) reicht ein simpler Eigenbau — eine neue Dependency für 10 Zeilen Slug-Logik lohnt sich hier nicht (Abwägung zugunsten von "kein Framework"-Prinzip, aber siehe Alternativen-Tabelle) |

**Key insight:** Der komplexeste Teil dieser Phase ist NICHT eine schwierige Bibliotheks-Integration, sondern die **korrekte Pfad-Buchhaltung** zwischen WebUI-Prozess (Multi-Agent-aware) und N unabhängigen Single-Agent-Containern. Bibliotheken (Fernet, drei LLM-SDKs, Docker-SDK) sind alle Standard-Wahl und gut dokumentiert — das Risiko liegt in der Orchestrierungs-Logik selbst.

### Alternativen erwogen

| Statt | Könnte man auch | Warum trotzdem die empfohlene Wahl |
|-------|------------------|-------------------------------------|
| Self-Inspection für Host-Pfade | `docker.sock`-Mount-Info aus `/proc/self/mountinfo` parsen | Self-Inspection ist Docker-API-nativ, plattformunabhängiger als `/proc`-Parsing (das bei rootless Docker/Podman abweicht) |
| Ein gemeinsames Named Volume + Env-Var-Pfad-Trennung (empfohlen) | Ein Named Volume PRO Agent (`agent-data-<id>`) | Volume-pro-Agent wäre sauberer isoliert, aber jedes neue Volume braucht wieder Erzeugung+Aufräum-Logik über die SDK — mehr bewegliche Teile für denselben Nutzen, den Env-Var-Pfad-Trennung schon bietet |
| Eigener Mini-Dispatcher `llm.py` | LiteLLM (unified API für 100+ Provider) | LiteLLM wäre für 3 Provider und ein einziges Call-Pattern (kein Streaming) Overkill; zusätzliche Dependency + Abstraktionsebene ohne Mehrwert für diesen schmalen Use-Case |

## State of the Art

| Alter Ansatz | Aktueller Ansatz | Seit | Impact |
|--------------|------------------|------|--------|
| `google-generativeai` (Google AI Python SDK, alt) | `google-genai` (Google Gen AI SDK, offiziell empfohlener Nachfolger) | seit ~2025 | Neues Paket, neuer Import-Pfad `from google import genai` — altes Paket ist Legacy/Wartungsmodus |
| OpenAI Chat-Completions als einziger Zugang | Responses-API (`client.responses.create`) als neuerer, von OpenAI empfohlener Zugang, Chat-Completions bleibt parallel unterstützt | seit ~2024/2025 | Für dieses Projekt irrelevant — Chat-Completions reicht für Single-Prompt-Pattern, Responses-API bietet hier keinen Mehrwert (kein Multi-Turn/Tool-Use) |
| `cryptography` 4x.x-Serie (Trainingsstand) | `cryptography` 49.0.0 | laufend, mehrere Major-Releases seit Trainingsstand | Fernet-API selbst ist seit Jahren stabil und unverändert — Major-Version-Sprünge betreffen primär interne OpenSSL-Bindings, nicht die hier genutzte High-Level-API |

**Deprecated/veraltet:**
- `google-generativeai`: durch `google-genai` abgelöst, nicht mehr für Neuprojekte verwenden.
- Gemini 2.0-Familie (`gemini-2.0-flash`, `gemini-2.0-flash-lite`): laut Recherche zum 1. Juni 2026 abgeschaltet — falls in älteren Tutorials referenziert, NICHT verwenden.

## Assumptions Log

| # | Claim | Sektion | Risiko bei Falsch |
|---|-------|---------|---------------------|
| A1 | OpenAI-Modell-Defaults `gpt-5-mini` (Classify) / `gpt-5.4` (Draft) sind gültige, aktuell verfügbare API-Model-IDs | LLM-SDKs & Modell-Defaults | Wenn ungültig: `openai.NotFoundError`/`BadRequestError` bei jedem Classify/Draft-Call für OpenAI-Kunden — LLM-04-Fixture-Test schlägt sofort sichtbar fehl (kein stiller Fehler). **Mitigation bereits eingebaut:** `.env`-Override via `MODEL_CLASSIFY`/`MODEL_DRAFT` erlaubt Korrektur ohne Code-Deploy. **Empfehlung:** Vor LLM-04-Durchlauf einen `client.models.list()`-Check als Verifikations-Task einplanen. |
| A2 | Google-Modell-Defaults `gemini-2.5-flash-lite` (Classify) / `gemini-2.5-pro` (Draft) sind gültige, aktuell verfügbare API-Model-IDs | LLM-SDKs & Modell-Defaults | Geringeres Risiko als A1 (offizielle Docs-Seite mit Code-Beispiel gefunden), aber eine neuere `gemini-3.x`-Familie existiert laut Recherche parallel — falls 2.5er-Serie bereits abgekündigt wäre, gleiche Mitigation wie A1. |
| A3 | `socket.gethostname()` liefert im WebUI-Container zuverlässig die eigene Container-ID (Docker-Default-Verhalten, nicht explizit in offizieller Doku als API-Contract festgeschrieben) | Docker-SDK: dynamische Agent-Container | Falls in einer künftigen Docker-Version geändert oder durch expliziten `hostname:`-Compose-Eintrag überschrieben: Self-Inspection schlägt fehl mit `docker.errors.NotFound`. **Mitigation:** Fallback auf `HOSTNAME`-Env-Var (identischer Wert) UND expliziten Container-ID-Lookup über `/proc/self/cgroup` als zweite Fallback-Stufe, falls der Plan besonders defensiv sein soll. |
| A4 | AVV/DPA-Aussagen zu OpenAI (30-Tage-Default-Retention, ZDR nur Enterprise) und Google (nur bezahlter Tier ohne Training) sind aktuell (Stand Recherche 2026-07-15) | DSGVO/AVV je Provider | Retention-Policies ändern sich — Betreiber-Doku sollte auf die jeweilige Live-Policy-Seite verlinken statt die Aussage hart einzufrieren. Kein technisches Risiko, aber ein Compliance-Risiko wenn veraltet zitiert. |
| A5 | Named-Volume-Referenzierung per reinem Namen (ohne Host-Pfad) funktioniert identisch für SDK-erzeugte Container wie für Compose-erzeugte | Docker-SDK: dynamische Agent-Container | Gut etabliertes Docker-Engine-API-Verhalten (Volume-Treiber ist transparent für Named Volumes) — Risiko gering, aber ungetestet in DIESEM Projekt-Kontext, sollte im ersten MA-03-Task real verifiziert werden (nicht nur gegen Mock). |

## Open Questions

1. **Exakte OpenAI/Google-Modell-IDs für Produktiv-Einsatz**
   - Was wir wissen: SDK-Call-Pattern ist sicher, Modell-Familie (mini/flash-lite für Classify, mid/pro für Draft) ist richtig gewählt.
   - Was unklar ist: die exakten String-Suffixe (`gpt-5.4` vs. `gpt-5.6-terra` vs. andere Variante) — Web-Recherche zu "Juli 2026"-Ständen liefert teils widersprüchliche/aggregator-basierte statt originär-offizielle Treffer.
   - Empfehlung: Ein früher Plan-Task (Wave 0 oder 1) sollte einen einmaligen `client.models.list()`-Check pro Provider mit einem echten Test-Key durchführen und die Konstanten in `MODEL_DEFAULTS` ggf. anpassen, BEVOR LLM-04 (Fixture-Durchlauf) beginnt.

2. **Wo leben WebUI-globale Settings (`WEBUI_USER`/`WEBUI_PASSWORD`/`AUTOSTART_ENABLED`) nach der Migration?**
   - Was wir wissen: Diese Felder sind heute Teil derselben `/config/.env`-Root-Datei, die jetzt "Agent default" wird.
   - Was unklar ist: Ob sie in derselben Root-`.env` verbleiben (die dann NUR NOCH WebUI-globale Keys enthält, keine Agent-Keys mehr) oder in eine eigene Datei (`/config/webui.env`) wandern.
   - Empfehlung: Root-`.env` als reine WebUI-Settings-Datei weiterverwenden (kein Dateiname-Wechsel nötig, nur inhaltliche Bedeutungsverschiebung — migrierte Agent-Keys werden aus ihr ENTFERNT nachdem sie nach `agents/default/.env` verschoben wurden). Minimal-invasiv, kein neuer Dateiname im Deployment-Paket nötig.

3. **Slug-Kollisionsstrategie bei gleichnamigen Agenten (z. B. zwei `info@`-Adressen unterschiedlicher Domains)**
   - Was wir wissen: Slug wird aus E-Mail oder Name abgeleitet (Claude's Discretion laut CONTEXT.md).
   - Was unklar ist: exaktes Kollisions-Suffix-Schema.
   - Empfehlung: `slug = re.sub(r"[^a-z0-9]+", "-", email_or_name.lower()).strip("-")`, bei Kollision `-2`, `-3`, … anhängen; Prüfung gegen bestehende `/config/agents/*`-Verzeichnisnamen beim Anlegen.

## Environment Availability

| Dependency | Erforderlich für | Verfügbar (Vizionists Dev) | Version | Fallback |
|------------|-------------------|------------------------------|---------|----------|
| PyPI-Zugriff (`pip`/`slopcheck`) | Paket-Verifikation | ✓ | — | — |
| Docker + Docker-SDK | MA-03/04/05 (lokaler Test mit ≥2 parallelen Agent-Containern) | ✓ (aus Phase 4 bestätigt) | 7.2.0 | — |
| Echter OpenAI-API-Key | LLM-04-Fixture-Test für OpenAI-Provider | Nicht in dieser Recherche-Session geprüft — muss vor Ausführung besorgt werden | — | Ohne echten Key: Modell-ID-Verifikation (`client.models.list()`) nicht möglich, Task muss bis Key vorhanden verschoben werden |
| Echter Google-API-Key | LLM-04-Fixture-Test für Google-Provider | Nicht in dieser Recherche-Session geprüft | — | Analog OpenAI |
| 2 Test-IMAP-Postfächer | MA-05 (Parallelbetrieb-Verifikation) | Aus Phase 1/2 bereits ein GMX/IONOS-Testaccount vorhanden — zweiter Account muss ggf. neu angelegt werden | — | Vizionists-eigene Zweit-Adresse (z. B. Gmail) als zweiter Test-Account |

**Missing dependencies with no fallback:** keine (alle fehlenden Punkte sind vor Ausführung beschaffbar, kein technischer Blocker).
**Missing dependencies with fallback:** echte OpenAI-/Google-Keys (Fallback: Modell-Verifikation verschieben, Mock-Tests laufen ohne echten Key).

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | ja (unverändert aus Phase 4) | HTTPBasic + bcrypt (bestehend), keine Änderung durch Phase 5 |
| V3 Session Management | nein | Stateless Basic-Auth, kein Session-Store (unverändert) |
| V4 Access Control | teilweise | Kein Rollen-Modell (Ein-Betreiber-Persona, unverändert) — Agent-Löschen/Anlegen ist wie bisher jedem authentifizierten WebUI-Nutzer möglich |
| V5 Input Validation | ja | Agent-ID-Slug wird server-seitig aus Nutzereingabe generiert und gegen ein striktes Whitelist-Pattern (`^[a-z0-9-]+$`) validiert, BEVOR er als Verzeichnis-/Container-Name verwendet wird — verhindert Path-Traversal (`../../etc`) über einen manipulierten Agent-Namen |
| V6 Cryptography | ja — NEU in dieser Phase | `cryptography.fernet.Fernet` (nie selbstgebaute Krypto), Key-Datei `chmod 600`, kein Hardcoded-Key im Code |
| V8 Data Protection | ja | Fernet-verschlüsselte Secrets in `.env`, ehrlich dokumentierter Schutzumfang (siehe SEC-03-Sektion) |

### Known Threat Patterns für diesen Stack

| Pattern | STRIDE | Standard-Mitigation |
|---------|--------|----------------------|
| Path-Traversal über Agent-ID (`agent_id = "../../etc/passwd"`) | Tampering | Striktes Slug-Whitelist-Pattern `^[a-z0-9-]{1,64}$`, serverseitig VOR jeder Pfad- oder Docker-Namens-Konstruktion validiert — niemals Rohwert aus Formular direkt in `Path(...)` oder Container-Namen einsetzen |
| Prompt-Injection über `context.md`/Kundenmail-Body in den Draft-Prompt (bestehendes Risiko, durch 3 Provider jetzt 3x relevant) | Tampering/Information Disclosure | Bereits bestehende Mitigation (PII-Redaction, kein Auto-Send) bleibt unverändert; bei allen 3 Providern gilt: LLM-Output landet NUR im Draft, nie automatisch versendet |
| Secret-Leak über Docker-Logs (API-Key versehentlich mitgeloggt bei SDK-Fehlern) | Information Disclosure | Alle drei `_call_*`-Funktionen dürfen `api_key` NIE in Log-Statements einbetten — Exception-Handling loggt nur Fehlertyp/Model-Name, nicht die Eingabe-Parameter |
| Fernet-Key-Diebstahl über Docker-Volume-Backup ohne Zugriffskontrolle | Information Disclosure | Dokumentierter Schutzumfang (SEC-03) — kein technischer Fix, sondern ehrliche Doku-Pflicht im README/RUNBOOK |
| Cross-Agent-Datenleck durch fehlenden `agent_id`-Parameter (Pitfall 3) | Information Disclosure | Server-seitige Pflicht-Parametrisierung aller Config-/State-Zugriffsfunktionen, keine globalen Fallback-Pfade mehr |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/05-multi-llm-multi-agent-verschl-sselung-v1-2/05-CONTEXT.md` — D-46…D-50 + Specifics + Deferred
- `.planning/REQUIREMENTS.md` — LLM-01…04, MA-01…05, SEC-01…03 Wortlaut
- `.planning/ROADMAP.md` — Phase-5-Sektion, Success Criteria, Risiken
- `agent/src/config.py`, `classify.py`, `generate.py`, `main.py`, `status_writer.py`, `provider_config.py` (2026-07-15 gelesen) — bestehende Env-Var-Konventionen, Pfad-Defaults, Prompt-Format
- `webui/src/config_io.py`, `docker_ctrl.py`, `main.py`, `state_reader.py`, `auth.py`, `templates/index.html` (2026-07-15 gelesen) — bestehende Routen, Masking-Logik, HTMX-Muster
- `agent/prompts/classify.txt`, `generate.txt` (2026-07-15 gelesen) — bestätigt Single-Prompt-Format ohne System/User-Split
- PyPI Registry via `pip index versions` + `slopcheck install` (2026-07-15) — alle 5 Kern-Pakete `[OK]`, keine Slop-Treffer
- [cryptography.io Fernet-Doku](https://cryptography.io/en/latest/fernet/) — Key-Generierung, encrypt/decrypt, InvalidToken
- [docker-py Containers-Doku](https://docker-py.readthedocs.io/en/stable/containers.html) — `containers.run()`-Signatur, Labels, Filter
- [docker-py LogConfig](https://docker-py.readthedocs.io/en/stable/api.html#docker.types.LogConfig) — `log_config`-Parameter-Name bestätigt
- [github.com/openai/openai-python](https://github.com/openai/openai-python) — Chat-Completions-Pattern, Fehlerklassen
- [github.com/googleapis/python-genai](https://github.com/googleapis/python-genai) — `genai.Client`, `generate_content`-Pattern, Fehlerklassen
- [ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash-lite) — Modell-ID + Code-Beispiel

### Secondary (MEDIUM confidence)
- [openai.com/policies/data-processing-addendum](https://openai.com/policies/data-processing-addendum/), [openai.com/enterprise-privacy](https://openai.com/enterprise-privacy/) — DPA/ZDR-Aussagen
- [ai.google.dev/gemini-api/terms](https://ai.google.dev/gemini-api/terms), [ai.google.dev/gemini-api/docs/logs-policy](https://ai.google.dev/gemini-api/docs/logs-policy) — Paid-vs-Free-Tier-Datennutzung
- [github.com/docker/docker-py Issue #1903](https://github.com/docker/docker-py/issues/1903) — Bind-Mount-Introspektion via `container.attrs['Mounts']`
- `developers.openai.com/api/docs/models/gpt-5-mini` (in Suchergebnissen referenziert, nicht direkt gefetcht) — Existenz des Modells `gpt-5-mini`

### Tertiary (LOW confidence — flagged)
- "GPT-5.6 Sol/Terra/Luna"-Modellfamilie und deren exakte API-Model-ID-Strings — nur über Preisvergleichs-Aggregator-Seiten (benchlm.ai, aipricing.guru, eesel.ai) belegt, NICHT konsistent über eine originär-offizielle OpenAI-Docs-Seite verifiziert. Siehe Assumptions Log A1.
- `socket.gethostname()` == Container-ID — community-etabliertes Pattern, keine explizite offizielle Docker-API-Vertragsgarantie gefunden. Siehe Assumptions Log A3.

## Metadata

**Confidence Breakdown:**
- Standard Stack (SDK-Versionen, Fernet, Docker-SDK-Patterns): HIGH — PyPI-verifiziert, slopcheck OK, offizielle Docs/GitHub-READMEs zitiert
- Architektur (Self-Inspection, Env-Var-Pfad-Routing, Migration-Ablauf): HIGH — baut direkt auf gelesenem Bestandscode auf, keine Spekulation
- Modell-Defaults OpenAI/Google (LLM-03): LOW-MEDIUM — widersprüchliche Web-Recherche-Ergebnisse zu exakten Modell-ID-Strings, explizite Verifikations-Empfehlung vor Produktiv-Einsatz ausgesprochen
- DSGVO/AVV-Hinweise: MEDIUM — auf offiziellen Policy-Seiten zitiert, aber naturgemäß zeitlich volatil

**Research date:** 2026-07-15
**Valid until:** 2026-07-29 (LLM-Modell-Landschaft ist fast-moving — 14 statt der üblichen 30 Tage, insbesondere die OpenAI/Google-Modell-IDs sollten bei Ausführungsverzug erneut geprüft werden; Docker-SDK/Fernet-Teile bleiben deutlich länger gültig)

## RESEARCH COMPLETE

**Phase:** 05 — Multi-LLM, Multi-Agent & Verschlüsselung (v1.2)
**Confidence:** MEDIUM-HIGH

### Key Findings für den Planner
1. **Architektur ist geklärt und risikoarm:** Self-Inspection des `webui`-Containers (`client.containers.get(socket.gethostname())`) liefert Host-Pfade/Volume-Namen für dynamisch erzeugte Agent-Container. Pfad-Trennung zwischen Agenten läuft über vier BEREITS existierende Env-Var-Overrides im Agent (`AGENT_ENV_FILE`, `CONTEXT_FILE`, `STATE_DB`, `AGENT_STATUS_FILE`) — **null Pfad-Code-Änderungen in `agent/src/config.py` nötig**, nur der LLM-Adapter und Fernet-Decrypt kommen dazu.
2. **Größter struktureller Diff liegt in der WebUI, nicht im Agent:** `config_io.py`, `docker_ctrl.py`, `state_reader.py` und `main.py` müssen von "ein globaler Agent" auf "N Agenten via `agent_id`-Parameter" umgebaut werden — das ist der aufwändigste Teil der Phase, deutlich größer als der LLM-Adapter oder die Fernet-Integration.
3. **Modell-Defaults für OpenAI/Google sind die einzige LOW-Confidence-Stelle:** `gpt-5-mini`/`gpt-5.4` und `gemini-2.5-flash-lite`/`gemini-2.5-pro` sind plausible, aber nicht restlos verifizierte Defaults — Empfehlung: früher Verifikations-Task mit `client.models.list()` gegen echte Keys, BEVOR LLM-04 (Fixture-Durchlauf) beginnt. Bestehendes `.env`-Override-Pattern (`MODEL_CLASSIFY`/`MODEL_DRAFT`) dient als Notfall-Korrekturpfad ohne Code-Deploy.
4. **Update-Flow und Compose-Datei brauchen einen Breaking Change:** Der statische `agent`-Service muss aus `docker-compose.yml` entfernt werden (nur noch `webui` + `agent-data`-Volume mit explizitem `name:`), und `pull_and_restart()` muss von `docker compose up -d agent` auf einen SDK-Loop über alle Agent-Container umgestellt werden — als eigener Plan-Task einplanen.
5. **Migration (MA-01) ist ein eigenständiger, sauber abgrenzbarer Task:** Verzeichnisse verschieben (nicht kopieren) + Key-Rename (`ANTHROPIC_API_KEY`→`LLM_API_KEY`) + alten Container ersetzen — bewusst OHNE gleichzeitige Fernet-Verschlüsselung der migrierten Werte (die läuft separat und lazy über den bereits geplanten SEC-02-Mechanismus).

### Ready for Planning
Empfohlene Wave-Struktur für den Planner:
- **Wave 0:** `pyproject.toml`-Erweiterungen (agent: `openai`, `google-genai`, `cryptography`; webui: `cryptography`), `crypto.py` in beiden Services, Model-Verifikations-Task (`client.models.list()` gegen echte Keys)
- **Wave 1** *(parallel)*: `agent/src/llm.py` (Adapter) + Umstellung `classify.py`/`generate.py`; UND unabhängig davon `webui`-Refactor von globalen Pfaden auf `agent_id`-Parameter in `config_io.py`/`state_reader.py`
- **Wave 2** *(blocked on Wave 1)*: `docker_ctrl.py`-Erweiterung (Self-Inspection, `create_or_replace_agent_container`, `list_agent_containers`), Compose-Datei-Umbau (Service entfernen, Volume-`name:` ergänzen)
- **Wave 3** *(blocked on Wave 2)*: Migration-Hook (WebUI-Startup, analog `docker-entrypoint.sh`), Agent-Dropdown + neue Routen in `main.py`/Templates
- **Wave 4** *(blocked on Wave 3)*: Update-Flow-Umbau (SDK-Loop statt Compose-Restart), Deployment-Paket-Builder-Diff, Versionsbump
- **Wave 5:** LLM-04-Fixture-Durchlauf je Provider (nach Model-Verifikation aus Wave 0), MA-05-Parallelbetrieb-Test mit 2 echten Test-Postfächern
