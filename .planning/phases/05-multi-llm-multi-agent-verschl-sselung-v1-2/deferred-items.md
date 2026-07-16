# Deferred Items — Phase 05

## 05.04 (agents_io + migration)

- **`webui/tests/test_endpoints_config.py` — 5 Tests scheitern lokal mit
  `docker.errors.DockerException: Error while fetching server API version`**
  (`test_get_index_shows_form`, `test_post_save_updates_env`,
  `test_post_save_password_change`, `test_post_save_empty_password_keeps_old`,
  `test_save_auto_fills_own_email_from_imap_user`).
  Ursache: kein Docker-Daemon in dieser Dev-Umgebung erreichbar (Windows,
  kein laufendes Docker Desktop) — betrifft `docker_ctrl.get_agent_status()`,
  das `main.index()`/`main.save()` aufruft. Diese Datei ist NICHT Teil von
  `files_modified` in 05.04 (nur `agents_io.py`/`migration.py`/
  `docker-entrypoint.sh`/`.gitignore`/`.dockerignore`/Tests) — vorbestehendes,
  umgebungsbedingtes Problem, außerhalb des Scopes dieses Plans (Rule-Scope-Boundary).
  Alle 30 neuen Tests (`test_agents_io.py` + `test_migration.py`) sind grün,
  1 skipped (chmod Windows). Sobald Docker Desktop läuft, sollten diese 5
  Tests wieder grün sein.
