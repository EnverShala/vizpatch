# Plan 01-skeleton — Summary

**Plan ID:** 01-skeleton
**Title:** Repo-Skeleton, Config, Logging, State, Prompts
**Wave:** 1
**Status:** Completed
**Date:** 2026-07-10

## Scope

Das komplette Repo-Skelett wurde unter `D:\Vizionists\kiemailagent\agent\` angelegt: Docker-Setup, Python-Package-Config, Prompt-Templates, Config-Loader, JSON-Logger und SQLite-State-Layer. Keine IMAP-/LLM-Logik — nur die Grundlagen für die nachfolgenden Plans.

## Created Files

Alle Pfade absolut:

### Root-Ebene (`agent/`)
- `D:\Vizionists\kiemailagent\agent\.gitignore`
- `D:\Vizionists\kiemailagent\agent\.env.example`
- `D:\Vizionists\kiemailagent\agent\pyproject.toml`
- `D:\Vizionists\kiemailagent\agent\Dockerfile`
- `D:\Vizionists\kiemailagent\agent\docker-compose.yml`
- `D:\Vizionists\kiemailagent\agent\context.md.example`

### Prompts (`agent/prompts/`)
- `D:\Vizionists\kiemailagent\agent\prompts\classify.txt`
- `D:\Vizionists\kiemailagent\agent\prompts\generate.txt`

### Python-Package (`agent/src/`)
- `D:\Vizionists\kiemailagent\agent\src\__init__.py` (leer)
- `D:\Vizionists\kiemailagent\agent\src\config.py`
- `D:\Vizionists\kiemailagent\agent\src\logging_setup.py`
- `D:\Vizionists\kiemailagent\agent\src\state.py`

### Leere Ordner (Platzhalter für spätere Plans)
- `D:\Vizionists\kiemailagent\agent\tests\` — wird in Plan 04 gefüllt

## Task Status

| Task | Beschreibung | Status |
|---|---|---|
| 1.1 | Ordnerstruktur `agent/` + `.gitignore` | done |
| 1.2 | `pyproject.toml` mit Dependencies | done |
| 1.3 | `Dockerfile` mit `python:3.13-slim` + non-root User `kea` | done |
| 1.4 | `docker-compose.yml` mit Named Volume + Log-Rotation | done |
| 1.5 | `.env.example` mit allen Env-Vars + Provider-Beispielen | done |
| 1.6 | `context.md.example` mit Sektionen About/Öffnungszeiten/FAQ/Ton/Signatur | done |
| 1.7 | Prompts `classify.txt` + `generate.txt` mit Platzhaltern | done |
| 1.8 | `config.py` mit `Config`-Dataclass + `load_config()` + Fail-Fast Validierung | done |
| 1.9 | `logging_setup.py` mit `JsonFormatter` + `setup_logging()` | done |
| 1.10 | `state.py` mit SQLite-Schema + Dedup-API + `get_or_set_first_run()` | done |

## Deviations from Plan

Keine. Der gesamte Content wurde verbatim aus dem Plan (`01-skeleton.md`) übernommen, Platzhalter/Struktur der `context.md.example` verbatim aus `01-CONTEXT.md` Sektion "context.md.example".

## Verification (Structural)

- `agent/` existiert mit Sub-Ordnern `src/`, `prompts/`, `tests/`
- Alle im Plan gelisteten Dateien sind vorhanden (siehe "Created Files")
- `src/__init__.py` leer angelegt (Package-Marker)
- `.gitignore` enthält `.env`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `data/`, `*.db`, `.venv/`
- Prompt-Templates enthalten alle geforderten Platzhalter (`{from}`, `{subject}`, `{body_snippet}`, `{company_name}`, `{context_md_full}`, `{body}`)
- `Config`-Dataclass ist `frozen=True`, alle Env-Vars aus `.env.example` gemappt
- State-Schema enthält beide Tabellen (`processed_emails` mit PK `message_id` + Index; `meta(key, value)`)

Runtime-Verifikation (docker build, pip install, python-Import) wurde übersprungen — der Host hat keinen Docker/Python 3.13. Structural-Verify only.

## Notes for Downstream Plans

- **Python-Package-Root:** `agent/src/` — alle nachfolgenden Module (`imap_client.py`, `classify.py`, `generate.py`, `draft.py`, `pii.py`, `main.py`) gehören hier hinein.
- **Import-Pfad im Container:** Der Container-`WORKDIR` ist `/app`, gestartet wird via `python -m src.main`. Interne Imports also `from src.config import load_config`, nicht `from agent.src.config …`.
- **Config-Kontrakt:** `load_config()` liefert eine frozen `Config`-Dataclass mit allen gemappten Feldern — nachfolgende Module nehmen `Config` per DI, nicht `os.getenv()` direkt.
- **State-Kontrakt:** `state.py` verwendet reine Funktionen mit `db_path` als erstem Argument (kein globaler Connection-Pool, kein ORM). Plan 04 (main.py) muss `init_db(cfg.state_db)` beim Startup aufrufen.
- **Prompt-Substitution:** Runtime nutzt `str.format()` — `generate.txt` erwartet `{company_name}` das aus `OWN_DISPLAY_NAME` gefüttert wird.
- **Backfill-Marker:** `get_or_set_first_run()` ist der Anker für den 24h-Backfill-Schutz (Plan 02/04).
- **Tests-Ordner** ist leer angelegt, aber leere Ordner werden von Git nicht getrackt — Plan 04 muss beim Anlegen der ersten Test-Datei damit rechnen.
