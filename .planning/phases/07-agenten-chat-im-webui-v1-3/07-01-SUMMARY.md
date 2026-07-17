---
phase: 07-agenten-chat-im-webui-v1-3
plan: 01
subsystem: webui-chat
tags: [fastapi, sse, streaming, anthropic, openai, google-genai, chat]

# Dependency graph
requires:
  - phase: 05-multi-llm-multi-agent-verschluesselung-v1-2
    provides: agents_io.read_env_raw, crypto.decrypt_value, llm.py provider dispatch pattern (Anthropic/OpenAI/Google)
  - phase: 06-schreibstil-adaption
    provides: style_extract.MODEL_DRAFT_DEFAULTS (reused, not duplicated)
provides:
  - webui/src/chat.py — provider-agnostic streaming adapter (stream_chat, resolve_chat_target, ChatConfigError)
  - GET /chat/{agent_id}/embed — chrome-less, embeddable chat partial (D-61 foundation for Phase 8)
  - POST /chat/{agent_id}/send — SSE streaming endpoint (D-62 walking skeleton, real token streaming end-to-end)
  - webui/static/chat.js + chat.css — local-only vanilla SSE client + styling
affects: [07-02-plan (system prompt/history), 07-03-plan (rate limit + mail_context), 07-04-plan (main WebUI chat embedding), phase-8-outlook-addin]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Webui-only streaming sibling module pattern: chat.py mirrors llm.py's dispatch idiom (_DISPATCH -> _STREAM_DISPATCH, lazy SDK imports, unknown-provider-falls-back-to-anthropic) without touching the byte-identical drift-guarded llm.py twin"
    - "Chrome-less embeddable partial: own <!doctype html> root template with zero {% extends %}, only /static-relative resources — established for Phase 8 Outlook-Add-in reuse"
    - "SSE frame encoding: multi-line chunks split into multiple `data:` continuation lines per SSE spec, terminated by 'event: done'/'event: error'"

key-files:
  created:
    - webui/src/chat.py
    - webui/src/templates/chat.html
    - webui/static/chat.js
    - webui/static/chat.css
    - webui/tests/test_chat.py
    - webui/tests/test_endpoints_chat.py
  modified:
    - webui/src/main.py

key-decisions:
  - "D-59/D-62 reconciliation via new webui-only module webui/src/chat.py instead of adding streaming to the drift-guarded llm.py (per plan's design_note) — honors D-59 intent (same provider routing mechanic, provider/key exactly of the chosen agent) without breaking the llm.py<->agent/src/llm.py byte-identical sync contract (WR-06)"
  - "MODEL_DRAFT_DEFAULTS reused from style_extract.py (no new duplicated model table, no new drift-guard target)"
  - "/send route has no agent-existence check (only key/provider resolution) -> unknown-but-valid agent_id returns 400 (ChatConfigError), NOT 404; only /embed checks agents_io.list_agent_ids() and 404s — per plan-checker guidance embedded in the executor prompt"

patterns-established:
  - "Streaming-sibling-module pattern for future provider-agnostic streaming needs without touching drift-guarded llm.py/crypto.py/pii.py/provider_config.py"

requirements-completed: [CHAT-01, CHAT-03, CHAT-05]

# Metrics
duration: 30min
completed: 2026-07-17
---

# Phase 7 Plan 01: Agenten-Chat Walking-Skeleton (SSE) Summary

**Real end-to-end SSE token streaming from a new webui-only `chat.py` adapter (Anthropic/OpenAI/Google, provider+key exactly of the chosen agent) into a chrome-less embeddable `/chat/{agent_id}/embed` partial with a vanilla-JS fetch/ReadableStream SSE client — no CDN, no external resources.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-07-17T18:05:00+02:00 (approx.)
- **Completed:** 2026-07-17T18:27:13+02:00
- **Tasks:** 2
- **Files modified:** 6 created, 1 modified

## Accomplishments
- `webui/src/chat.py`: `stream_chat()` streams provider-agnostically (Anthropic via `messages.stream()`/`text_stream`, OpenAI via `chat.completions.create(stream=True, max_completion_tokens=...)` WR-01-shape, Google via `generate_content_stream()`), falls back to Anthropic for unknown/empty provider, never logs `api_key`
- `resolve_chat_target(agent_id)` resolves `(provider, api_key, model)` exactly for the chosen agent via `read_env_raw` + `crypto.decrypt_value` + `style_extract.MODEL_DRAFT_DEFAULTS` — no duplicated model table, no separate Anthropic-only path
- `GET /chat/{agent_id}/embed` renders a genuinely chrome-less partial (own `<!doctype html>`, zero `{% extends %}`) with only `/static`-relative resources
- `POST /chat/{agent_id}/send` streams real SSE frames (`text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`), encoding multi-line chunks as multiple `data:` continuation lines, terminating with `event: done` or `event: error`
- `webui/static/chat.js`: vanilla `fetch()` + `ReadableStream` SSE client (no library), incremental buffer parsing on `\n\n` boundaries, appends decoded text to the current assistant bubble in `#chat-log`
- `webui/static/chat.css`: minimal local-only chat styling (bubbles, input, controls)

## Task Commits

Each task was committed atomically:

1. **Task 1: Provider-agnostic streaming adapter webui/src/chat.py** - `57bcf7b` (feat, TDD-style: tests + implementation)
2. **Task 2: Chat routes (embed + SSE send) + chrome-less partial + vanilla SSE client** - `b749323` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `webui/src/chat.py` - Streaming adapter: `resolve_chat_target`, `_stream_anthropic/_openai/_google`, `_STREAM_DISPATCH`, `stream_chat`, `ChatConfigError`
- `webui/src/templates/chat.html` - Chrome-less chat partial with `#chat-log`, `#chat-input`, send/reset buttons, `data-agent-id` root attribute
- `webui/static/chat.js` - Vanilla SSE client (fetch + ReadableStream, incremental frame parsing)
- `webui/static/chat.css` - Local-only chat styling
- `webui/tests/test_chat.py` - 11 tests for `chat.py` (streaming per provider, fallback, key resolution, invalid agent_id, missing key, no-api-key-in-log)
- `webui/tests/test_endpoints_chat.py` - 7 endpoint tests (auth, chrome-less rendering, SSE streaming, 404/400 split)
- `webui/src/main.py` - Added `StreamingResponse` import + `from . import chat`; added `chat_embed`, `chat_send`, `_sse_data_frame` helper

## Decisions Made
- Kept `llm.py` completely untouched (drift-guard `test_llm_sync.py` still passes) — new streaming logic lives exclusively in the new webui-only `chat.py` module, per the plan's `<design_note>` reconciliation of D-59 (Phase-5 adapter reuse intent) vs. D-62 (real streaming) vs. WR-06 (byte-identical sync contract)
- Reused `style_extract.MODEL_DRAFT_DEFAULTS` directly rather than introducing a third copy of the model-defaults table
- `/send` intentionally has no agent-existence pre-check (unlike `/embed`) — an unknown-but-valid `agent_id` surfaces as 400 via `ChatConfigError` (no stored key) rather than 404, matching the plan-checker guidance provided in the execution prompt

## Deviations from Plan

None - plan executed exactly as written (including the design_note's D-59/D-62/drift-guard reconciliation, which was itself part of the plan).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required. This plan reuses existing per-agent LLM credentials already configured via the WebUI's IMAP/LLM-API-Key fieldset.

## Next Phase Readiness

- SSE streaming risk (Uvicorn/FastAPI + browser incremental rendering) is retired end-to-end; `chat.py` + `/chat/{agent_id}/send` + `chat.js` form a working walking skeleton
- Ready for Plan 07-02 (system prompt injection: context.md + style.md + agent status via `state_reader`) — `stream_chat`/`resolve_chat_target` signatures are stable extension points
- Ready for Plan 07-03 (rate limiting D-60, `mail_context` field D-65) — `/send` route has no rate limit yet (T-07-04 accepted for this walking skeleton) and takes only `message` (no `mail_context` yet, deferred per plan scope)
- Ready for Plan 07-04 (main WebUI chat embedding) — `chat.html` partial is already chrome-less and reusable
- No blockers

## Self-Check: PASSED

- `webui/src/chat.py` exists: FOUND
- `webui/src/templates/chat.html` exists: FOUND
- `webui/static/chat.js` exists: FOUND
- `webui/static/chat.css` exists: FOUND
- `webui/tests/test_chat.py` exists: FOUND
- `webui/tests/test_endpoints_chat.py` exists: FOUND
- Commit `57bcf7b` found in git log: FOUND
- Commit `b749323` found in git log: FOUND
- `cd webui && python -m pytest -q` → 225 passed, 3 skipped (baseline was 207 passed/3 skipped; +18 new tests)
- `cd webui && python -m pytest tests/test_llm_sync.py tests/test_model_defaults_sync.py -q` → both green (drift-guards intact)
- All plan-level acceptance criteria (grep checks for `def stream_chat`, `MODEL_DRAFT_DEFAULTS` import, `max_completion_tokens`, route paths, `text/event-stream`, zero `extends`, zero external URLs) verified passing

---
*Phase: 07-agenten-chat-im-webui-v1-3*
*Completed: 2026-07-17*
