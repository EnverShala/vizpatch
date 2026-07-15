# Phase 5: Multi-LLM, Multi-Agent & Verschlüsselung (v1.2) - Context

**Gathered:** 2026-07-15
**Status:** Ready for planning
**Source:** Direktauftrag Betreiber (Kommando-Argumente /gsd:plan-phase) + Orchestrator-Defaults (autonom, vom Nutzer bestätigt durch "plane komplett, keine Rückfragen")

<domain>
## Phase Boundary

Diese Phase liefert drei Features, ausschließlich als Erweiterung des bestehenden Agent+WebUI-Stacks (FastAPI/Jinja2/HTMX + Python-Agent + Docker-SDK):

1. **Multi-LLM-Provider:** Dropdown im WebUI-Formular zur Wahl zwischen Anthropic (Default), OpenAI und Google Gemini. Generisches `LLM_API_KEY`-Feld ersetzt `ANTHROPIC_API_KEY`. Interner Adapter im Agent routet Classify- und Draft-Calls zum jeweiligen SDK.
2. **Multi-Agent:** Ein Agent-Dropdown im WebUI (leer, wenn kein Agent gespeichert ist) erlaubt das Anlegen, Auswählen, Bearbeiten und Löschen mehrerer Agenten (= Mail-Accounts). Mehrere Agenten laufen gleichzeitig, jeder als eigener Docker-Container.
3. **Secrets-Verschlüsselung:** IMAP-Passwort und LLM-API-Key liegen verschlüsselt in den `.env`-Dateien (dort, wo sie heute gespeichert sind — kein neuer Speicherort).

**Nicht in dieser Phase:** Auto-Send, Draft-Vorschau/Historie im WebUI, OAuth2, IMAP-IDLE, Mandanten-Trennung mit Logins pro Kunde (Multi-Agent ≠ Multi-Tenant: eine WebUI, ein Betreiber, mehrere Postfächer). Ausführung der Pläne erfolgt explizit später (nach Esso-Rollout).
</domain>

<decisions>
## Implementation Decisions

### Nutzer-Vorgaben (locked, wörtlich aus dem Auftrag)
- WebUI-Dropdown zur Auswahl zwischen Anthropic, OpenAI, Google AI
- Bei E-Mail ebenfalls ein Dropdown, **leer wenn kein Agent gespeichert ist**, um mehrere Agenten (mehrere Mail-Accounts) gleichzeitig zu verwalten und auszuführen
- Die Daten (Credentials) sind "einfach verschlüsselt" in der `.env` bzw. am aktuellen Speicherort — keine neue Datenbank, kein externer Secret-Store

### D-46: Ein Container pro Agent (locked)
Der Agent-Code bleibt Single-Account. Die WebUI orchestriert pro gespeichertem Agenten einen eigenen Container `vizpatch-agent-<agent-id>` via Docker-SDK (Fähigkeit existiert seit Phase 4 für einen Container). `restart_policy: unless-stopped` via SDK, Container-Labels (`vizpatch.agent-id=<id>`) für Zuordnung und Aufräumen.
**Why:** Minimaler Umbau am getesteten Agent-Code, saubere Isolation (Absturz/Rate-Limit eines Accounts betrifft die anderen nicht), Status/Logs pro Agent trivial.

### D-47: Config-Layout `/config/agents/<agent-id>/` (locked)
Pro Agent ein Verzeichnis mit eigener `.env` + `context.md`. Agent-ID ist ein Slug (aus Name oder E-Mail-Adresse abgeleitet, kollisionssicher). Beim ersten Start der neuen WebUI wird ein vorhandenes Single-Agent-Layout (`/config/.env` + `/config/context.md`) automatisch und verlustfrei als Agent `default` migriert. State analog unter `/data/agents/<agent-id>/` (SQLite `state.db` + `agent_status.json`).
**Why:** Bleibt beim heutigen Speicherort (Bind-Mount `./config`), Zero-Config-Bootstrap und Section-Save aus Phase 4 funktionieren pro Agent-Verzeichnis weiter; Esso-Installation überlebt das Update ohne Neukonfiguration.

### D-48: Fernet + Key-Datei, kein Master-Passwort (locked)
Symmetrische Verschlüsselung mit `cryptography.fernet`. Secret-Werte stehen als `enc:<token>` in der `.env`. Key-Datei (z. B. `/config/.secret_key`) wird beim ersten Start generiert, `chmod 600`, liegt im selben Config-Bind-Mount. WebUI verschlüsselt beim Save, Agent entschlüsselt beim Config-Load. Klartext-Legacy-Werte werden erkannt und beim nächsten Save verschlüsselt. Kein Master-Passwort-Prompt.
**Why:** Nutzer will es "einfach verschlüsselt"; Master-Passwort würde Zero-Config und Autostart nach Reboot brechen. Schutzumfang (Datei-/Backup-Leaks, nicht Root-Zugriff auf den Host) wird ehrlich dokumentiert (SEC-03).

### D-49: LLM-Provider pro Agent, Modell-Defaults hart verdrahtet (locked)
`LLM_PROVIDER` + `LLM_API_KEY` sind Felder der Agent-`.env` (pro Agent unabhängig). Kein Modell-Auswahlfeld im UI — pro Provider ein fest verdrahtetes Classify+Draft-Modellpaar (Anthropic → Haiku 4.5 / Sonnet 4.6; OpenAI/Google-Äquivalente im Research verifizieren). Adapter-Modul im Agent (`llm.py` o. ä.), `classify.py`/`generate.py` rufen nur noch den Adapter.
**Why:** UI bleibt schlank (Betreiber ist kein LLM-Experte), Modellpflege ist Code-Sache; Provider-Wahl pro Agent erlaubt gemischte Setups.

### D-50: Dropdown-Semantik (locked)
Agent-Dropdown leer bei frischer Installation → Formular startet im "Neuen Agent anlegen"-Modus. Auswahl eines Agenten lädt dessen Formular (HTMX, ohne Full-Reload passend zum Section-Save-Muster). Löschen mit Zwei-Stufen-Bestätigung (wie Zero-Reset aus UI-08) entfernt Config-Verzeichnis, Container und State.

### Claude's Discretion
- Exakte Slug-Regeln für Agent-IDs, Kollisionshandling
- HTMX-Detailverhalten (Partial-Templates, Reload-Grenzen) beim Agent-Wechsel
- Aufteilung/Benennung der neuen Module (z. B. `agent/src/llm.py`, `webui/src/agents_io.py`, `webui/src/crypto.py`)
- Wie der Agent-Container sein Config-Verzeichnis erhält (Bind-Mount-Subpfad vs. Env-Var `AGENT_ID` + gemeinsamer Mount) — im Research klären, was mit Docker-SDK-erzeugten Containern robust ist
- Umgang mit WebUI-eigenen Einstellungen (Login-Hash bleibt global in `/config/.env` oder eigener Datei)
- Fehlerbilder bei ungültigem/fehlendem Key (Key gelöscht, `.env` noch verschlüsselt): klare Fehlermeldung + Reset-Pfad
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` — Phase-5-Sektion (Goal, 6 Success Criteria, Risiken)
- `.planning/REQUIREMENTS.md` — LLM-01…04, MA-01…05, SEC-01…03

### Bestehender Code (Erweiterungsbasis)
- `webui/src/main.py` — alle Routes (/, /save, /agent/{action}, /context/generate, /reset, /update/*)
- `webui/src/config_io.py` — .env-Read/Write, get_missing_config (wird pro-Agent-fähig)
- `webui/src/docker_ctrl.py` — Docker-SDK-Wrapper (wird Multi-Container-fähig)
- `webui/src/state_reader.py` — SQLite-Ro + agent_status.json-Ro (wird pro-Agent-fähig)
- `webui/docker-entrypoint.sh` — Zero-Config-Seeding (Migration-Hook)
- `webui/src/templates/index.html` + `_status_card.html` — Formular mit Section-Save (bekommt Agent- + Provider-Dropdown)
- `agent/src/config.py` — .env/context/prompts-Loader (bekommt Entschlüsselung + LLM_*-Vars)
- `agent/src/classify.py`, `agent/src/generate.py` — Anthropic-Calls (werden auf Adapter umgestellt)
- `agent/src/main.py` — Wait-for-Config-Loop (muss mit Agent-Verzeichnis-Pfad umgehen)
- `agent/docker-compose.yml` — beide Services (Rolle des statischen `agent`-Service klären: entfällt oder wird Template)

### Phase-4-Planungsartefakte (Muster + Entscheidungen D-27…D-45)
- `.planning/phases/04-web-ui-multi-kunde/04-CONTEXT.md`
- `.planning/phases/04-web-ui-multi-kunde/04-RESEARCH.md`

### Test-Grundlage
- `.planning/phases/02-deployment-beim-kunden/PRE-DEPLOYMENT-TEST.md` + 14 `.eml`-Fixtures (LLM-04-Retest)
</canonical_refs>

<specifics>
## Specific Ideas

- Dropdown-Reihenfolge Provider: Anthropic (Default) | OpenAI | Google
- `enc:`-Prefix als Erkennungsmerkmal verschlüsselter Werte (Klartext ohne Prefix = Legacy, wird migriert)
- AVV-Hinweistext im WebUI abhängig vom gewählten Provider (ein Satz, kein Rechtstext)
- Status-Bereich: eine Status-Kachel pro Agent (Liste), nicht nur eine globale
- `install-autostart.sh`/systemd: muss weiterhin funktionieren — WebUI-Container startet via Compose, Agent-Container hängen an Docker-`restart_policy` (überleben Reboot ohne systemd-Änderung; verifizieren)
</specifics>

<deferred>
## Deferred Ideas

- Modell-Auswahl pro Agent im UI (v2 — erst wenn Kunden danach fragen)
- Azure-OpenAI-/Mistral-/Ollama-Support (v2)
- Master-Passwort / Hardware-Key für Secrets (v2, bricht Zero-Config)
- Multi-Tenant (Logins pro Kunde, Mandanten-Trennung) — bleibt out of scope
</deferred>

---

*Phase: 05-multi-llm-multi-agent-verschl-sselung-v1-2*
*Context gathered: 2026-07-15 via Direktauftrag + autonome Orchestrator-Defaults*
