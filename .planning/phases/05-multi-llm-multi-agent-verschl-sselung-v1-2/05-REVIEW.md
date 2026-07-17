---
phase: 05-multi-llm-multi-agent-verschl-sselung-v1-2
reviewed: 2026-07-17T02:34:49Z
depth: standard
files_reviewed: 46
files_reviewed_list:
  - .dockerignore
  - .gitignore
  - agent/pyproject.toml
  - agent/README.md
  - agent/src/classify.py
  - agent/src/config.py
  - agent/src/crypto.py
  - agent/src/generate.py
  - agent/src/imap_client.py
  - agent/src/llm.py
  - agent/src/main.py
  - agent/src/status_writer.py
  - agent/tests/conftest.py
  - agent/tests/test_classify.py
  - agent/tests/test_config_multi_agent.py
  - agent/tests/test_config_provider_override.py
  - agent/tests/test_crypto.py
  - agent/tests/test_generate.py
  - agent/tests/test_generate_with_history.py
  - agent/tests/test_llm.py
  - agent/tests/test_main_history.py
  - agent/tests/test_main_multi_account.py
  - deployment/docker-compose.phase4.yml
  - deployment/kunde-env.example
  - deployment/README.phase4.md
  - deployment/vizionists-test-env.example
  - scripts/build-deployment-package.sh
  - webui/docker-entrypoint.sh
  - webui/pyproject.toml
  - webui/src/agents_io.py
  - webui/src/config_io.py
  - webui/src/crypto.py
  - webui/src/llm_detect.py
  - webui/src/llm_seed.py
  - webui/src/main.py
  - webui/src/migration.py
  - webui/src/state_reader.py
  - webui/src/templates/_status_card.html
  - webui/src/templates/index.html
  - webui/tests/test_agents_io.py
  - webui/tests/test_config_io.py
  - webui/tests/test_crypto.py
  - webui/tests/test_endpoints_agent.py
  - webui/tests/test_endpoints_config.py
  - webui/tests/test_endpoints_reset.py
  - webui/tests/test_endpoints_seed.py
  - webui/tests/test_llm_detect.py
  - webui/tests/test_llm_seed.py
  - webui/tests/test_migration.py
  - webui/tests/test_security.py
  - webui/tests/test_state_reader.py
findings:
  critical: 1
  warning: 6
  info: 6
  total: 13
status: issues_found
---

# Phase 5: Code Review Report

**Reviewed:** 2026-07-17T02:34:49Z
**Depth:** standard
**Files Reviewed:** 46
**Status:** issues_found

## Summary

Reviewed the Phase-5 changes: Multi-LLM adapter (`agent/src/llm.py`), Multi-Account agent loop (`agent/src/main.py`, `config.py`), Fernet encryption (`crypto.py` in both services), and the per-agent WebUI data layer + routing (`agents_io.py`, `migration.py`, `main.py`, templates).

Overall the security-sensitive surfaces are handled well: the slug whitelist (`AGENT_ID_PATTERN` / `AGENT_SLUG_PATTERN`) is consistently enforced on every path-building helper, so path traversal via `agent_id` is blocked (tests confirm `../evil` → 400/ValueError); `load_agent_config` reads via `dotenv_values` without mutating `os.environ`, so multi-account isolation holds; secrets are chmod-600, `.dockerignore`/`.gitignore` exclude `.secret_key`, and API keys are never logged. No hardcoded live secrets were found.

The findings below concentrate on (1) a correctness bug in the header-parsing/dispatch of `_process_one` that predates Phase 5 but lives in a reviewed file, (2) the newly shipped OpenAI/Google adapters being effectively non-functional as configured, and (3) several observability/UX regressions introduced by the multi-account status plumbing.

## Critical Issues

### CR-01: `_process_one` fails to skip mails without a `Message-ID` and then crashes on them

**File:** `agent/src/main.py:56-64`
**Issue:** The default for a missing header is a **non-empty list**, not an empty string:
```python
message_id = msg.headers.get("message-id", [""])
if isinstance(message_id, tuple):
    message_id = message_id[0] if message_id else ""
if not message_id:      # `[""]` is truthy -> guard never fires
    logger.warning("skip_no_message_id", ...)
    return
```
When a mail has no `Message-ID` header, `msg.headers.get(...)` returns the default `[""]` (a `list`, not a `tuple`), so the `isinstance(..., tuple)` branch is skipped and `if not message_id` evaluates `not [""]` → `False`. The `[""]` list then flows into `state.is_processed(config.state_db, message_id)` and `state.mark_processed(message_id=[""], ...)`, where sqlite3 raises `Error binding parameter … type 'list' is not supported`. The exception is caught by the `_poll_once` try/except and logged as `process_failed`, so any legitimate customer mail lacking a `Message-ID` (contact-form senders, some ticketing gateways) is **never answered and re-fails on every 5-minute poll**. The existing test only exercises the tuple case (`{"message-id": ("<abc@example.com>",)}`), so the miss is untested.
**Fix:** Use a string-typed default and normalize both container types:
```python
raw = msg.headers.get("message-id", "")
if isinstance(raw, (tuple, list)):
    raw = raw[0] if raw else ""
message_id = (raw or "").strip()
if not message_id:
    logger.warning("skip_no_message_id", extra={"from": msg.from_, "subject": msg.subject})
    return
```

## Warnings

### WR-01: OpenAI and Google adapters ship non-functional (wrong param + placeholder model IDs, no guard)

**File:** `agent/src/llm.py:32-58`, `agent/src/config.py:51-55`
**Issue:** `MODEL_DEFAULTS` uses model IDs that do not exist as written (`gpt-5-mini`, `gpt-5.4`, `gemini-2.5-pro/-flash-lite`) and `_call_openai` passes `max_tokens=` / `temperature=` to `chat.completions.create`. Current GPT-5-class models reject `max_tokens` (they require `max_completion_tokens`) and constrain `temperature`. The config comment acknowledges these are "provisorisch … verifiziert vor Produktiv-Einsatz", but nothing prevents a customer from pasting an OpenAI/Google key: `llm_detect` will happily set `LLM_PROVIDER=openai`, the WebUI shows "Provider erkannt: OpenAI", and then **every classify/draft call fails silently each poll cycle** with only a per-agent status error. For a phase whose headline feature is "Multi-LLM", two of three providers are broken on arrival.
**Fix:** Either gate non-Anthropic providers behind an explicit "unverified" flag / disable them in the UI until validated, or correct the call shape (`max_completion_tokens`, drop unsupported `temperature`) and verify model IDs via `client.models.list()` before shipping. At minimum, surface a clear "Provider noch nicht freigegeben" error at save time instead of per-cycle failures.

### WR-02: Successful-cycle status write clobbers the real `detection_source`, so the UI never shows the detected Drafts folder

**File:** `agent/src/main.py:272-278` (and consumer `webui/src/templates/index.html:116-134`)
**Issue:** `_resolve_drafts_folder` writes the meaningful `detection_source` (`special-use` / `provider` / `explicit`) to the status file just before polling. Immediately after a successful `_poll_once`, the `else` branch of `_run_cycle` overwrites it with `detection_source="ok"`:
```python
status_writer.write_status(
    drafts_folder=cfg.imap_drafts_folder,
    detection_source="ok",   # overwrites 'special-use'/'provider'
    ...
)
```
The template only renders the green "Drafts-Ordner automatisch erkannt" confirmation for `detection_source in ('special-use','provider','explicit')`. `"ok"` matches none of those branches, so after the first successful cycle the user always falls through to the generic "wird beim ersten Poll automatisch erkannt" hint — the detected folder name is never confirmed back to them.
**Fix:** Preserve the resolved source on the success write (thread it through from `_resolve_drafts_folder`, e.g. store it on `cfg` or return it), or drop the `detection_source` argument from the success write so it does not overwrite the prior value.

### WR-03: A sole agent with an undecryptable/broken config waits idle forever with no surfaced error

**File:** `agent/src/main.py:281-309`
**Issue:** `_wait_for_agents` counts an agent as "ready" only if `load_agent_config` succeeds and `agent_enabled` is true; `DecryptionError`/`RuntimeError` are swallowed with `continue`. If the only configured agent has a broken Fernet token (key replaced/lost — exactly the SEC-03 failure mode) or a missing required field, `ready` stays `0` and the process loops in the idle wait **indefinitely**, never entering `_run_cycle`, so `_fail_agent` is never called and **no `error` is ever written to that agent's `agent_status.json`**. The WebUI then shows "Wartet auf nächsten Zyklus" with no explanation. This directly undermines the "fail-fast statt stiller Retry-Endlosschleife" intent documented on `DecryptionError` in `config.py`.
**Fix:** When agents exist but none load, write an error status per failing agent (reuse `_fail_agent`) before/while waiting, so the misconfiguration is visible in the UI instead of an eternal silent idle.

### WR-04: Transient IMAP probe failure is cached as the provider default until the `.env` mtime changes

**File:** `agent/src/main.py:208-223`
**Issue:** If `detect_drafts_folder()` raises (IMAP briefly unreachable during the probe), the code caches `folder = config.imap_drafts_folder, source = "provider"` keyed on the `.env` mtime:
```python
except Exception as e:
    logger.warning("drafts_folder_probe_failed", ...)
...
_drafts_cache[config.agent_id] = (env_mtime, folder, source)
```
Because cache invalidation is tied only to the `.env` mtime, a one-off probe failure "sticks": SPECIAL-USE auto-discovery is never retried on subsequent cycles even after the server recovers, until the customer happens to re-save the agent config. A server whose true Drafts folder differs from the static provider default will then keep appending to the wrong/auto-created folder.
**Fix:** Do not cache the result when the probe raised an exception (only cache genuine detections and the deliberate provider fallback), or add a short TTL so a failed probe is retried on the next cycle.

### WR-05: `save` provider-detect message can misreport when only a masked/empty key is submitted alongside a real change

**File:** `webui/src/main.py:345-366`
**Issue:** The provider is only re-derived and reported when a new non-masked `llm_api_key` is present, which is correct — but note that `updates["OWN_EMAIL_ADDRESS"] = imap_user` is written **unconditionally** whenever `imap_user` is submitted (line 337-340), overwriting any independently configured `OWN_EMAIL_ADDRESS`. For the "IMAP_USER == OWN_EMAIL_ADDRESS for 99%" assumption this is fine, but a customer who intentionally set a distinct own-sender address (e.g. a shared alias vs. login) has it silently reset on every IMAP-section save, re-enabling reply-on-own loops for the alias.
**Fix:** Only default `OWN_EMAIL_ADDRESS` from `imap_user` when it is not already set, or expose it as its own field rather than coupling it to `imap_user`.

### WR-06: `crypto.py` is duplicated verbatim across two services with no shared source of truth

**File:** `agent/src/crypto.py:1-59`, `webui/src/crypto.py:1-59`
**Issue:** The two files are byte-for-byte identical (~59 lines) and encode a security-critical contract (`enc:` prefix, key path `/config/.secret_key`, InvalidToken → RuntimeError translation). They are also tested by two identical copies of `test_crypto.py`. A future fix applied to only one copy (e.g. changing the key filename or prefix) silently breaks cross-service decrypt — the WebUI would encrypt with one scheme and the agent fail to decrypt. The build script comment even calls this out ("identisches ~35-Zeilen-Modul in beiden Services") without a mechanism to keep them in sync.
**Fix:** Extract to a single shared module/package installed into both images, or add a CI check that asserts the two files are identical. Not urgent, but it is a latent correctness/security divergence risk.

## Info

### IN-01: `_process_one` is annotated `-> None` but returns a tuple

**File:** `agent/src/main.py:54,125`
**Issue:** The signature says `-> None`, yet the REPLY_NEEDED path returns `(raw_bytes, message_id)`. The caller relies on the tuple, so it works, but the annotation is misleading and defeats type checking.
**Fix:** Annotate as `-> Optional[tuple[bytes, str]]`.

### IN-02: Inline `import re as _re` inside `_process_one`; unused `Optional` import

**File:** `agent/src/main.py:11,66`
**Issue:** `re` is imported locally inside the hot loop function (`import re as _re`) instead of at module level, and `from typing import Optional` (line 11) is unused in the module.
**Fix:** Move `import re` to the top of the module and remove the unused `Optional` import.

### IN-03: agent/README.md load command references a stale version

**File:** `agent/README.md:23`
**Issue:** Step 2 shows `docker load -i vizpatch-v1.0.0.tar` while the package/version is now v1.2.0 (see `pyproject.toml`, deployment README). A customer copy-pasting this hits "file not found".
**Fix:** Use the versioned placeholder consistently, e.g. `vizpatch-v1.2.0.tar`.

### IN-04: `_call_anthropic` assumes the first content block is text

**File:** `agent/src/llm.py:29`
**Issue:** `response.content[0].text` will raise `AttributeError` if the first block is a non-text block. Unlikely for these plain single-prompt calls, but not defensive.
**Fix:** Filter for text blocks (as `llm_seed.generate` already does with `if block.type == "text"`).

### IN-05: `detect_drafts_folder` matches on substring `"Drafts"` rather than the exact `\Drafts` flag

**File:** `agent/src/imap_client.py:70`
**Issue:** `any("Drafts" in f for f in flags)` would also match a hypothetical flag string containing "Drafts" as a substring. Low risk given RFC 6154 flag names, but a stricter equality/`\\Drafts` check is more correct.
**Fix:** Match the exact special-use attribute (`\Drafts`).

### IN-06: `migration.py` value split uses the stripped line, dropping intentional trailing/edge whitespace

**File:** `webui/src/migration.py:112`
**Issue:** `value = stripped.split("=", 1)[1]` operates on the whitespace-trimmed line, so a value with meaningful trailing whitespace (unusual but legal in a quoted secret) would be altered during migration. Cosmetic for the expected inputs.
**Fix:** Split the original line (not `stripped`) or document that trimming is intended.

---

## Narrative Findings (AI reviewer)

All findings above are narrative (direct code-review) findings; no `<structural_findings>` substrate was provided with this review. Highest-priority items to address before ship: **CR-01** (crash/no-reply on mails without `Message-ID`), **WR-01** (OpenAI/Google effectively broken as shipped), and **WR-03** (silent infinite idle on a broken sole agent — this defeats the documented SEC-03 fail-fast intent).

---

_Reviewed: 2026-07-17T02:34:49Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
