# Phase 7: Agenten-Chat im WebUI (v1.3) — Context

**Gathered:** 2026-07-17
**Status:** Ready for planning
**Source:** Lean-Pfad — Roadmap-Entscheidungen + Betreiber-Freigabe (Planungstiefe „lean", Limit-Defaults dem Assistenten überlassen)

<domain>
## Phase Boundary

Ein Chat-Bereich **pro Agent** im bestehenden WebUI. Der Betreiber chattet mit einem LLM-Assistenten,
der `context.md`, `style.md` und den Agent-Status kennt (letzte Polls, Drafts-Ordner, Fehler). Zweck:
Support-Fragen („warum hat Mail X keinen Draft bekommen?"), Umformulierungen, `context.md`-Pflege.

Der Chat wird bewusst als **einbettbares, chrome-loses Partial + saubere `/chat`-API** gebaut — Phase 8
(Outlook-Add-in) ist genau dieser Chat, in Outlook eingebettet. Die `/chat`-API akzeptiert daher schon
in Phase 7 einen **optionalen Mail-Kontext** (Betreff/Absender/Body), damit Phase 8 (OUT-03) nur noch
Office.js daran anschließen muss — keine API-Änderung in Phase 8 nötig.

**NICHT in Scope:** Persistenz des Verlaufs in einer DB; der Chat kann keine Mails senden/ändern
(Kein-Auto-Send gilt auch hier); kein zweiter LLM-Sonderweg neben dem Phase-5-Adapter; HTTPS/Outlook
(das ist Phase 8).
</domain>

<decisions>
## Implementation Decisions (locked)

### Verlauf & UI (CHAT-01)
- **D-58:** Chat-Verlauf lebt ausschließlich in der Browser-Session (keine neue DB, kein SQLite-Schema).
  Reset-Button leert den Verlauf. Auth-geschützt wie alle WebUI-Routen (bestehendes `auth.py`-Regime).
- HTMX + SSE-Streaming (SSE-Extension), Ton/Look konsistent mit bestehendem `index.html`.

### LLM-Anbindung (CHAT-03)
- **D-59:** Chat ruft den **Phase-5-LLM-Adapter** (`webui/src/llm.py::llm_call`) mit Provider/Key des
  **gewählten Agenten** (aus dessen `.env`, Fernet-entschlüsselt via bestehendem `agents_io`/`crypto`).
  Kein separater Anthropic-Sonderweg. Prompt-Injection-Anker analog `webui/prompts/context-seed.txt`.

### System-Prompt / Wissen (CHAT-02)
- **D-64:** System-Prompt injiziert `context.md` + `style.md` (falls vorhanden) + kompakten Agent-Status
  (letzte Polls, Drafts-Ordner, letzte Fehler) via bestehendem `state_reader`. Chat ist rein beratend.

### Kosten-/Missbrauchsschutz (CHAT-04)
- **D-60:** Rate-Limit **20 Nachrichten/Minute** pro Session, **max 2000 Token** pro Antwort,
  Verlaufs-Trunkierung auf ein festes Token-Budget im Prompt. Alles via `.env` konfigurierbar
  (`CHAT_RATE_LIMIT_PER_MIN=20`, `CHAT_MAX_TOKENS=2000`, `CHAT_HISTORY_TOKEN_BUDGET`). Werte sind ein
  Kostensicherheitsnetz (Chat wird selten genutzt) — Betreiber hat die Default-Wahl dem Assistenten überlassen.
- **D-63:** Kein-Auto-Send im Chat: der Chat hat **keine** Mail-schreib-/sende-Fähigkeit (kein Tool-Call,
  der IMAP APPEND/SMTP auslöst). Rein lesender Assistent.

### Einbettbarkeit / Phase-8-Vorarbeit (CHAT-05)
- **D-61:** Chat-Frontend als **eigenständiges, chrome-loses Partial** unter eigener Route
  (z. B. `GET /chat/{agent_id}/embed`) — **keine externen Ressourcen** (kein CDN, alles inline/lokal,
  wie htmx.min.js bereits lokal vorliegt). Der Haupt-WebUI-Chat rendert dasselbe Partial in seiner Chrome.
  Nachweis: Einbettung in einer nackten Test-HTML-Seite funktioniert.
- **D-62:** SSE über einen dedizierten Streaming-Endpoint (FastAPI `StreamingResponse`). Erster Plan =
  Walking-Skeleton, das echtes SSE-Streaming end-to-end zeigt, bevor Wissen/Limits draufkommen.
- **D-65:** Die `/chat`-Sende-API akzeptiert ein **optionales `mail_context`-Feld** (Betreff/Absender/Body).
  In Phase 7 ungenutzt/leer; in Phase 8 füllt Office.js es mit der geöffneten Mail (OUT-03). Kein
  Nachrüsten der API in Phase 8.

### Claude's Discretion
- Konkrete Route-Namen, SSE-Event-Format, HTMX-Verdrahtung, Rate-Limit-Implementierung (In-Memory pro
  Prozess reicht — Single-Container), Prompt-Wortlaut. Executor wählt konsistent mit bestehenden Mustern.
</decisions>

<canonical_refs>
## Canonical References

**Downstream-Agenten MÜSSEN diese vor dem Planen/Implementieren lesen.**

### LLM-Adapter & Secrets (Phase 5)
- `webui/src/llm.py` — provider-agnostischer `llm_call`, Modell-Defaults (Chat nutzt das Draft-Modell des Agenten)
- `webui/src/agents_io.py` — per-Agent `.env`/`context.md`/`style.md`-I/O, `read_env_raw`
- `webui/src/crypto.py` — Fernet-Entschlüsselung der Secrets

### WebUI-Muster
- `webui/src/main.py` — bestehende FastAPI-Routen, auth-Dependency, HTMX-Endpoints, Section-Save
- `webui/src/auth.py` — Auth-Regime (optionaler Login), auf das alle Chat-Routen sich stützen
- `webui/src/state_reader.py` — Agent-Status (letzte Polls, Drafts-Ordner, Fehler) für CHAT-02
- `webui/src/templates/index.html` — UI-Muster (HTMX, Fieldsets, Section-Save), in das der Chat integriert wird
- `webui/prompts/context-seed.txt` — Prompt-Injection-Anker-Muster (Vorbild für den Chat-System-Prompt)
- `webui/static/htmx.min.js` — lokal eingebundenes htmx (Vorbild: SSE-Extension ebenfalls lokal einbinden, kein CDN)
- `webui/src/style_extract.py` — Beispiel für einen sauberen Service-Layer (Muster für einen Chat-Service)

### Roadmap / Requirements
- `.planning/ROADMAP.md` — Phase 7 Goal + 5 Success Criteria + Risiken
- `.planning/REQUIREMENTS.md` — CHAT-01 … CHAT-05 (und OUT-03 für die Mail-Kontext-Vorarbeit)
</canonical_refs>

<deferred>
## Deferred Ideas
- Persistenter Chat-Verlauf / History-Export → bewusst NICHT (D-58, keine neue DB in v1.3).
- Chat-„Actions" (Mail senden, context.md automatisch schreiben) → NICHT (D-63, Kein-Auto-Send).
- HTTPS/Reverse-Proxy + Office.js → Phase 8.
</deferred>

---

*Phase: 07-agenten-chat-im-webui-v1-3*
*Context gathered: 2026-07-17 via Lean-Pfad (Roadmap + Betreiber-Freigabe)*
