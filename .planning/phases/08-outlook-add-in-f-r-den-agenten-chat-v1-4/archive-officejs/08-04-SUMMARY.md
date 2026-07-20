---
phase: 08-outlook-add-in-f-r-den-agenten-chat-v1-4
plan: 04
status: task-1-complete-task-2-pending-human-checkpoint
requirements-completed: []
date: 2026-07-17
---

# 08-04 SUMMARY — Sideload-Abnahme (Checkpoint)

## Task 1 — Automatisches Vor-Gate ✅ GRÜN

Die volle Sicherheitsnetz-Suite wurde als Vor-Gate ausgeführt (keine Code-Änderung, reine Verifikation):

| Suite | Ergebnis |
|---|---|
| webui volle Suite | **288 passed, 3 skipped** |
| Drift-Guards (`test_llm_sync`, `test_model_defaults_sync`) | **2 passed** |
| Add-in-Tests (`test_endpoints_addin`, `test_addin_readonly`, `test_addin_docs`, `test_security`) | **24 passed** |
| agent (Regressionscheck) | **109 passed, 1 skipped** |

Alle Akzeptanzkriterien von Task 1 erfüllt (≥ Baseline 256/3 zzgl. Add-in-Tests; Add-in- und Drift-Guard-Tests grün). Die Live-Abnahme darf starten.

## Task 2 — Live-Sideload-Abnahme ⏳ PENDING (blocking human checkpoint, D-71)

**Nicht durch den Assistenten abschließbar.** Braucht echtes Outlook (neues Outlook + OWA) und einen HTTPS-erreichbaren Server (Reverse-Proxy gemäß `deployment/README.addin.md`, `ADDIN_BASE_URL` gesetzt). Der Betreiber führt die Schritte aus `08-04-PLAN.md` (Task 2, `how-to-verify`) durch:

1. HTTPS-Erreichbarkeit `/addin/taskpane.html` + `/addin/manifest.xml` (OUT-02/04)
2. Manifest offiziell validieren (`npx office-addin-manifest validate manifest.xml`), Permission `ReadItem` (OUT-01)
3. Sideloading neues Outlook + OWA (OUT-01)
4. Auth-Fluss im iframe (OUT-02)
5. Live-Mail-Kontext im Chat, Mailwechsel aktualisiert Kontext (OUT-03)
6. Kein-Auto-Send: kein Sende-/Compose-Element, keine Mail durch das Add-in erzeugt (OUT-04)
7. Agent-Dropdown wechselt das iframe-Ziel

**Resume-Signal:** „approved" oder konkrete Abweichungen (Outlook-Variante, Schritt-Nr., Beobachtung). Bei Abweichungen: `/gsd:plan-phase 08 --gaps`.

Diese Abnahme fällt natürlich mit dem Esso-Rollout / einer HTTPS-Test-Session zusammen (analog den Browser-/A-B-Checkpoints der Phasen 6 und 7).

## Phase-8-Status

Der **baubare Teil ist vollständig** (08-01…08-03 + 08-04 Task 1): Taskpane-Serving same-origin mit pfad-abhängiger CSP, XML-Manifest (ReadItem, `ADDIN_BASE_URL`-templatisiert), Office.js-Mail-Kontext via origin-validiertem postMessage → `mail_context` (D-65/D-69), strukturell rein lesend, HTTPS-Runbook + Sideloading-/M365-Doku. Requirements OUT-01…04 sind in ihren baubaren Anteilen umgesetzt und getestet; die **Live-Bestätigung** aller fünf Success Criteria steht als menschlicher Checkpoint aus.

**SC-Nachweis 08-04:** SC (Live-Bestätigung OUT-01…04) NICHT abgeschlossen — Task-2-Checkpoint offen. Kein „approved" beansprucht.
