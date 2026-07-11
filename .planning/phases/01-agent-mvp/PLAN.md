# Phase 1: Agent MVP — Plan-Index

**Modus:** MVP · Coarse · Parallelisierbar (Wave 2 hat 2 parallele Plans)
**Erwarteter Aufwand:** 1.5–2.5 Werktage

## Plans in dieser Phase

| Plan | Titel | Wave | Depends on | Kurzform |
|---|---|---|---|---|
| [01-skeleton](01-skeleton.md) | Repo-Skeleton, Config, Logging, State, Prompts | 1 | — | Dockerfile, compose, pyproject, .env.example, prompts/, src/config.py, src/logging_setup.py, src/state.py |
| [02-imap-draft](02-imap-draft.md) | IMAP-Client, Draft-Builder, PII | 2 | 01 | src/imap_client.py, src/draft.py, src/pii.py |
| [03-llm](03-llm.md) | LLM-Klassifikation + Draft-Generation | 2 | 01 | src/classify.py, src/generate.py |
| [04-main-tests-release](04-main-tests-release.md) | Main-Loop + Tests + README + Release | 3 | 02, 03 | src/main.py, tests/, README.md, git tag v1.0.0 |

## Wave-Schedule

```
Wave 1:  ▓ 01-skeleton
Wave 2:  ▓ 02-imap-draft     ▓ 03-llm         (parallel)
Wave 3:  ▓ 04-main-tests-release
```

Bei paralleler Ausführung von Wave 2 sinkt der Wall-Clock-Aufwand entsprechend.

## Phase 1 Must-Haves (goal-backward)

Diese Kriterien werden am Phasen-Ende geprüft (via `/gsd:verify-phase 1` bzw. manuell):

1. **Agent läuft lokal** — `docker compose up -d` startet ohne Fehler, `docker compose logs -f agent` zeigt `poll_start`/`poll_done`-Events im JSON-Format
2. **Test-Suite grün** — `pytest agent/tests/ -v` mit ≥ 25 Tests, 100 % Pass
3. **End-to-End manuell verifiziert** — Testmail an Vizionists-eigenen GMX-Testaccount produziert Draft mit korrektem `In-Reply-To`-Threading innerhalb ≤ 10 Min (manueller Test in Phase 2 wiederholt)
4. **Kein Auto-Send** — Code enthält nirgends `smtp_send` / `send_message` / SMTP-Client, nur IMAP-`APPEND`
5. **Prompts externalisiert** — `agent/prompts/classify.txt` und `agent/prompts/generate.txt` existieren und werden bei Runtime geladen
6. **PII-Redaction default aktiv** — `.env.example` hat `ENABLE_PII_REDACTION=true`
7. **Backfill-Schutz aktiv** — `BACKFILL_DAYS=1` als Default in `.env.example`; `_compute_since()` verwendet den kleineren Wert aus `now - BACKFILL_DAYS` und `first_run_at - 1h`
8. **Auto-Start konfiguriert** — `docker-compose.yml` hat `restart: unless-stopped`
9. **Repo v1.0.0 getaggt** — Git-Tag existiert lokal (Push zum Remote optional)

## Requirement-Coverage-Check

| REQ-ID | Plan | Status |
|---|---|---|
| AGT-01 (IMAP) | 02 | Covered |
| AGT-02 (State) | 01 | Covered |
| AGT-03 (Classify) | 03 | Covered |
| AGT-04 (Generate) | 03 | Covered |
| AGT-05 (Draft) | 02 | Covered |
| AGT-06 (Poll-Loop) | 04 | Covered |
| AGT-07 (Logging) | 01 | Covered |
| AGT-08 (Config) | 01 | Covered |
| AGT-09 (Signal-Handling) | 04 | Covered |
| AGT-10 (PII) | 02 | Covered |
| DEL-01 (Dockerfile) | 01 | Covered |
| DEL-02 (Compose) | 01 | Covered |
| DEL-03 (pyproject) | 01 | Covered |
| DEL-04 (.env.example) | 01 | Covered |
| DEL-05 (context.md.example) | 01 | Covered |
| DEL-06 (Prompts) | 01 | Covered |
| DEL-07 (README) | 04 | Covered |
| DEL-08 (Repo v1.0.0) | 04 | Covered |
| TEST-01 (Classify-Tests) | 04 (Task 4.6) | Covered |
| TEST-02 (Draft-Tests) | 04 (Task 4.5) | Covered |
| TEST-03 (E2E-Smoke) | 04 (Task 4.9) + Phase 2 manuell | Partial-Covered (manuelle E2E gegen echten IMAP passiert in Phase 2) |
| PRE-01 | parallel Kundenklärung | Nicht in Plans (extern) |

**Coverage:** 21/22 Requirements der Phase 1 vollständig in Plans; TEST-03 zusätzlich durch Phase-2-manuellen-Test.

## Risiken für die Ausführung

| Risiko | Mitigation |
|---|---|
| `imap-tools`-API-Änderungen zwischen 1.7 → 2.x | pyproject pinnt `<2.0` |
| Anthropic-SDK Breaking Changes | pyproject pinnt `<1.0`, aktueller Stand `>= 0.42` |
| `imap_tools.MailMessageFlags.DRAFT`-Konstante könnte anders heißen | Task 2.1 dokumentiert Fallback-Notiz für den Executor |
| Docker Compose `-f` vs. Compose Plugin v2 Syntax | Explizit Plugin-Syntax verwendet |
| `python-dotenv`-Load-Order in Container (Env-Datei liegt in `env_file`-Property) | `env_file: .env` ist Compose-Feature, `load_dotenv()` ist Fallback für lokale Tests |

## Nächster Schritt

**Ausführung:** `/gsd:execute-phase 1` — der Executor arbeitet die 4 Plans in ihrer Wave-Reihenfolge ab.

**Alternative (schrittweise):** `/gsd:execute-plan 01-skeleton`, dann `02-imap-draft` und `03-llm` parallel, dann `04-main-tests-release`.
