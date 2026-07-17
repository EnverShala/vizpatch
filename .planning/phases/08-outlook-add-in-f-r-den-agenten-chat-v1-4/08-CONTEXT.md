# Phase 8: Outlook-Add-in für den Agenten-Chat (v1.4) — Context

**Gathered:** 2026-07-17
**Status:** Ready for planning
**Source:** Lean-Pfad — Roadmap-Entscheidungen + Betreiber-Freigabe (analog Phase 7)

<domain>
## Phase Boundary

Der Agenten-Chat aus Phase 7 wird als **Office-Add-in (Office.js, Taskpane)** in Outlook nutzbar —
neues Outlook (Windows/Mac), Outlook im Web (OWA). Das Add-in ist eine **dünne Hülle**: es lädt das
einbettbare, chrome-lose Chat-Partial (`/chat/{agent_id}/embed`, CHAT-05) vom Kundenserver und reicht
die gerade geöffnete Mail (Betreff/Absender/Body via Office.js) als Kontext in den Chat — über den in
Phase 7 gebauten Hook (`window.vizpatchGetMailContext` → `mail_context`-Feld der `/chat`-API, D-65).

Liefergegenstand: Manifest, Taskpane-Seite, Sideloading-/Central-Deployment-Doku, HTTPS-Runbook-Kapitel.

**NICHT in Scope:** Der Chat selbst (Phase 7); Mail senden/ändern (Kein-Auto-Send, rein lesend);
Änderungen an der `/chat`-API (Phase 7 hat `mail_context` bereits vorgesehen — keine API-Änderung nötig).
</domain>

<decisions>
## Implementation Decisions (locked)

### Serving-Architektur (löst den Phase-7-CSP-Aufschub)
- **D-66:** Die Taskpane-Seite wird **vom bestehenden WebUI-Container selbst ausgeliefert** (neue
  Route(n), z. B. `GET /addin/taskpane.html` + statische Add-in-Assets). Dadurch ist die Taskpane
  **same-origin** mit dem Chat-Partial → **kein CORS, kein Cross-Origin-iframe-CSP-Problem**. Das ist
  die bewusste Auflösung des in Phase 7 (07-04 scope_note) nach Phase 8 verschobenen frame-ancestors-Themas:
  Taskpane und `/chat/.../embed` liegen unter derselben HTTPS-Origin, daher genügt ein
  `frame-ancestors 'self'` (bzw. gezielt die Office-Host-Origins), keine fremde Origin muss freigegeben werden.

### Manifest & Kompatibilität (OUT-01)
- **D-67:** Klassisches **XML-Add-in-Manifest** (breiteste Outlook-Kompatibilität: neues Outlook + OWA
  heute stabil). Sideloading für neues Outlook + OWA dokumentiert; zentrale M365-Admin-Verteilung als
  Alternative beschrieben. Das Manifest ist **pro Kunde templatisiert** über die öffentliche HTTPS-Basis-URL
  des Kundenservers (Config/Env, z. B. `ADDIN_BASE_URL`) — die URL variiert je Installation.

### Taskpane-Einbettung & Auth (OUT-02)
- **D-68:** Die Taskpane **iframed** `/chat/{agent_id}/embed` (same-origin, D-66). Agent-Auswahl über ein
  kleines Dropdown in der Taskpane (nutzt eine schlanke Liste der Agenten). Auth = **bestehendes
  WebUI-Auth-Regime** (optionaler Basic-Auth/Session) — der Browser/Outlook-Webview handhabt den
  Auth-Prompt im iframe; der Fluss wird dokumentiert. Kein neues Auth-System.

### Mail-Kontext (OUT-03)
- **D-69:** Office.js liest die geöffnete Mail (`Office.context.mailbox.item`: `subject`,
  `from.emailAddress`, `body.getAsync(text)`) und übergibt sie an den iframe-Chat via **`postMessage`**;
  `chat.js` (Phase 7) überschreibt `window.vizpatchGetMailContext`, sodass der Kontext ins `mail_context`-
  Feld der `/chat`-API fließt (D-65). Rein lesend — keine Office-Write-APIs.

### HTTPS & Read-only (OUT-04)
- **D-70:** HTTPS-Runbook-Kapitel für den Kundenserver: **Reverse-Proxy vor der WebUI** (z. B. Caddy mit
  selbstverwaltetem/Let's-Encrypt-Zertifikat), Ports, `frame-ancestors`-Hinweis. Add-in ist strikt
  **rein lesend** (Kein-Auto-Send) — dokumentiert und strukturell (keine Office-Write- / Mail-Send-Aufrufe).

### Abnahme
- **D-71:** Manifest-Validierung, Sideloading und HTTPS-Erreichbarkeit sind ein **menschlicher Checkpoint**
  (brauchen echtes Outlook + HTTPS-Server) — analog den Abnahme-Checkpoints in Phase 6/7. Der baubare Teil
  (Manifest, Taskpane, Doku, automatisierbare Tests) wird vollständig geliefert; die Live-Sideload-Abnahme
  bleibt dem Betreiber/Kunden.

### Claude's Discretion
- Genaue Route-/Datei-Namen, Taskpane-Layout/CSS, postMessage-Event-Format, Manifest-GUID/Icons,
  Caddyfile-Details. Executor wählt konsistent mit bestehenden WebUI-Mustern (FastAPI-Routen, static/).
</decisions>

<canonical_refs>
## Canonical References

**Downstream-Agenten MÜSSEN diese vor dem Planen/Implementieren lesen.**

### Phase-7-Chat (die Basis, auf der Phase 8 aufsetzt)
- `webui/src/main.py` — Chat-Routen (`/chat/{id}/embed`, `/chat/{id}/send`), auth-Dependency, Routen-Muster
- `webui/src/templates/chat.html` + `webui/src/templates/_chat.html` — das chrome-lose Partial, das die Taskpane iframed
- `webui/static/chat.js` — enthält `window.vizpatchGetMailContext`-Hook (Phase-8-Erweiterungspunkt) + Session-Historie
- `webui/src/chat.py` — `/chat`-Server-Seite inkl. optionalem `mail_context` (D-65)
- `webui/src/auth.py` — Auth-Regime, an das die Add-in-Routen sich halten
- `webui/src/agents_io.py` — Agentenliste für das Taskpane-Dropdown

### WebUI-Serving & Deployment
- `webui/Dockerfile`, `webui/src/main.py` (StaticFiles-Mount-Muster), `webui/static/` — wie Assets ausgeliefert werden
- `deployment/docker-compose.phase4.yml`, `deployment/README.phase4.md`, `deployment/kunde-env.example` — Deployment-Kontext für ADDIN_BASE_URL + HTTPS
- `.planning/phases/02-deployment-beim-kunden/RUNBOOK.md` — bestehendes Runbook, in das das HTTPS-Kapitel passt (oder ein neues deployment/-Doc)

### Roadmap / Requirements
- `.planning/ROADMAP.md` — Phase 8 Goal + 5 Success Criteria + Risiken
- `.planning/REQUIREMENTS.md` — OUT-01 … OUT-04
</canonical_refs>

<deferred>
## Deferred Ideas
- Änderungen an der `/chat`-API → nicht nötig (Phase 7 D-65 hat `mail_context` vorgesehen).
- Unified JSON-Manifest → NICHT (D-67, XML für breite Kompatibilität in v1.4).
- Add-in schreibt/sendet Mails → NICHT (D-70, Kein-Auto-Send).
</deferred>

---

*Phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4*
*Context gathered: 2026-07-17 via Lean-Pfad (Roadmap + Betreiber-Freigabe)*
