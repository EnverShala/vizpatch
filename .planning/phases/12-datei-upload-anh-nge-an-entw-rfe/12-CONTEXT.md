# Phase 12: Datei-Upload-Anhänge an Entwürfe — Context

**Gathered:** 2026-07-21
**Status:** Ready for planning
**Source:** Synthetisiert aus `.planning/todos/pending/chat-draft-attachments.md` (Betreiber-Entscheidung 2026-07-21) + 2 Architektur-Weichen (plan-phase-Discuss)

<domain>
## Phase Boundary

Der agentische WebUI-Chat (Phase 9, `webui/src/chat_tools.py`) bekommt die Fähigkeit,
**Datei-Anhänge an Entwürfe** zu hängen. Der Betreiber lädt ad-hoc eine Datei im Chat hoch;
der Agent ruft ein neues Werkzeug `entwurf_mit_anhang(...)` auf, das den Entwurf als
MIME-multipart baut und per IMAP APPEND im Drafts-Ordner ablegt. **Kein Senden** — der
Anhang landet ausschließlich am Entwurf, der Betreiber prüft und sendet wie immer selbst.

**In Scope:**
- Ad-hoc-Upload-Endpoint in der WebUI (alle Dateitypen, Größenlimit)
- Neues Chat-Werkzeug `entwurf_mit_anhang` (MIME-multipart + IMAP APPEND + Threading)
- Chat-UI-Upload-Widget (HTMX), turn-gebundene Dateiverfügbarkeit
- Kein-Auto-Send-Absicherung + tmp-Cleanup

**Out of Scope (bewusst):**
- Outlook-Add-in-Upload (separater COM/VSTO-Client — Folge-Todo)
- Varianten A (kuratierter Ordner) und B (Anhang aus vorhandener Mail weiterreichen)
- Dateityp-Whitelist (Betreiber will explizit „alle möglichen Dateien")
- Auto-Send jeder Art (Grundprinzip-Bruch)
</domain>

<decisions>
## Implementation Decisions

### Quelle des Anhangs (gelockt)
- **D-90:** **Variante C — Ad-hoc-Upload, ALLE Dateitypen.** Begründung (Todo): Der Agent
  wird ausschließlich von der Stationsleitung (einzelner vertrauenswürdiger Nutzer) bedient.
  Der Anhang kommt direkt vom Betreiber per Upload, nicht aus Mail-Inhalt → Prompt-Injection-
  Risiko der Quelle entfällt weitgehend. Keine Dateityp-Whitelist.

### Scope (Discuss-Weiche 1)
- **D-91:** **Nur WebUI.** Upload-Endpoint + Chat-Upload-Widget ausschließlich in der WebUI.
  Das Outlook-Add-in bleibt in dieser Phase unberührt; „Weiterreichen aus dem Add-in" wird
  als Folge-Todo zurückgestellt (kleinster sauberer Slice, schnell live).

### Anhang-Fluss (Discuss-Weiche 2)
- **D-92:** **LLM-Werkzeug `entwurf_mit_anhang`.** Nutzer lädt Datei hoch → der Agent ruft
  im Chat-Tool-Loop ein neues Werkzeug auf (analog `entwurf_erstellen`/`entwurf_bearbeiten`),
  das die hochgeladene Datei als Base64-MIME-Part an einen Entwurf hängt und per IMAP APPEND
  ablegt. Nahtlos im bestehenden agentischen Tool-Loop, kein paralleler UI-Pfad.

### Aufbau / MIME
- **D-93:** Entwurf wird als **RFC-5322 MIME-multipart** gebaut — analog den bestehenden
  Helfern `_build_new_draft`/`_build_edited_draft` in `webui/src/chat_tools.py` und dem
  Muster in `agent/src/draft.py`. Anhang = separater Base64-kodierter MIME-Part.
  Threading-Header (`In-Reply-To`/`References`) erhalten wie bei `entwurf_bearbeiten`.

### Größenlimit
- **D-94:** Konfigurierbares `MAX_ATTACHMENT_MB` (konservativer Default **15**). Grund: Nicht
  Outlook, sondern der **Mail-Provider** limitiert beim späteren Senden (~20–25 MB, teils 35);
  Base64 bläht ~+33 %, plus IMAP-APPEND-Limits mancher Server. Das Werkzeug prüft die Rohgröße
  und lehnt Überschreitung mit klarer Meldung ab.

### Sicherheit / Kein-Auto-Send
- **D-95:** **Kein-Auto-Send bleibt strukturell.** Kein SMTP, kein `.Send(`, keine
  Versand-Route. Der bestehende AST-Kein-Auto-Send-Wächter (Phase 9, CTOOL-05) muss das neue
  Werkzeug abdecken (grün gegen `entwurf_mit_anhang`). Temporäre Upload-Dateien werden nach dem
  APPEND im `finally`-Block gelöscht. Upload nur für authentifizierte WebUI-Session.
- **D-96:** **Dateiinhalt geht NICHT ans LLM.** Der Agent sieht nur Dateiname/Metadaten (im
  Tool-Result), nie den Datei-Rohinhalt. Streaming-Upload (kein Full-Memory-Load).

### Claude's Discretion
- Genaue Referenzierung der hochgeladenen Datei im Chat-Turn (Session-/Turn-Handle, Pfad in
  `/config`-Tmp o. ä.) — Researcher/Planner wählen das robusteste Muster gegen den vorhandenen
  Chat-/Session-Code (`webui/src/chat.py`, Session-Autorisierung in `chat_tools.py`).
- MIME-Typ-Erkennung des Anhangs (mimetypes/magic) — Best-Effort, kein Blocker.
- Fehler-/Statusdarstellung im Chat-UI bei Ablehnung (Limit überschritten, Upload-Fehler).
</decisions>

<canonical_refs>
## Canonical References

**Downstream-Agenten MÜSSEN diese vor Planung/Umsetzung lesen.**

### Bestehende Chat-Werkzeuge & Draft-Bau (Analogien)
- `webui/src/chat_tools.py` — `entwurf_erstellen`, `entwurf_bearbeiten`, Helfer
  `_build_new_draft` / `_build_edited_draft`, Threading-Header, Drafts-Ordner-Resolution,
  Session-Autorisierung, Tool-Schema-Registry
- `webui/src/chat.py` — agentischer Tool-Loop, SSE-Streaming, `build_chat_prompt`
- `agent/src/draft.py` — RFC-5322-Aufbau + IMAP-APPEND-Muster (Referenz für MIME)

### Upload-Muster (Bestand)
- `.planning/phases/04-web-ui-multi-kunde/04-RESEARCH.md` (Sektion „FastAPI Upload-Handler",
  „Tarball-Upload mit Streaming") — Streaming-`UploadFile` + `tempfile`-Muster; **Hinweis:**
  die frühere `/update/upload`-Route wurde 2026-07-20 entfernt (siehe REQUIREMENTS UI-05),
  das Streaming-Muster bleibt aber die Referenz

### Kein-Auto-Send-Wächter
- Phase-9-AST-Wächter (CTOOL-05) — muss `entwurf_mit_anhang` mit abdecken
- `webui/src/chat_tools.py` — Bestätigungs-/Session-Gate-Muster (falls relevant)

### Quelle der Entscheidung
- `.planning/todos/pending/chat-draft-attachments.md` — Betreiber-Beschluss Variante C
</canonical_refs>

<specifics>
## Specific Ideas

- Werkzeugname: `entwurf_mit_anhang` (deutsches Werkzeug-Naming wie alle Chat-Tools).
- Default `MAX_ATTACHMENT_MB=15`, konfigurierbar (env, wie andere Agent-/WebUI-Configs).
- Anhang als eigener Base64-MIME-Part; Body/Text-Part wie bei `entwurf_erstellen`/`-bearbeiten`.
- Nach erfolgreichem APPEND: temporäre Upload-Datei löschen (finally).
</specifics>

<deferred>
## Deferred Ideas

- **Add-in-Upload** (COM/VSTO-Client, „Weiterreichen aus dem Add-in") — separater Folge-Todo.
- **Variante A** (kuratierter Anhang-Ordner `/config/agents/<id>/attachments/`) und **Variante B**
  (Anhang aus vorhandener Postfach-Mail weiterreichen) — nicht jetzt.
- **Datenschutzerklärung/AVV-Wortlaut** zur Upload-Fähigkeit — geht in die gebündelte DSB-Abnahme
  am Ende der funktionalen Phasen (Betreiber-Entscheidung: Rechtstext gesammelt, nicht pro Feature).
</deferred>

---

*Phase: 12-datei-upload-anh-nge-an-entw-rfe*
*Context gathered: 2026-07-21 via plan-phase Discuss (Todo-Synthese + 2 Architektur-Weichen)*
