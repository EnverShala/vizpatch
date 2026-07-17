---
phase: 06-schreibstil-adaption
plan: 04
subsystem: testing
tags: [fixtures, ab-test, style-adaption, checkpoint-pending]

# Dependency graph
requires:
  - phase: 06-schreibstil-adaption
    provides: "06-01 (style.md-Injection in generate.py), 06-03 (Style-Endpoints + WebUI-Fieldset)"
provides:
  - "A/B-Fixtures für den SC2-Nachweis (agent/tests/fixtures/style_ab/)"
affects: [06-04-checkpoint, phase-6-abschluss]

# Tech tracking
tech-stack:
  added: []
  patterns: [".eml-Fixture-Konvention aus tests/fixtures/pre-deployment/ wiederverwendet für neuen style_ab-Ordner"]

key-files:
  created:
    - agent/tests/fixtures/style_ab/style-locker-ton.md
    - agent/tests/fixtures/style_ab/standard-oeffnungszeiten.eml
    - agent/tests/fixtures/style_ab/beschwerde-verspaetung.eml
    - agent/tests/fixtures/style_ab/README.md
  modified: []

key-decisions:
  - "Task 1 (Fixture-Vorbereitung) und Task 2 (menschliche A/B-Abnahme + Klick-Pfad) sind bewusst als getrennte Ausführungsschritte behandelt worden — Task 2 ist ein blockierender checkpoint:human-verify und wurde in diesem Lauf NICHT ausgeführt (kein Docker-Start, kein echter LLM-Call, keine Ton-Bewertung)."

requirements-completed: []  # STY-02/STY-05 bleiben OFFEN — nur das Fixture-Material (Task 1) ist fertig, der eigentliche Nachweis steht im Checkpoint noch aus.

# Metrics
duration: ~15min
completed: 2026-07-17
---

# Phase 6 Plan 04: A/B-Fixtures für Schreibstil-Abnahme (Task 1 von 2 — Task 2 PENDING)

**Drei A/B-Test-Fixtures (lockeres style.md, Standard-Fall, Beschwerde-Fall) + README mit Abnahme-Ablauf für den noch ausstehenden menschlichen Checkpoint — SC2 ist NICHT bewiesen, nur vorbereitet.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-07-17
- **Completed:** 2026-07-17 (nur Task 1)
- **Tasks:** 1 von 2 abgeschlossen (Task 2 = blockierender Checkpoint, ausdrücklich nicht ausgeführt)
- **Files modified:** 4 (alle neu angelegt)

## Accomplishments

- `agent/tests/fixtures/style_ab/style-locker-ton.md` — Beispiel-`style.md` nach dem D-56-Abschnitts-Schema (Anrede, Du/Sie, Grußformel, Satzlänge, Formalität, typische Wendungen), bewusst extrem locker/Du-basiert formuliert, um im Ton-Vergleich maximal sichtbar zu sein.
- `agent/tests/fixtures/style_ab/standard-oeffnungszeiten.eml` — sachlich-neutraler Standard-Fall (Öffnungszeiten-Frage), analog zum bestehenden `.eml`-Format aus `tests/fixtures/pre-deployment/`.
- `agent/tests/fixtures/style_ab/beschwerde-verspaetung.eml` — Beschwerde-Mail (Wartezeit + unfreundliches Personal) für den Hierarchie-Test (T-06-01): lockeres style.md darf eine Beschwerde-Antwort NICHT im Ton übersteuern.
- `agent/tests/fixtures/style_ab/README.md` — dokumentiert den Abnahme-Ablauf für Task 2: zwei Wege (End-to-End über die WebUI inkl. Klick-Pfad, oder direkter `generate_draft_text()`-Aufruf mit echtem LLM-Key), Erwartungstabelle für die Ton-vs-Inhalt-Beobachtung in beiden Fällen.

## Task Commits

1. **Task 1: A/B-Fixture vorbereiten (mit/ohne style.md, Beschwerde-Fall)** - `9f690cf` (feat)

**Plan metadata:** wird separat committet (dieser SUMMARY-Commit)

## Files Created/Modified

- `agent/tests/fixtures/style_ab/style-locker-ton.md` - Beispiel-style.md, D-56-Schema, extrem lockerer Du-Ton
- `agent/tests/fixtures/style_ab/standard-oeffnungszeiten.eml` - Standard-Fall (sachlich-neutral)
- `agent/tests/fixtures/style_ab/beschwerde-verspaetung.eml` - Beschwerde-Fall (verärgerter Kunde)
- `agent/tests/fixtures/style_ab/README.md` - Abnahme-Ablauf + Erwartungstabelle für Task 2

## Decisions Made

- Neue `.eml`-Fixtures statt Wiederverwendung der bestehenden `pre-deployment/01-oeffnungszeiten-frage.eml` bzw. `04-reklamation.eml`: das A/B-Material sollte eigenständig und thematisch klar dem Style-Checkpoint zuordenbar sein (eigener Ordner, eigene Message-IDs), ohne die bestehende Pre-Deployment-Fixture-Suite (14 Dateien, D-18) zu verändern oder zu vermischen.
- README beschreibt zwei Wege zur Draft-Erzeugung (WebUI End-to-End vs. direkter Python-Aufruf), weil Task 2 explizit sowohl den Klick-Pfad als auch die reine Ton-Beobachtung abnehmen muss — der Bediener kann wählen, ob er den vollen Pfad oder nur den A/B-Vergleich zuerst durchgeht.

## Deviations from Plan

None - Task 1 wurde exakt wie im Plan spezifiziert ausgeführt (3 Fixture-Dateien + README, alle Akzeptanzkriterien erfüllt).

## Issues Encountered

None für Task 1.

## Task 2: NICHT ausgeführt — blockierender Human-Verify-Checkpoint offen

**Task 2 (`type="checkpoint:human-verify" gate="blocking"`) wurde in diesem Ausführungslauf bewusst NICHT angefasst.** Dieser Checkpoint erfordert:
- `docker compose up` (WebUI + Agent starten)
- Einen echten IMAP-Login + echten LLM-Call (Anthropic-Key, kein Mock)
- Subjektive menschliche Ton-Bewertung von vier Drafts (Standard mit/ohne Stil, Beschwerde mit/ohne Stil)
- Den vollständigen WebUI-Klick-Pfad (Agent anlegen, style.md automatisch/Button, editieren, Re-Learn, beide Esso-Guards 7a+7b, STY-05-Hinweis bei leerem Postfach ohne Freitext)

Keiner dieser Schritte ist automatisierbar oder wurde simuliert. **SC2 ("Draft mit vs. ohne Stil-Profil unterscheidet sich sichtbar im Ton, Beschwerde-Hierarchie hält") ist damit NICHT bewiesen** — nur das Test-Material dafür liegt bereit.

**Resume-Signal für den Betreiber:** „approved" wenn Ton-Unterschied sichtbar UND Beschwerde-Hierarchie hält UND Klick-Pfad + beide Esso-Guards (7a vorhandenes style.md, 7b migriert-ohne-style.md) + STY-05-Hinweis stimmen; sonst konkrete Abweichungen beschreiben (siehe `06-04-PLAN.md` Task 2).

## User Setup Required

Für den Checkpoint (Task 2) muss der Betreiber:
1. `docker compose up` ausführen (WebUI + Agent starten)
2. Einen Agenten mit echten IMAP-Creds + Anthropic-API-Key anlegen (Postfach mit Gesendet-Ordner, idealerweise ~30 gesendete Mails für die Extraktion)
3. Den Inhalt von `style-locker-ton.md` als style.md setzen (oder Re-Learn mit passendem Freitext auslösen)
4. Die beiden `.eml`-Fixtures als eingehende Mails nachstellen und je zweimal draften lassen (mit/ohne style.md)
5. Die 4 resultierenden Drafts gegen die Erwartungstabelle in `agent/tests/fixtures/style_ab/README.md` prüfen

## Next Phase Readiness

**Plan 06-04 ist NICHT abgeschlossen.** Task 1 (dieses Fixture-Material) ist fertig und committet. Task 2 (blockierender menschlicher Checkpoint) steht aus — erst nach „approved" ist SC2 nachgewiesen und Phase 6 kann als abgeschlossen betrachtet werden. ROADMAP.md und STATE.md wurden entsprechend NICHT auf "06-04 abgeschlossen" gesetzt, sondern markieren den Checkpoint als offen (siehe STATE.md-Eintrag zu diesem Lauf).

---
*Phase: 06-schreibstil-adaption*
*Task 1 completed: 2026-07-17 — Task 2 (Checkpoint) PENDING*
