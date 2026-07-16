# Phase 5: Multi-LLM, Multi-Agent & Verschlüsselung (v1.2) - Context

**Gathered:** 2026-07-15
**Status:** Ready for planning
**Source:** Direktauftrag Betreiber (Kommando-Argumente /gsd:plan-phase) + Orchestrator-Defaults (autonom, vom Nutzer bestätigt durch "plane komplett, keine Rückfragen")

<domain>
## Phase Boundary

Diese Phase liefert drei Features, ausschließlich als Erweiterung des bestehenden Agent+WebUI-Stacks (FastAPI/Jinja2/HTMX + Python-Agent + Docker-SDK):

1. **Multi-LLM-Provider:** Dropdown im WebUI-Formular zur Wahl zwischen Anthropic (Default), OpenAI und Google Gemini. Generisches `LLM_API_KEY`-Feld ersetzt `ANTHROPIC_API_KEY`. Interner Adapter im Agent routet Classify- und Draft-Calls zum jeweiligen SDK.
2. **Multi-Agent:** Ein Agent-Dropdown im WebUI (leer, wenn kein Agent gespeichert ist) erlaubt das Anlegen, Auswählen, Bearbeiten und Löschen mehrerer Agenten (= Mail-Accounts). Mehrere Agenten laufen gleichzeitig — **in einem einzigen Agent-Container** (Multi-Account-Loop), Start/Stop pro Agent über ein Aktiv-Flag. Einrichtungs-Flow (Nutzer wörtlich): Agent anlegen → Provider klicken (Anthropic/OpenAI/Google) → API-Key + E-Mail + IMAP-Passwort + Context eingeben → Agent ist konfiguriert und erscheint im Dropdown.
3. **Secrets-Verschlüsselung:** IMAP-Passwort und LLM-API-Key liegen verschlüsselt in den `.env`-Dateien (dort, wo sie heute gespeichert sind — kein neuer Speicherort).

**Nicht in dieser Phase:** Auto-Send, Draft-Vorschau/Historie im WebUI, OAuth2, IMAP-IDLE, Mandanten-Trennung mit Logins pro Kunde (Multi-Agent ≠ Multi-Tenant: eine WebUI, ein Betreiber, mehrere Postfächer). Ausführung der Pläne erfolgt explizit später (nach Esso-Rollout).
</domain>

<decisions>
## Implementation Decisions

### Nutzer-Vorgaben (locked, wörtlich aus dem Auftrag + Korrektur-Runde 2026-07-16)
- WebUI-Dropdown zur Auswahl zwischen Anthropic, OpenAI, Google AI
- Bei E-Mail ebenfalls ein Dropdown, **leer wenn kein Agent gespeichert ist**, um mehrere Agenten (mehrere Mail-Accounts) gleichzeitig zu verwalten und auszuführen
- **Ausdrücklich KEIN Container pro Agent** — Agenten werden per Dropdown ausgewählt und per Start/Stop-Button laufen gelassen
- **Pro Agent genau 1 API-Key** konfigurierbar (der Key des gewählten Providers)
- Einrichtungs-Flow: Agent anlegen → Provider klicken → API-Key, E-Mail, IMAP-Passwort, Context eingeben → Agent erscheint im Dropdown
- Die Daten (Credentials) sind "einfach verschlüsselt" in der `.env` bzw. am aktuellen Speicherort — keine neue Datenbank, kein externer Secret-Store

### D-46 (revidiert 2026-07-16): Ein Agent-Container gesamt, Aktiv-Flag pro Agent (locked, Nutzer-Entscheidung)
Es gibt weiterhin genau **einen** Agent-Container (wie heute via Compose, `restart: unless-stopped`). `main.py` wird Multi-Account: Pro Poll-Zyklus wird die Agenten-Liste aus `/config/agents/*/` frisch eingelesen und **sequentiell** jeder Agent mit gesetztem Aktiv-Flag verarbeitet (eigene IMAP-Verbindung, eigener State, eigener LLM-Provider je Durchlauf). Start/Stop-Button im WebUI schreibt nur das Aktiv-Flag (z. B. `AGENT_ENABLED=true|false` in der Agent-`.env`) — wirkt ab dem nächsten Poll-Zyklus, **kein** Container-Restart, **kein** Docker-SDK pro Agent. Fehler eines Agenten (Auth-Fehler, Rate-Limit, IMAP down) werden geloggt und isoliert — die übrigen Agenten laufen im selben Zyklus weiter. Docker-Steuerung im WebUI bleibt wie in Phase 4 (ein `agent`-Service: globales Start/Stop/Restart als Admin-Funktion), Update-Flow bleibt Compose-basiert.
**Why:** Nutzer-Entscheidung (bestätigt per Rückfrage 2026-07-16: "1 Container, Aktiv-Flag pro Agent"). Weniger RAM, kein dynamisches Container-Management, Start/Stop reagiert sofort und ohne Root-äquivalente Docker-Operationen.

### D-47: Config-Layout `/config/agents/<agent-id>/` (locked)
Pro Agent ein Verzeichnis mit eigener `.env` + `context.md`. Agent-ID ist ein Slug (aus Name oder E-Mail-Adresse abgeleitet, kollisionssicher). Beim ersten Start der neuen WebUI wird ein vorhandenes Single-Agent-Layout (`/config/.env` + `/config/context.md`) automatisch und verlustfrei als Agent `default` migriert. State analog unter `/data/agents/<agent-id>/` (SQLite `state.db` + `agent_status.json`).
**Why:** Bleibt beim heutigen Speicherort (Bind-Mount `./config`), Zero-Config-Bootstrap und Section-Save aus Phase 4 funktionieren pro Agent-Verzeichnis weiter; Esso-Installation überlebt das Update ohne Neukonfiguration.

### D-48: Fernet + Key-Datei, kein Master-Passwort (locked)
Symmetrische Verschlüsselung mit `cryptography.fernet`. Secret-Werte stehen als `enc:<token>` in der `.env`. Key-Datei (z. B. `/config/.secret_key`) wird beim ersten Start generiert, `chmod 600`, liegt im selben Config-Bind-Mount. WebUI verschlüsselt beim Save, Agent entschlüsselt beim Config-Load. Klartext-Legacy-Werte werden erkannt und beim nächsten Save verschlüsselt. Kein Master-Passwort-Prompt.
**Why:** Nutzer will es "einfach verschlüsselt"; Master-Passwort würde Zero-Config und Autostart nach Reboot brechen. Schutzumfang (Datei-/Backup-Leaks, nicht Root-Zugriff auf den Host) wird ehrlich dokumentiert (SEC-03).

### D-49: LLM-Provider pro Agent, Modell-Defaults hart verdrahtet (locked)
`LLM_PROVIDER` + `LLM_API_KEY` sind Felder der Agent-`.env` (pro Agent unabhängig). Kein Modell-Auswahlfeld im UI — pro Provider ein fest verdrahtetes Classify+Draft-Modellpaar (Anthropic → Haiku 4.5 / Sonnet 4.6; OpenAI/Google-Äquivalente im Research verifizieren). Adapter-Modul im Agent (`llm.py` o. ä.), `classify.py`/`generate.py` rufen nur noch den Adapter.
**Why:** UI bleibt schlank (Betreiber ist kein LLM-Experte), Modellpflege ist Code-Sache; Provider-Wahl pro Agent erlaubt gemischte Setups.

### D-50: Dropdown-Semantik + Status-Übersicht (locked)
Agent-Dropdown leer bei frischer Installation → Formular startet im "Neuen Agent anlegen"-Modus. Auswahl eines Agenten lädt dessen Formular (HTMX, ohne Full-Reload passend zum Section-Save-Muster). Löschen mit Zwei-Stufen-Bestätigung (wie Zero-Reset aus UI-08) entfernt Config-Verzeichnis und State (Aktiv-Flag vorher aus → Agent fällt aus dem nächsten Poll-Zyklus). Der Status-Bereich zeigt eine **Übersicht aller Agenten** (bestätigt per Rückfrage 2026-07-16): je Zeile Läuft/Gestoppt (Aktiv-Flag + Last-Poll-Heartbeat), letzter Poll, eigener Start/Stop-Button.

### Claude's Discretion
- Exakte Slug-Regeln für Agent-IDs, Kollisionshandling
- HTMX-Detailverhalten (Partial-Templates, Reload-Grenzen) beim Agent-Wechsel
- Aufteilung/Benennung der neuen Module (z. B. `agent/src/llm.py`, `webui/src/agents_io.py`, `webui/src/crypto.py`)
- Exakte Mechanik des Aktiv-Flags (Key in der Agent-`.env` vs. Marker-Datei) und des Heartbeats für die "Läuft"-Anzeige
- Struktur des Multi-Account-Poll-Zyklus in `main.py` (sequentiell reicht; Fehler-Isolation pro Agent Pflicht; Wait-for-Config-Loop generalisieren auf "0 konfigurierte Agenten")
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
- `webui/src/docker_ctrl.py` — Docker-SDK-Wrapper (bleibt Single-Container: globales Start/Stop/Restart + Update des einen `agent`-Service)
- `webui/src/state_reader.py` — SQLite-Ro + agent_status.json-Ro (wird pro-Agent-fähig)
- `webui/docker-entrypoint.sh` — Zero-Config-Seeding (Migration-Hook)
- `webui/src/templates/index.html` + `_status_card.html` — Formular mit Section-Save (bekommt Agent- + Provider-Dropdown)
- `agent/src/config.py` — .env/context/prompts-Loader (bekommt Entschlüsselung + LLM_*-Vars)
- `agent/src/classify.py`, `agent/src/generate.py` — Anthropic-Calls (werden auf Adapter umgestellt)
- `agent/src/main.py` — Polling-Loop + Wait-for-Config (wird Multi-Account: Agenten-Discovery aus `/config/agents/*/`, Aktiv-Flag-Filter, Fehler-Isolation pro Agent)
- `agent/src/state.py`, `agent/src/imap_client.py` — werden pro Agent instanziiert (State-DB-Pfad + IMAP-Verbindung je Agent)
- `agent/docker-compose.yml` — beide Services bleiben unverändert bestehen (ein `agent`-Service)

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
- Status-Bereich: Übersichts-Liste aller Agenten (je Zeile Status + letzter Poll + Start/Stop-Button)
- `install-autostart.sh`/systemd: unverändert — es gibt weiterhin nur die zwei Compose-Services `agent` + `webui`, Reboot-Verhalten wie in Phase 4
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
