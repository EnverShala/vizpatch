# Phase 9: Agentischer Chat mit Postfach-Werkzeugen (v1.5) — Context

**Gathered:** 2026-07-18
**Status:** Ready for planning
**Source:** Lean-Pfad — Betreiber-Entscheidung im Live-Test (voller Umfang inkl. Löschen)

<domain>
## Phase Boundary

Der Chat aus Phase 7 wird von „rein beratend" zu „handelnd": das LLM erhält **Werkzeuge (Tool-Use)**,
mit denen es auf ausdrückliche Anweisung des Betreibers das Postfach bearbeitet — Mails suchen/lesen,
Entwürfe auflisten/lesen/bearbeiten und Mails/Entwürfe **in den Papierkorb verschieben**. Der Chat läuft
weiter über den gewählten Agenten (dessen Provider/Key + IMAP-Zugang).

**NICHT in Scope:** Senden von Mails (Kein-Auto-Send, strukturell kein Sende-Tool); endgültiges Löschen
(Expunge) — Löschen = Move in den Papierkorb, reversibel; neue DB/Historie (Verlauf bleibt Browser-Session,
D-58); Outlook/HTTPS (Phasen 7/8 unverändert).
</domain>

<decisions>
## Implementation Decisions (locked)

### Adapter & Architektur
- **D-72:** Der Chat wird agentisch über **LLM-Tool-Use** (Schleife: Tool-Request → IMAP-Ausführung →
  Tool-Result → LLM weiter → finale Antwort). **Start mit Anthropic** (Esso-Key). OpenAI/Google: entweder
  Tool-Use oder **sauberer Fallback** auf den beratenden Chat (kein Absturz).
- **D-73 (Drift-Guard!):** Die Tool-Use-Logik kommt in ein **webui-eigenes Modul** (Erweiterung von
  `webui/src/chat.py` bzw. neues `webui/src/chat_tools.py`), **NICHT** in `webui/src/llm.py` —
  `llm.py`/`pii.py`/`crypto.py`/`provider_config.py` sind byte-identische Drift-Guard-Zwillinge von
  `agent/src/` und dürfen nicht divergieren (gleiche Begründung wie Phase-7-D-59).

### Werkzeuge (per gewähltem Agent, mit entschlüsselten IMAP-Creds)
- **D-74:** Read-only-Tools: `mails_suchen(query, folder=INBOX, limit)`, `mail_lesen(uid)`,
  `entwuerfe_auflisten()`, `entwurf_lesen(uid)`.
- **D-75:** `entwurf_bearbeiten(uid, neuer_text[, neuer_betreff])` — legt die neue Fassung per IMAP-APPEND
  im Entwürfe-Ordner ab und verschiebt den alten Entwurf in den Papierkorb; **Threading-Header
  (In-Reply-To/References) bleiben erhalten**. Kein Senden.
- **D-76:** Destruktive Tools `mail_in_papierkorb(uid, folder)` / `entwurf_in_papierkorb(uid)` =
  **IMAP-Move in den Papierkorb** (SPECIAL-USE `\Trash` + `provider_config`-Fallback), **kein Expunge**
  (reversibel). Ausführung **nur mit `confirmed=true`**: ohne Bestätigung liefert das Tool ein
  „Bestätigung erforderlich"-Result mit exakter Zielbeschreibung (Betreff/Absender/Datum); das LLM nennt
  es dem Betreiber und ruft das Tool erst nach explizitem „ja" erneut mit `confirmed=true` auf. **Jede
  Löschung/Verschiebung wird protokolliert** (structured log).

### Sicherheit
- **D-77 (Kein-Auto-Send strukturell):** Der Werkzeugsatz enthält **kein** Sende-/SMTP-Tool; nur
  IMAP-SEARCH/FETCH/APPEND/MOVE. Reply-Versand ist nicht möglich.
- **D-78:** Mail-Inhalte laufen **vor** der LLM-Übergabe durch **PII-Redaction** (gleiches `pii.py`-Regime).
  Tool-Results werden als **untrusted DATA** markiert (Injection-Anker) — Mail-Inhalt darf das LLM nicht zu
  ungefragten (v. a. destruktiven) Tool-Aufrufen verleiten; destruktive Tools nie ohne Nutzer-Bestätigung.
- **D-79:** IMAP-Zugriff nutzt dieselbe per-Agent-Mechanik wie die Stil-Extraktion
  (`webui/src/style_extract.py`): Fernet-entschlüsselte Creds, Timeouts pro Operation, SPECIAL-USE-
  Ordnererkennung mit `provider_config`-Fallback.

### UX & Angleichung
- **D-80:** Der agentische Loop läuft serverseitig; SSE zeigt **Tool-Aktivität** („🔧 durchsuche Postfach…")
  plus die finale gestreamte Antwort. Rate-Limit/Token-Deckel (D-60) und Browser-Session-Verlauf (D-58)
  gelten weiter.
- **D-81:** Datenschutzerklärung (`_datenschutz.html`, Ziffer 6) und AVV-Verarbeitungszwecke
  (`AVV-CHECKLIST.md` §6.2) werden auf die **tatsächlichen** Fähigkeiten angeglichen (Löschen=Papierkorb,
  Bestätigungspflicht).

### Claude's Discretion
- Tool-Namen/Schemas im Detail, SSE-Event-Format der Tool-Aktivität, max. Tool-Runden pro Anfrage
  (Endlosschutz), UID- vs. Message-ID-Referenzierung, genaue Suchsyntax. Executor wählt konsistent mit
  bestehenden Mustern.
</decisions>

<canonical_refs>
## Canonical References

**Downstream-Agenten MÜSSEN diese vor dem Planen/Implementieren lesen.**

### Chat-Basis (Phase 7)
- `webui/src/chat.py` — `stream_chat`, `build_system_prompt`, `resolve_chat_target` (Provider/Key/Modell pro Agent)
- `webui/src/main.py` — Chat-Routen (`/chat/{id}/send`, `/embed`), SSE-Frames, `_parse_chat_history`
- `webui/prompts/chat-system.txt` — System-Prompt + Injection-Anker (erweitern um Werkzeug-Regeln)
- `webui/static/chat.js` — Frontend (Tool-Aktivitäts-Events anzeigen)

### IMAP & Sicherheit (Wiederverwendung)
- `webui/src/style_extract.py` — bestehende per-Agent-IMAP-Verbindung (Muster für Suchen/Lesen/Ordnererkennung)
- `webui/src/agents_io.py` — per-Agent `.env`/Creds, `read_env_raw`
- `webui/src/crypto.py` — Fernet-Entschlüsselung (Drift-Guard — nicht ändern)
- `webui/src/pii.py` — PII-Redaction (Drift-Guard — nicht ändern; nur aufrufen)
- `webui/src/provider_config.py` — Ordner-Fallback (Drift-Guard — nicht ändern; nur nutzen)

### Agent-seitige Referenz für IMAP-Muster (nur lesen, nicht ändern)
- `agent/src/imap_client.py` — IMAP-Wrapper, `detect_drafts_folder`, APPEND/Move-Muster
- `agent/src/draft.py` — RFC-5322 + Threading (In-Reply-To/References) für `entwurf_bearbeiten`

### Angleichung
- `webui/src/templates/_datenschutz.html` (Ziffer 6) · `.planning/phases/02-deployment-beim-kunden/AVV-CHECKLIST.md` (§6.2)

### Roadmap / Requirements
- `.planning/ROADMAP.md` — Phase 9 Goal + 6 Success Criteria + Risiken · `.planning/REQUIREMENTS.md` — CTOOL-01…05
</canonical_refs>

<deferred>
## Deferred Ideas
- Endgültiges Löschen (Expunge) → NICHT (D-76, nur Papierkorb).
- Mail senden / Reply verschicken → NICHT (D-77, Kein-Auto-Send).
- Persistenter Chat-Verlauf → NICHT (D-58 bleibt).
- Volle OpenAI/Google-Tool-Use-Parität → best effort; Fallback genügt für v1.5.
</deferred>

---

*Phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5*
*Context gathered: 2026-07-18 via Lean-Pfad (Betreiber-Entscheidung im Live-Test)*
