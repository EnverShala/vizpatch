---
slug: rename-kea-to-vizpatch
status: complete
completed: 2026-07-13
files_changed: 24
---

# Summary: Rename KEA → Vizpatch

**Ausgeführt:** 2026-07-13
**Status:** ✅ complete
**Scope:** Aktiver Code + aktive Planung. Historische Phase-1/2-Docs und `dist/deployment-paket-v1.0.0/` bewusst unverändert.

## Ersetzungen

| Alt | Neu | Wo |
|---|---|---|
| `kea-tankstelle` | `vizpatch` | Docker-Image-Name, Python-Package (pyproject.toml), GitHub-Repo-Referenzen, Tarball-Namen |
| `kea-agent` | `vizpatch-agent` | Docker-Container-Name (agent-Service) |
| `kea-webui` | `vizpatch-webui` | Docker-Container-Name (Phase-4-Plans, RESEARCH.md) |
| `kea.service` | `vizpatch.service` | systemd-Unit-Name |
| `/opt/kea` | `/opt/vizpatch` | Kundenserver-Deployment-Verzeichnis |
| `KEA` | `Vizpatch` | Produkt-Titel, config.json `code`-Feld (VIZPATCH) |
| `kea` (Logger, User) | `vizpatch` | Python `logging.getLogger("kea.*")`, Linux-User in Dockerfile |
| `KEA-Test-Entwürfe` | `Vizpatch` | IMAP-Ordner-Name im Test-Setup (Enver hat den Ordner 2026-07-13 manuell als `Vizpatch` angelegt — kein `-Test-Entwürfe`-Suffix mehr) |
| `KI Email Agent` / `KI-Email-Agent` | `Vizpatch` (in Plans/CONTEXT) — bleibt als Descriptor in `Vizpatch — KI Email Agent für Tankstelle` |
| `KEA_DIR` | `VIZPATCH_DIR` | Env-Var in install-autostart.sh (Phase-4-Plan 04.05) |

## Geänderte Dateien (24)

**Aktiver Code (10):**
- `agent/src/logging_setup.py` — `getLogger("kea")` → `getLogger("vizpatch")`
- `agent/src/imap_client.py` — `kea.imap` → `vizpatch.imap`
- `agent/src/main.py` — 2× `getLogger("kea")` → `getLogger("vizpatch")`
- `agent/src/classify.py` — `kea.classify` → `vizpatch.classify`
- `agent/src/generate.py` — `kea.generate` → `vizpatch.generate`
- `agent/tests/conftest.py` — Docstring
- `agent/tests/fixtures/pre-deployment/README.md` — `KEA-Test-Entwürfe` → `Vizpatch-Test-Entwürfe`
- `agent/Dockerfile` — Linux-User `kea` → `vizpatch` (3× useradd/chown/USER)
- `agent/docker-compose.yml` — `image: kea-tankstelle:v1.0.0` → `vizpatch:v1.0.0`; `container_name: kea-agent` → `vizpatch-agent`
- `agent/pyproject.toml` — `name = "kea-tankstelle"` → `"vizpatch"`; description aktualisiert

**Aktive Planung (9):**
- `CLAUDE.md` — Header + Repo-Layout-Kommentar
- `.planning/PROJECT.md` — Titel
- `.planning/STATE.md` — Titel + History-Eintrag für Rename
- `.planning/ROADMAP.md` — Titel + Phase-1-Success-Criterion 5 + Phase-4-Success-Criterion 5 (systemd-Unit-Name)
- `.planning/REQUIREMENTS.md` — Titel + DEL-08 + DEP-01 + UI-05
- `.planning/config.json` — project.name + project.code
- `.planning/phases/04-web-ui-multi-kunde/04-CONTEXT.md` — Bulk (D-32, D-38, D-39, D-41)
- `.planning/phases/04-web-ui-multi-kunde/04-RESEARCH.md` — Bulk
- `.planning/phases/04-web-ui-multi-kunde/04.01…04.05-PLAN.md` — Bulk (kea-webui, kea.service Grep-Pattern, KEA_DIR, alle Referenzen)

**Skripte + Deployment-Templates (2):**
- `scripts/build-deployment-package.sh` — `kea-tankstelle` → `vizpatch` (Image-Tag, Tar-Name, Doc-Header)
- `deployment/vizionists-test-env.example` — `IMAP_DRAFTS_FOLDER=KEA-Test-Entwürfe` → `Vizpatch-Test-Entwürfe`

**Quick-Task-Doku (3):** PLAN.md und dieses SUMMARY.md (in `.planning/quick/20260712-rename-kea-to-vizpatch/`).

## Bewusst unangetastet gelassen

**Historische Records (documenting the past — keine Rewrites):**
- `.planning/phases/01-agent-mvp/*` (Phase-1-Docs, abgeschlossen 2026-07-10)
- `.planning/phases/02-deployment-beim-kunden/*` (Phase-2-Docs, abgeschlossen 2026-07-12)
- `.planning/research/SUMMARY-inboxzero-obsolete.md`

**Gebautes Artefakt:**
- `dist/deployment-paket-v1.0.0/*` — v1.0.0-Tarball bereits gebaut (54 MB Docker-Image mit Tag `kea-tankstelle:v1.0.0`). Wird in Phase 4.05 durch v1.1.0 (`vizpatch:v1.1.0` + `vizpatch-webui:v1.1.0`) ersetzt. Umbenennen der Text-Files im Ordner würde nicht mehr zum Binärimage im Tarball passen.

**Nicht produkt-spezifisch (agnostisch, unverändert):**
- Docker-Compose-Service-Namen `agent` und `webui` (Service-Rollen)
- Env-Var-Präfixe `IMAP_*`, `ANTHROPIC_*`, `WEBUI_*`, `AGENT_*`

## Manuelle Follow-ups (durch Enver)

1. **Ordner-Rename** `D:\Vizionists\kiemailagent` → `D:\Vizionists\vizpatch` — Windows kann das laufende Working-Directory nicht renamen; nach Session-Ende in Explorer/CMD durchführen. Danach `cd D:\Vizionists\vizpatch && claude` neu starten.
2. **GitHub-Repo umbenennen** `EnverShala/vizpatch` → `EnverShala/vizpatch` — via Repository Settings → Rename (GitHub setzt Redirect für alte URL automatisch, existierende Clones bleiben funktionsfähig).
3. **Lokale Git-Remote-URL aktualisieren:**
   ```
   git remote set-url origin git@github.com:EnverShala/vizpatch.git
   git remote -v   # verifizieren
   ```
4. **GHCR-Namespace prüfen:** Phase-4-Plans referenzieren `ghcr.io/EnverShala/vizpatch` — sicherstellen dass das Package im GHCR-Namespace verfügbar ist bzw. beim ersten Push automatisch angelegt wird.

## Verifikation

```
$ grep -rn "kea\|KEA\|kea-tankstelle" agent/ scripts/ CLAUDE.md .planning/STATE.md .planning/ROADMAP.md .planning/REQUIREMENTS.md .planning/config.json .planning/PROJECT.md .planning/phases/04-web-ui-multi-kunde/
# → keine Treffer in aktivem Code + aktiver Planung
```

Restanzen (bewusst so):
- `dist/deployment-paket-v1.0.0/*` (gebautes Artefakt)
- `.planning/phases/01-*` und `02-*` (historische Records)
- `research/SUMMARY-inboxzero-obsolete.md` (historisch)
- Beschreibende Zusätze wie `Vizpatch — KI Email Agent für Tankstelle` (Descriptor, gewollt)
