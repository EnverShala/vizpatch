---
id: chat-confirmation-gate-reduce
title: Bestätigungs-Gate im Chat reduzieren/abschaltbar machen (Betreiber-Feedback)
created: "2026-07-21"
status: pending
area: webui
severity: feedback
defer: true
found_during: phase-8-live-abnahme
---

## Feedback (Betreiber 2026-07-21)

Der Agent fragt bei Aktionen zu oft nach Bestätigung ("soll ich?"). Das soll
**weniger werden oder ganz weg**. Begründung des Betreibers: Der Agent kann ohnehin
**keine Mails senden** und **nichts endgültig löschen** (Papierkorb-Move ist
reversibel, kein Expunge) → geringer Schaden. Zudem nur **ein vertrauenswürdiger
Nutzer** (Stationsleitung).

## Ist-Zustand

- CTOOL-04: destruktive Aktionen (Papierkorb-Move) verlangen ein Zwei-Schritt-
  Bestätigungs-Token (HMAC über `session_id`, `chat_tools.py`).
- Bereits am 2026-07-19 gelockert: Bestätigung nur **einmal pro Chat-Sitzung**
  (nicht pro Aktion).

## Empfehlung

Config-Schalter `CHAT_REQUIRE_TRASH_CONFIRM` (bzw. per Agent), **Default an** für
andere Kunden, für diese Installation **aus** → Agent verschiebt ohne Rückfrage in
den Papierkorb (reversibel). Alternativ Gate ganz entfernen. Kein Gate ist bei
den aktuell rein reversiblen Aktionen vertretbar.

## Ripple — mitziehen

Änderung berührt: `chat_tools.py` (Gate-Logik), `webui/prompts/chat-system.txt`
(die Regel „erst bestätigen lassen"), sowie die Rechtstexte, die das Gate erwähnen
(`_datenschutz.html` Ziffer 6, `AVV-CHECKLIST.md` §6.2) — dort den Wortlaut an das
neue Verhalten angleichen (sonst Doku-Drift).

## Nicht jetzt

Prompt-relevante/compliance-berührende Änderung → sauber nach Phase-8-Abschluss
umsetzen (oder auf ausdrücklichen Wunsch sofort).
