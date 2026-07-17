---
phase: 05-multi-llm-multi-agent-verschl-sselung-v1-2
verified: 2026-07-17T00:00:00Z
status: human_needed
score: 7/7 code-verifiable truths verified (4 zusätzliche Punkte erfordern externe Live-Ressourcen)
overrides_applied: 0
human_verification:
  - test: "Modell-ID-Verifikation gegen echte OpenAI-/Google-Keys (client.models.list())"
    expected: "MODEL_DEFAULTS in agent/src/config.py enthält nur real verfügbare Modell-IDs (aktuell gpt-5-mini/gpt-5.4/gemini-2.5-flash-lite/gemini-2.5-pro als LOW/MED-Confidence-Platzhalter markiert)"
    why_human: "Erfordert echte, bezahlte OPENAI_API_KEY/GOOGLE_API_KEY — nicht in dieser Umgebung verfügbar (LLM-03)"
  - test: "14-.eml-Fixture-Durchlauf je Provider (Anthropic/OpenAI/Google), Gate >= 11/14 korrekt + Ø Draft-Qualität >= 3.5/5"
    expected: "Pro Provider dokumentiertes Klassifikations-/Qualitäts-Ergebnis, das das Gate erreicht"
    why_human: "Erfordert echte Provider-Keys und einen menschlichen Qualitäts-Reviewer für die Draft-Bewertung (LLM-04)"
  - test: "MA-05 Parallelbetrieb: 2 Agenten im selben Container gegen 2 echte Test-Postfächer, inkl. explizitem Fehler-Isolations-Check (Agent A falsches Passwort, Agent B draftet trotzdem)"
    expected: "Keine Cross-Kontamination, getrennte State-DBs, Fehler bei A sichtbar, B läuft weiter"
    why_human: "Erfordert 2 erreichbare Test-IMAP-Postfächer — aktuell nicht bereitgestellt (MA-05)"
  - test: "migrate() gegen eine echte Kopie des Esso-Live-Layouts (/config + /data) verifizieren (Byte-Identität context.md, state.db-Zeilenzahl, Idempotenz, Context-KI-Assistent nach Migration)"
    expected: "Alle 6 how-to-verify-Punkte aus 05.06-PLAN Task 3 bestätigt, kein Datenverlust"
    why_human: "Erfordert eine echte Kopie der Esso-Verzeichnisse — Esso-Rollout ist laut ROADMAP/STATE noch nicht abgeschlossen (MA-01 Live-Abnahme)"
---

# Phase 5: Multi-LLM & Multi-Agent (Verschlüsselung, v1.2) Verification Report

**Phase Goal:** Der Betreiber verwaltet im WebUI mehrere Agenten (= Mail-Accounts) gleichzeitig: Agent-Dropdown (leer, solange kein Agent gespeichert ist), Anlegen/Bearbeiten/Löschen pro Agent, Start/Stop pro Agent per Aktiv-Flag — alle Agenten laufen in EINEM Agent-Container (Multi-Account-Poll-Loop, kein Container pro Agent). Pro Agent gibt es genau ein generisches API-Key-Feld („API-Key (Anthropic / OpenAI / Google)"); der LLM-Provider wird aus dem Key-Prefix autodetektiert (D-51, kein Dropdown). Alle Secrets (IMAP-Passwort, API-Key) liegen verschlüsselt (Fernet) in den .env-Dateien; der Schlüssel liegt als chmod-600-Datei im Config-Volume. Bestehende Single-Agent-Installationen (Esso) werden beim ersten Start automatisch und verlustfrei migriert.

**Verified:** 2026-07-17
**Status:** human_needed
**Re-verification:** No — initial verification

## Context: Code Review + Fix Cycle Already Applied

Before this verification, a code review (`05-REVIEW.md`) found 1 critical (CR-01) and 6 warning-level (WR-01…WR-06) issues. All 7 were fixed in commits `ea3d554`…`9448838` prior to this verification pass. This verifier independently re-read the fixed source (not just the review/commit messages) to confirm each fix is actually present and correct:

- **CR-01** (mails without `Message-ID` crashed sqlite / never got a reply): confirmed fixed in `agent/src/main.py:60-66` — string-typed default, tuple/list normalization, `.strip()` guard.
- **WR-01** (OpenAI adapter wrong param + no guard): confirmed fixed in `agent/src/llm.py:32-50` — `max_completion_tokens` instead of `max_tokens`, `temperature` intentionally omitted, documented as unverified-pending-live-check.
- **WR-02** (`detection_source` clobbered on success): confirmed fixed — `_run_cycle`'s `else` branch now threads the real `drafts_source` through instead of writing `"ok"`.
- **WR-03** (broken sole agent waits idle forever, no error surfaced): confirmed fixed in `_wait_for_agents` — `DecryptionError`/`RuntimeError` during the wait loop now call `_fail_agent` per agent instead of silently `continue`-ing.
- **WR-04** (failed IMAP probe cached until next `.env` save): confirmed fixed — cache write is now guarded by `if not probe_failed`.
- **WR-05** (`OWN_EMAIL_ADDRESS` silently overwritten on IMAP save): confirmed fixed in `webui/src/main.py:339-351` — only defaults from `imap_user` when not already independently set.
- **WR-06** (duplicated `crypto.py` with no sync mechanism): confirmed fixed — `agent/tests/test_crypto_sync.py` + `webui/tests/test_crypto_sync.py` added, SHA-256 byte-identity guard.

All 46 review-scoped files were spot-checked against the fix commits; both test suites pass in full (agent: 105 passed/1 skipped, webui: 165 passed/3 skipped — independently re-run by this verifier, not taken from SUMMARY claims).

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Agent-Dropdown existiert, leer bei frischer Installation | ✓ VERIFIED | `webui/src/templates/index.html:28` `<select id="agent-select">` over `{{ agents }}` (from `agents_io.list_agent_ids()`); `test_get_index_shows_agent_dropdown_and_create_form_when_no_agents` in `test_endpoints_config.py` |
| 2 | Anlegen/Umbenennen/Löschen pro Agent (ohne Docker) | ✓ VERIFIED | Routes `POST /agents`, `POST /agents/{id}/rename`, `POST /agents/{id}/delete` in `webui/src/main.py:133-176`; backed by `agents_io.rename_agent`/`delete_agent` (no docker import, `grep -c "docker" webui/src/agents_io.py` == 0); tested in `test_endpoints_agent.py` (create/rename/delete/collision/invalid-id cases) |
| 3 | Start/Stop pro Agent per Aktiv-Flag (kein Container-Restart) | ✓ VERIFIED | `POST /agents/{agent_id}/{action}` → `agents_io.set_agent_enabled(agent_id, action=="start")`, writes `AGENT_ENABLED=true|false` via line-parser; `test_agent_start_calls_set_agent_enabled_true`/`_false` |
| 4 | Alle Agenten laufen in EINEM Container (Multi-Account-Poll-Loop) | ✓ VERIFIED | `agent/src/main.py` `_run_cycle()` loops `for agent_id, agent_dir in discover_agents()` sequentially inside one process; `docker-compose.phase4.yml` retains exactly 2 services (agent+webui), no per-agent container; `test_main_multi_account.py` proves 2-agent isolation + error isolation within one cycle |
| 5 | Genau ein generisches API-Key-Feld, Provider autodetektiert (kein Dropdown) | ✓ VERIFIED | `index.html:145-146` single `name="llm_api_key"` field, label "API-Key (Anthropic / OpenAI / Google)"; `grep -c 'name="llm_provider"' index.html` == 0; `webui/src/llm_detect.py::detect_llm_provider` implements the sk-ant-/AIza/sk- prefix rules; `test_save_anthropic_key_sets_provider`/`_google_key_`/`_openai_key_`/`_unrecognized_key_format_rejected` all pass |
| 6 | Secrets Fernet-verschlüsselt in .env; Key chmod-600 im Config-Volume | ✓ VERIFIED | `agent/src/crypto.py`/`webui/src/crypto.py` identical Fernet modules (`ENC_PREFIX`, `_load_or_create_key` with `chmod 600`); `agents_io.write_env` calls `encrypt_value` on `SECRET_KEYS={"IMAP_PASSWORD","LLM_API_KEY"}`; `.secret_key` excluded from `.gitignore`/`.dockerignore`; documented honestly in `deployment/README.phase4.md` (protects against file/backup leak, not root/full-volume access) |
| 7 | Single-Agent-Installation (Esso) wird beim ersten Start automatisch verlustfrei migriert | ⚠️ PARTIAL (code done, live abnahme fehlt) | `webui/src/migration.py::migrate()` implements idempotent move to `agents/default/` with key rename (`ANTHROPIC_API_KEY`→`LLM_API_KEY`), backup, zero-config phantom-agent guard — all unit-tested against synthetic `tmp_path` fixtures (`test_migration.py`, 8 tests green). **However** the ROADMAP-mandated live verification against a real copy of the Esso `/config`+`/data` layout (byte-identity, row-count preservation, idempotency against a grown production DB) was explicitly deferred in 05.06 because the Esso rollout itself is not yet complete — this is a human/external-resource verification item, not a code gap |

**Score:** 6/7 fully code-verified; 1/7 (migration) code-complete but pending real-layout live abnahme (see Human Verification below).

### Deferred / Human-Verification Items (documented, not simulated)

Per explicit instruction from the calling context, the following items were deliberately NOT executed by the 05.06 plan due to missing external resources (no fabricated results were produced) and are treated here as `human_verification` items rather than code gaps:

| Item | Requirement | Blocker |
|------|-------------|---------|
| Live model-ID verification (`client.models.list()`) | LLM-03 | No `OPENAI_API_KEY`/`GOOGLE_API_KEY` available |
| 14-.eml fixture gate per provider (≥11/14 + Ø≥3.5/5) | LLM-04 | Same — no OpenAI/Google keys |
| Parallel-operation + error-isolation against 2 real mailboxes | MA-05 | No 2 test IMAP mailboxes available |
| Migration against real Esso layout copy | MA-01 (live abnahme) | Esso rollout not yet complete |

These four items are the reason overall status is `human_needed` rather than `passed`. The code paths underlying all four are unit-tested and pass; what remains outstanding is verification against real external systems, which this verifier — like the executor — cannot fabricate.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `agent/src/crypto.py`, `webui/src/crypto.py` | Fernet encrypt/decrypt/is_encrypted + key mgmt | ✓ VERIFIED | Byte-identical (SHA-256 guarded by `test_crypto_sync.py`), `ENC_PREFIX="enc:"`, round-trip + legacy-passthrough + InvalidToken→RuntimeError all tested |
| `agent/src/llm.py` | Dispatcher to anthropic/openai/google | ✓ VERIFIED | `llm_call()` dict-dispatch, lazy imports for openai/google, Anthropic fallback for unknown provider, no api_key in logs (caplog-tested) |
| `agent/src/config.py` | `discover_agents`/`load_agent_config`, `LLM_PROVIDER`/`LLM_API_KEY`, `DecryptionError`, `MODEL_DEFAULTS` | ✓ VERIFIED | All present; `os.environ` isolation between agents proven by test (`test_config_multi_agent.py`) |
| `agent/src/main.py` | Multi-account loop, error isolation, IMAP timeout, per-agent logging | ✓ VERIFIED | `_run_cycle`, `_wait_for_agents`, `_fail_agent`, `_AgentLoggerAdapter`, `ImapClient(timeout=...)` all present and tested; CR-01/WR-02/WR-03/WR-04 fixes confirmed in source |
| `agent/src/status_writer.py` | Per-agent status file with `last_cycle` heartbeat | ✓ VERIFIED | `write_status(status_file=..., last_cycle=...)` |
| `webui/src/agents_io.py` | Per-agent CRUD, context.md I/O, flag toggle, rename/delete, slug guard | ✓ VERIFIED | `AGENT_ID_PATTERN`, `_agent_dir` guard, `SECRET_KEYS={"IMAP_PASSWORD","LLM_API_KEY"}`, all documented functions present, no docker import |
| `webui/src/migration.py` | Idempotent single→agents/default migration with agent-key guard | ✓ VERIFIED (code) / ⚠️ (live abnahme pending) | `migrate()` present, idempotent, backup, zero-config phantom-agent guard tested; real-layout abnahme deferred |
| `webui/src/llm_detect.py` | `detect_llm_provider(api_key) -> str\|None` | ✓ VERIFIED | Exact prefix rules implemented and tested (`test_llm_detect.py`) |
| `webui/src/main.py` | agent_id-parametrized routes, /agents CRUD, provider-autodetect save, multi-agent reset, global docker-admin routes retained | ✓ VERIFIED | All routes present (`/`, `/agents/status`, `POST /agents`, `/agents/{id}/rename`, `/agents/{id}/delete`, `/agents/{id}/{action}`, `/agent/{action}`, `/save`, `/context/generate`, `/reset`) |
| `webui/src/templates/index.html` | Agent dropdown + single API-key field + AVV hints + per-agent context.md | ✓ VERIFIED | Confirmed via grep + rendered-page tests |
| `webui/src/templates/_status_card.html` | Status overview for all agents (flag+heartbeat) + global admin tile | ✓ VERIFIED | `test_index_shows_two_status_rows`, `test_index_shows_agent_status_error` pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `agent/src/classify.py`/`generate.py` | `agent/src/llm.py` | `llm.llm_call(...)` | ✓ WIRED | No direct `Anthropic(` instantiation left in either file (`grep -c` == 0) |
| `agent/src/config.py` | `agent/src/crypto.py` | `decrypt_value` at config load | ✓ WIRED | `_decrypt_or_raise` helper used by both `load_config` and `load_agent_config` |
| `webui/src/agents_io.py` | `webui/src/crypto.py` | `encrypt_value` on save | ✓ WIRED | Applied to `SECRET_KEYS` before line-parser write |
| `webui/src/migration.py` | `/config/agents/default/.env` | Line-parser move + key rename + `AGENT_ENABLED` | ✓ WIRED | Confirmed in `test_migration.py` (key rename, provider/enabled fields, idempotency) |
| `agent/src/main.py` | `/config/agents/*/` | `discover_agents()` per cycle | ✓ WIRED | Called both in `_wait_for_agents` and `_run_cycle` (2 call sites, fresh discovery, no restart needed) |
| `webui/src/main.py` | `webui/src/agents_io.py` | CRUD/flag/rename/delete/read/write | ✓ WIRED | All routes call through, tests mock and assert call args |

### Requirements Coverage

| Requirement | Description | Status | Evidence |
|-------------|-------------|--------|----------|
| LLM-01 | Generic API-key field + provider autodetect, no dropdown | ✓ SATISFIED (code) | Verified above; REQUIREMENTS.md checkbox unchecked but marked "Pending (Checkbox-Nachpflege)" — this is a documentation-bookkeeping gap, not a code gap (confirmed independently) |
| LLM-02 | Internal LLM adapter (`llm_call`), classify/generate use only the adapter | ✓ SATISFIED (code) | Verified above; same checkbox-nachpflege note applies |
| LLM-03 | Provider model defaults verified against real keys | ✗ DEFERRED | No live keys available; treated as human_verification (see above), matches explicit REQUIREMENTS.md DEFERRED annotation |
| LLM-04 | 14-.eml fixture gate ≥11/14 + Ø≥3.5/5 per provider | ✗ DEFERRED | Same — human_verification |
| MA-01 | Per-agent config layout + migration | ✓ SATISFIED (code) / ⚠️ live abnahme open | Code+synthetic tests done (05.04); live Esso-layout abnahme deferred (05.06 Task 3) |
| MA-02 | Agent dropdown, CRUD, empty-state | ✓ SATISFIED (code) | Verified above; checkbox-nachpflege note applies |
| MA-03 | One container, multi-account loop, flag-based start/stop, error isolation | ✓ SATISFIED | REQUIREMENTS.md marked `[x]`; code independently confirmed |
| MA-04 | Per-agent state + status overview | ✓ SATISFIED | REQUIREMENTS.md marked `[x]`; code independently confirmed |
| MA-05 | Verified parallel operation, no cross-contamination | ✗ DEFERRED | No 2 test mailboxes available; human_verification |
| SEC-01 | Fernet encryption for secrets at rest, chmod-600 key | ✓ SATISFIED (code) | Verified above; checkbox-nachpflege note applies |
| SEC-02 | Transparent encrypt/decrypt on save/load | ✓ SATISFIED | REQUIREMENTS.md marked `[x]`; code independently confirmed |
| SEC-03 | Key handling documented, honest scope, zero-reset deletes key | ✓ SATISFIED | REQUIREMENTS.md marked `[x]`; deployment README section confirmed |

**Orphaned requirements check:** All 12 phase requirement IDs (LLM-01…04, MA-01…05, SEC-01…03) appear in at least one plan's `requirements:` frontmatter field (05.01: SEC-01; 05.02: MA-03/MA-04; 05.03: LLM-01/02/03/SEC-02; 05.04: MA-01/SEC-02/SEC-03; 05.05: MA-02/MA-04/LLM-01/LLM-04/SEC-03; 05.06: LLM-03/LLM-04/MA-01/MA-05/SEC-03). No orphaned requirements found.

**Note on unchecked checkboxes:** REQUIREMENTS.md shows `[ ]` for LLM-01, LLM-02, MA-02, SEC-01 despite the underlying code being independently confirmed complete and tested by this verifier. The traceability table at the bottom of REQUIREMENTS.md itself annotates these as "Pending (Checkbox-Nachpflege — Code lt. Plan-SUMMARY fertig)" — i.e. a known, self-documented bookkeeping lag, not a functional gap. Recommend updating these checkboxes as a trivial follow-up; not a blocker.

### Anti-Patterns Found

No blocking anti-patterns (TBD/FIXME/XXX without issue reference) found in phase-modified files. The 05-REVIEW.md's 1 critical + 6 warning findings were all fixed in commits `ea3d554`…`9448838`, independently re-verified in this pass (see "Context" section above). Remaining info-level items from the review (IN-01…IN-06 — type-hint mismatch, inline import, stale version string in README, non-defensive content-block access, substring-vs-exact drafts-folder match, migration whitespace edge case) are cosmetic/non-blocking and were not re-litigated here.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Agent test suite green | `cd agent && python -m pytest -q` | 105 passed, 1 skipped | ✓ PASS |
| WebUI test suite green | `cd webui && python -m pytest -q` | 165 passed, 3 skipped | ✓ PASS |
| crypto.py drift guard | `pytest agent/tests/test_crypto_sync.py webui/tests/test_crypto_sync.py` | included in full suite run, passed | ✓ PASS |
| No provider dropdown in template | `grep -c 'name="llm_provider"' webui/src/templates/index.html` | 0 | ✓ PASS |
| Secret key excluded from git/docker | `grep -c secret_key .gitignore .dockerignore` | >=1 in both | ✓ PASS |

### Probe Execution

Not applicable — no `scripts/*/tests/probe-*.sh` convention used in this project; verification relies on the pytest suites above (Step 7b spot-checks cover this role).

### Human Verification Required

### 1. Live OpenAI/Google Model-ID Verification (LLM-03)

**Test:** Run `client.models.list()` against real, paid `OPENAI_API_KEY` and `GOOGLE_API_KEY`; compare against `MODEL_DEFAULTS` in `agent/src/config.py` (`gpt-5-mini`/`gpt-5.4`, `gemini-2.5-flash-lite`/`gemini-2.5-pro`).
**Expected:** Either confirmation that these IDs exist, or `MODEL_DEFAULTS` corrected to real IDs and LOW/MED-confidence comment removed.
**Why human:** Requires real paid API credentials not available in this environment.

### 2. 14-.eml Fixture Quality Gate per Provider (LLM-04)

**Test:** Run the existing Pre-Deployment fixture suite through Anthropic/OpenAI/Google and score classification accuracy + draft quality.
**Expected:** ≥11/14 correct classification and Ø≥3.5/5 draft quality per provider.
**Why human:** Requires real provider keys and a human quality judgment of generated draft text.

### 3. MA-05 Parallel Operation + Error Isolation Against Real Mailboxes

**Test:** Configure 2 agents in the WebUI against 2 real reachable IMAP test mailboxes, enable both, send test mails, verify drafts land in the correct mailbox with no cross-contamination; then break Agent A's password and verify Agent B still drafts in the same cycle.
**Expected:** No cross-contamination; error isolation confirmed against a real IMAP round-trip (not mocked).
**Why human:** Requires 2 reachable test IMAP mailboxes; not available in this environment.

### 4. Migration Abnahme Against Real Esso Layout Copy (MA-01 live check)

**Test:** Copy the real Esso `/config` + `/data` directories into a test Compose environment, start v1.2.0 images, observe `migrate()`, verify all 6 how-to-verify points from 05.06-PLAN Task 3 (byte-identical context.md, preserved state.db row count, backup exists, idempotency on restart, Context-KI-Assistent still works post-migration, fresh-install phantom-agent guard still holds).
**Expected:** Verlustfreie, idempotente Migration gegen echte Produktivdaten.
**Why human:** Requires a real copy of the Esso customer's live directories — the Esso rollout itself is not yet complete per ROADMAP/STATE.

### Gaps Summary

No code-level gaps were found. All 7 phase-goal truths that can be verified from the codebase (dropdown, CRUD, flag-based start/stop, single-container multi-account loop, generic key field with autodetect, Fernet encryption with chmod-600 key, migration code+synthetic-test coverage) are VERIFIED. The prior code review's 1 critical + 6 warning findings were confirmed fixed by independent source inspection (not just trusting commit messages or SUMMARY claims) and both test suites pass in full when re-run by this verifier.

The reason overall status is `human_needed` rather than `passed` is four explicitly-deferred, externally-blocked verification items (LLM-03, LLM-04, MA-05, and the MA-01 live-layout abnahme) that require real API keys, real test mailboxes, and a real customer-data copy that do not exist in this environment — consistent with the phase's own honest DEFERRED documentation in `05.06-SUMMARY.md` and `REQUIREMENTS.md`. These are not code defects; they are pending real-world validation steps that no amount of additional coding can substitute for.

Minor non-blocking note: REQUIREMENTS.md checkboxes for LLM-01, LLM-02, MA-02, SEC-01 remain unchecked despite code being verified complete — a trivial documentation follow-up, already self-flagged in REQUIREMENTS.md's own traceability table as "Checkbox-Nachpflege."

---

*Verified: 2026-07-17*
*Verifier: Claude (gsd-verifier)*
