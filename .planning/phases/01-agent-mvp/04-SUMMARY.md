# Plan 04 Summary — Main-Loop, Tests, README, v1.0.0-Release

**Plan ID:** `04-main-tests-release`
**Title:** Main-Loop, Tests, README, v1.0.0-Release
**Wave:** 3 (final plan of Phase 1)
**Status:** Complete

## Created Files

Production source:
- `agent/src/main.py` — polling loop entry point with signal handling, backoff, per-message error isolation

Test infrastructure:
- `agent/tests/__init__.py` (empty)
- `agent/tests/conftest.py` — pytest fixtures (`tmp_db`, `mock_config`, `mock_anthropic_classify_reply_needed`, `mock_anthropic_classify_ignore`, `mock_anthropic_generate`)
- `agent/tests/test_state.py` — 5 tests
- `agent/tests/test_pii.py` — 5 tests
- `agent/tests/test_draft.py` — 6 tests
- `agent/tests/test_classify.py` — 6 tests (3 parse + 3 classify)
- `agent/tests/test_generate.py` — 4 tests

Docs:
- `agent/README.md` — operator setup guide (~80 lines)

## Task Status

| Task | Status | Notes |
|---|---|---|
| 4.1 `agent/src/main.py` | Done | Verbatim per plan |
| 4.2 test infrastructure | Done | Verbatim per plan |
| 4.3 test_state.py | Done | 5/5 pass |
| 4.4 test_pii.py | Done | 5/5 pass |
| 4.5 test_draft.py | Done (with fix) | 6/6 pass — see deviation below |
| 4.6 test_classify.py | Done | 6/6 pass |
| 4.7 test_generate.py | Done | 4/4 pass |
| 4.8 README.md | Done | Verbatim per plan |
| 4.9 E2E verify | Partial | pytest all green; docker build not verified |
| 4.10 git init + tag | Done | Tag `v1.0.0` created |

## Test Results

- **Runtime:** Python 3.14.5 (Windows), pytest 9.1.1
- **Collected:** 26 tests
- **Passed:** 26 / 26
- **Total runtime:** ~1.0 s

```
tests/test_classify.py — 6 passed
tests/test_draft.py    — 6 passed
tests/test_generate.py — 4 passed
tests/test_pii.py      — 5 passed
tests/test_state.py    — 5 passed
```

## Git Tag Confirmation

```
$ cd agent && git log --oneline
25bb1f8 feat: initial KEA agent v1.0.0

$ git tag
v1.0.0
```

Tag `v1.0.0` annotated with message `"v1.0.0 — First shippable release"`. No remote configured; no push performed (per plan instruction).

## Deviations from Plan

1. **Fixture .eml files skipped.** Plan front-matter lists 10 `agent/tests/fixtures/*.eml` files under `files_modified`, but no task defines their content — tests use `MagicMock`, not real .eml fixtures. Directory not created.

2. **`test_draft.py` minor adjustment.** The plan's verbatim code calls `email.message_from_bytes(raw).get_content()`. In Python 3.13+ / 3.14, the legacy `Message` class returned by `message_from_bytes()` without a `policy` argument does not expose `.get_content()`. Added a `_parse(raw)` helper that passes `policy=email.policy.default` so the modern `EmailMessage` class is returned; test intent is preserved. All 6 draft tests pass. Production code (`src/draft.py`) was NOT modified.

3. **Python runtime.** Environment has Python 3.14.5 (via `py` launcher; no 3.13 available). `pyproject.toml` requires `>=3.13` which 3.14 satisfies. All dependencies installed and tests pass cleanly.

4. **`kea_tankstelle.egg-info/` excluded.** Pip's editable install created this metadata dir before the first `git add`. Added `*.egg-info/` to `.gitignore` and removed from staging before commit.

5. **Docker build NOT verified.** Docker may not be installed on this workstation; plan Task 4.9 step 3 (`docker build -t kea-tankstelle:dev .`) and step 4 (`docker compose config`) were skipped per orchestration guidance. Dockerfile and docker-compose.yml exist unchanged from Plan 01. Deployment-time smoke test is Phase 2 territory.

## Notes for Phase 2 (Deployment)

- **First-run prerequisites on customer host (`/opt/kea/agent/`):**
  1. `cp .env.example .env && chmod 600 .env` — fill IMAP creds + Anthropic key
  2. `cp context.md.example context.md` — fill company facts, hours, tone, signature
  3. `docker compose up -d`
- **State persistence:** Named volume `agent-data` holds `state.db` (dedup + first-run timestamp). Never delete without accepting risk of re-draft storm.
- **Drafts destination:** IMAP folder configured by `IMAP_DRAFTS_FOLDER` (provider-specific: `Entwürfe` for GMX/T-Online/Web.de, `Drafts` for IONOS, `[Gmail]/Drafts` for Gmail, `INBOX.Drafts` for All-Inkl).
- **No auto-send.** Agent APPENDs to Drafts only. Operator sends manually from their normal mail client. `OWN_EMAIL_ADDRESS` filter blocks reply-on-reply loops.
- **First-poll backfill:** limited to `BACKFILL_DAYS=1` (default). Never bump this for the first customer without accepting a burst of drafts on historical mail.
- **Backoff on failure:** exponential from `POLL_INTERVAL_SECONDS` up to 3600 s; resets to base on next success.
- **DSGVO prerequisites for live customer traffic:** AVV signed with Anthropic; Zero-Data-Retention header configured; PII redaction (`ENABLE_PII_REDACTION=true`) default on.
- **Provider-specific thread testing needed for Phase 2 UAT:** verify `In-Reply-To` + `References` renders draft in the correct thread for GMX (Entwürfe), Gmail ([Gmail]/Drafts), Outlook/IONOS (Drafts).
