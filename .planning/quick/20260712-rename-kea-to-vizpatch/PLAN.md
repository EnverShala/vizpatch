---
slug: rename-kea-to-vizpatch
created: 2026-07-12T22:39:52
type: rename
---

# Quick Task: Rename KEA → Vizpatch

**Kontext:** Der Produkt-Name ist jetzt "Vizpatch". Alle "KEA" / "kea" / "kea-tankstelle" / "KI Email Agent" (als Produkt-Name, nicht als beschreibende Formulierung) werden zu "Vizpatch" / "vizpatch".

## Rename-Mapping

| Alt | Neu | Kontext |
|---|---|---|
| `kea-tankstelle` | `vizpatch` | Docker-Image-Name, GitHub-Repo-Name, Python-Package |
| `kea-agent` | `vizpatch-agent` | Docker-Container-Name |
| `kea.service` | `vizpatch.service` | systemd-Unit |
| `/opt/kea` | `/opt/vizpatch` | Deployment-Verzeichnis |
| `KEA` | `Vizpatch` | Produkt-Titel, Logger-Präfix |
| `kea` (Logger, User) | `vizpatch` | Python-Logger-Namen, Linux-User im Container |
| `KEA-Test-Entwürfe` | `Vizpatch-Test-Entwürfe` | IMAP-Ordner-Name im Test-Setup |
| `KI Email Agent` (als Produkt) | `Vizpatch` | Freitext-Vorkommen als Produkt-Referenz |

## Scope

**Rename in aktivem Code + aktiver Planung:**
- `CLAUDE.md`
- `.planning/PROJECT.md`, `STATE.md`, `ROADMAP.md`, `REQUIREMENTS.md`, `config.json`
- `.planning/phases/04-web-ui-multi-kunde/*` (CONTEXT + RESEARCH + 5 PLANs)
- `agent/src/*.py`, `agent/tests/conftest.py`, `agent/tests/fixtures/pre-deployment/README.md`
- `agent/Dockerfile`, `agent/docker-compose.yml`, `agent/pyproject.toml`, `agent/README.md`
- `scripts/build-deployment-package.sh`
- `deployment/vizionists-test-env.example`

**NICHT umbenennen (Grund):**
- `.planning/phases/01-agent-mvp/*` — historischer Record (Phase abgeschlossen)
- `.planning/phases/02-deployment-beim-kunden/*` — historischer Record (Phase abgeschlossen)
- `.planning/research/SUMMARY-inboxzero-obsolete.md` — historischer Record
- `dist/deployment-paket-v1.0.0/*` — bereits gebautes Tarball-Artefakt; wird in Phase 4.05 als `vizpatch:v1.1.0` neu gebaut

**NICHT geändert (nicht produkt-spezifisch):**
- Docker-Compose-Service-Namen `agent` und `webui` (Service-Rollen)
- Env-Vars `IMAP_*`, `ANTHROPIC_*`, `WEBUI_*` (agnostisch)

## Manuelle Follow-ups (nicht in dieser Task)

1. **Ordner-Rename** `D:\Vizionists\kiemailagent` → `D:\Vizionists\vizpatch` — von Enver manuell nach Session-Ende, weil Windows das laufende Working-Directory nicht renamen kann
2. **GitHub-Repo umbenennen** `EnverShala/vizpatch` → `EnverShala/vizpatch` — via GitHub Settings → Rename repository (GitHub setzt Redirect für alte URL automatisch)
3. **Lokale Git-Remote-URL neu setzen** nach Repo-Rename: `git remote set-url origin git@github.com:EnverShala/vizpatch.git`

## Erwartete Änderungen

~50–60 Edits über 20 Files.
