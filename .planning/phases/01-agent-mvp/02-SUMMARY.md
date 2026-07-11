# Plan 02-imap-draft — Summary

**Plan ID:** 02-imap-draft
**Title:** IMAP-Client, Draft-Builder, PII-Redaction
**Wave:** 2 (parallel to Plan 03-llm)
**Depends on:** 01-skeleton
**Requirements covered:** AGT-01, AGT-05, AGT-09, AGT-10

## Files created

- `D:\Vizionists\kiemailagent\agent\src\imap_client.py` — `ImapClient` context-manager wrapping `imap_tools.MailBox` / `MailBoxUnencrypted`. Exposes `fetch_new_messages(since, own_address) -> Iterator[MailMessage]` and `append_to_drafts(raw_msg_bytes: bytes) -> None`. Logs `imap_connected`, `imap_logout_failed`, `draft_appended` structured events.
- `D:\Vizionists\kiemailagent\agent\src\draft.py` — `build_reply_draft(original, draft_text, own_email, own_display_name) -> bytes`. Handles `Re:`/`AW:` prefix idempotently, `In-Reply-To` + `References` threading headers (reads from `original.headers`), UTF-8 quoted body with `> ` prefix (cap 200 lines), German-formatted quote header (`Am dd.mm.YYYY HH:MM schrieb …:`).
- `D:\Vizionists\kiemailagent\agent\src\pii.py` — `redact(text: str) -> str` for IBAN (regex-only) and Luhn-validated credit-card numbers. Phone-like non-Luhn digit blocks are preserved. Safe on empty/None-ish input.

## Tasks completed

- [x] Task 2.1 — `imap_client.py`
- [x] Task 2.2 — `draft.py`
- [x] Task 2.3 — `pii.py`

## Deviations from plan

None. All code written verbatim from the `<action>` blocks in `02-imap-draft.md`.

## Verification

Structural acceptance criteria met:
- `ImapClient` is a context manager (`__enter__`/`__exit__`) with `fetch_new_messages` + `append_to_drafts`; own-address filter is case-insensitive.
- `build_reply_draft` returns `bytes`, sets `In-Reply-To` / `References` from `original.headers["message-id"]` / `["references"]`, adds `Re:` prefix when missing, UTF-8 content.
- `redact` uses IBAN regex (`[A-Z]{2}\d{2}[A-Z0-9]{11,30}`) + Luhn-checked CC regex; returns input as-is on empty string.

Runtime import checks (`python -c "from src.<mod> import ..."`) were intentionally skipped per execution instructions (deps not installed on host).

## Notes for Plan 04 (main.py wiring)

- `ImapClient` MUST be used inside a `with` block — plain calls trip the internal `assert self._mailbox is not None`. Wrap each poll cycle in one `with ImapClient(config) as client:` context.
- `append_to_drafts(raw_msg_bytes)` expects the raw bytes returned by `build_reply_draft(...)` — no extra serialization needed. Pipe the return value straight through.
- `pii.redact()` operates on plain-text bodies and should be applied **before** passing content to both `classify.run(...)` and `generate.run(...)` when `config.enable_pii_redaction` is true. Apply once to `msg.text` (or `msg.html_to_text()` fallback), not to the raw `MailMessage`.
- Own-sender filtering is already done inside `fetch_new_messages`; `main.py` still needs a state-DB `message_id` dedup check to avoid re-drafting on subsequent polls.
- `fetch_new_messages` filters by `date_gte=since.date()` — coarser than a timestamp. Callers should still de-dupe via `state.processed_emails` and re-check `msg.date >= since` if sub-day precision matters.
- The `\Draft` flag is set via `MailMessageFlags.DRAFT`. If a provider rejects the flag name at runtime, this is the single point to swap to a raw string constant.
- Threading uses `original.headers["message-id"]` (imap-tools normalizes to lowercase). Missing `Message-ID` means no threading headers get written — the draft will appear as a standalone message in the client. Log a warning in `main.py` when this happens so provider-side issues surface.
