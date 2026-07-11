# Plan 03-llm — Summary

**Plan ID:** 03-llm
**Title:** LLM-Klassifikation und Draft-Generierung
**Phase:** 01-agent-mvp
**Wave:** 2 (parallel with 02-imap-draft, depends only on 01-skeleton)

## Created Files

- `agent/src/classify.py` — Anthropic Haiku call for REPLY_NEEDED / IGNORE classification
- `agent/src/generate.py` — Anthropic Sonnet call for draft text generation with `context.md` injection

## Tasks Completed

- [x] Task 3.1 — `agent/src/classify.py` written verbatim from plan
- [x] Task 3.2 — `agent/src/generate.py` written verbatim from plan

## Deviations from Plan

None. Both files were written exactly as specified in the plan's `<action>` blocks.

## Acceptance Criteria Verification (structural)

### `classify.py`
- Exports `classify_email(from_address, subject, body, config, client=None, logger=None)` returning `Literal["REPLY_NEEDED", "IGNORE"]`
- `MAX_BODY_CHARS = 2000`; `_extract_body_snippet` truncates with `[... truncated ...]` marker
- `_parse_response` defaults to `"IGNORE"` on unclear responses (safety default)
- `max_tokens=20`, `temperature=0.0` set on `client.messages.create`
- `logger.info("classified", extra={...})` with `from`, `subject`, `classification`, `raw_response`
- Injectable `client` parameter for dependency injection in tests

### `generate.py`
- Exports `generate_draft_text(from_address, subject, body, config, client=None, logger=None) -> str`
- `_extract_company_name` uses regex `r"^#\s+(?:Firmen-Kontext für\s+)?(.+?)$"` on first H1 with fallback `"der Firma"`
- Injects full `context.md` via `{context_md_full}` placeholder
- Uses `config.model_draft`, `config.llm_max_tokens_draft`, `config.llm_temperature_draft`
- `logger.info("draft_generated", extra={"draft_length": ...})`
- Injectable `client` parameter for tests

## Notes for Plan 04 (integration)

Both modules follow a consistent signature usable by the polling loop in `main.py`:

- **`classify_email(from_address, subject, body, config, client=None, logger=None) -> Literal["REPLY_NEEDED", "IGNORE"]`**
  - Body truncated to 2000 chars internally before LLM call (no need to pre-truncate upstream)
  - Returns safe default `"IGNORE"` on ambiguous LLM output — the main loop can trust the return value without extra guards
  - Uses `config.model_classify` (default `claude-haiku-4-5`)

- **`generate_draft_text(from_address, subject, body, config, client=None, logger=None) -> str`**
  - Returns stripped draft text only (no headers, no subject) — Plan 02's `draft.py` supplies RFC-5322 headers and threading
  - Full `context.md` is injected into the prompt from `config.context_md` (already loaded by `config.load_config()`)
  - Uses `config.model_draft` (default `claude-sonnet-4-6`) with configurable `max_tokens` / `temperature`
  - Note: body is NOT length-limited before the Sonnet call (unlike classify) — long-body handling is deferred; monitor token usage in Plan 04

- **Shared conventions:**
  - Both accept an injectable `Anthropic` client → tests in Plan 05 can pass mocks without touching the network
  - Both use their own child loggers (`kea.classify`, `kea.generate`) — Plan 04's `logging_setup.py` should ensure the root `kea` logger is configured with the JSON formatter
  - Both raise natively on `anthropic` SDK errors — the main polling loop must wrap calls in try/except and continue on transient failures
