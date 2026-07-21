---
id: chat-draft-attachments
title: Datei-Anhänge an Entwürfe (Kein-Auto-Send-konform) mit Größenlimit
created: "2026-07-21"
status: pending
area: webui
severity: idea
defer: true
found_during: phase-8-live-abnahme
---

## Idee (Betreiber-Wunsch 2026-07-21)

Der Agent soll Dateianhänge „mitschicken" können — unter Beachtung der Outlook-/
Provider-Dateigrößengrenze.

## WICHTIG — Kein-Auto-Send bleibt

Das Produktprinzip ist „nie senden, nur Entwürfe" (CLAUDE.md). Umsetzbar ist also
NICHT „versenden", sondern: der Agent **hängt eine Datei an einen ENTWURF an**; der
Betreiber prüft + sendet wie immer selbst. Echtes Auto-Senden wäre ein
Grundprinzip-Bruch und bräuchte eine explizite Betreiber-/DSB-Entscheidung.

## Zentrale Designfrage — Woher kommt die Datei?

- **(A) Kuratierter Anhang-Ordner pro Agent** `/config/agents/<id>/attachments/`
  (z. B. Preisliste.pdf, Formular.pdf) — Agent wählt aus freigegebener Liste.
  **Empfohlen** (Tankstelle): sicher, vorhersehbar, kein Upload-Weg, kein
  Injection-Risiko (nur freigegebene Dateien anhängbar).
- (B) Anhang aus einer vorhandenen Postfach-Mail weiterreichen.
- (C) Ad-hoc-Upload über WebUI/Add-in.

## Umsetzungsskizze (kompatibel)

- Neues Werkzeug `entwurf_mit_anhang(...)` in `chat_tools.py`: baut den Entwurf als
  RFC-5322 **MIME multipart** (analog `agent/src/draft.py`/`entwurf_bearbeiten`),
  Anhang als Base64-MIME-Part, per IMAP APPEND in Drafts. Kein SMTP, kein Send.
- Threading (In-Reply-To/References) wie bei `entwurf_bearbeiten` erhalten.

## Größenlimit (Betreiber-Hinweis beachten)

- Nicht „Outlook" limitiert primär, sondern der **Mail-Provider** beim späteren
  Senden (meist ~20–25 MB, teils 35 MB). Base64 bläht ~+33 % → Rohdatei sicher
  ~15–18 MB. Zusätzlich IMAP-APPEND-Limits mancher Server.
- Werkzeug prüft Rohgröße, lehnt Überschreitung ab; konfigurierbares
  `MAX_ATTACHMENT_MB` (konservativer Default, z. B. 15).

## Entscheidung (2026-07-21, Betreiber)

**Variante C — Ad-hoc-Upload, ALLE Dateitypen.** Begründung: Der Agent wird
ausschließlich von der **Stationsleitung** genutzt (macht auch das gesamte Büro),
also ein einzelner vertrauenswürdiger Nutzer. Der Anhang kommt damit direkt vom
Betreiber (Upload), nicht aus Mail-Inhalt → das Prompt-Injection-Risiko der
Quelle entfällt weitgehend.

Umsetzungsfolgen für C:
- Upload-Endpoint im WebUI (und Weiterreichen aus dem Add-in), Datei landet
  temporär serverseitig, wird als MIME-Part in den Entwurf gebaut (IMAP APPEND).
- Keine Dateityp-Whitelist gewünscht („alle möglichen Dateien") — trotzdem
  Größenlimit `MAX_ATTACHMENT_MB` (~15, Base64 +33 %) und temporäre Dateien nach
  dem APPEND wieder löschen. Kein-Auto-Send bleibt (Anhang nur am Entwurf).

## Nicht jetzt

Eigenes Feature (eigene Phase/Plan) nach Phase-8-Abschluss. Quelle = C ist entschieden.
