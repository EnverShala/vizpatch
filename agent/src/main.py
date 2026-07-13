"""Polling-Loop-Entry-Point. Verdrahtet alle Module."""
from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from anthropic import Anthropic

from . import classify, generate, pii, state
from .config import Config, load_config
from .draft import build_reply_draft
from .imap_client import ImapClient
from .logging_setup import setup_logging


_shutdown = False


def _handle_sigterm(signum, frame):
    global _shutdown
    logging.getLogger("vizpatch").info("shutdown_requested", extra={"signal": signum})
    _shutdown = True


def _compute_since(config: Config) -> datetime:
    """Compute the 'since' timestamp for IMAP fetch:
    - First run: now - BACKFILL_DAYS
    - Later:     first_run_at - 1h overlap
    """
    first_run = state.get_or_set_first_run(config.state_db)
    if first_run.tzinfo is None:
        first_run = first_run.replace(tzinfo=timezone.utc)
    return min(first_run - timedelta(hours=1), datetime.now(timezone.utc) - timedelta(days=config.backfill_days))


def _process_one(msg, config: Config, anthropic_client: Anthropic, logger: logging.Logger, imap: "ImapClient") -> None:
    """Process a single email: classify, generate draft if needed, append to Drafts."""
    message_id = msg.headers.get("message-id", [""])
    if isinstance(message_id, tuple):
        message_id = message_id[0] if message_id else ""
    if not message_id:
        logger.warning("skip_no_message_id", extra={"from": msg.from_, "subject": msg.subject})
        return

    if state.is_processed(config.state_db, message_id):
        return

    import re as _re
    body = msg.text or (_re.sub(r'<[^>]+>', ' ', msg.html).strip() if msg.html else "") or ""
    classification = classify.classify_email(
        from_address=msg.from_ or "",
        subject=msg.subject or "",
        body=body,
        config=config,
        client=anthropic_client,
        logger=logger,
    )

    if classification == "IGNORE":
        state.mark_processed(
            db_path=config.state_db,
            message_id=message_id,
            uid=int(msg.uid) if msg.uid else 0,
            from_address=msg.from_ or "",
            subject=msg.subject or "",
            classification="ignored",
            draft_created=False,
        )
        return

    # REPLY_NEEDED path
    body_for_llm = pii.redact(body) if config.enable_pii_redaction else body

    # D-26: Konversations-History aus IMAP frisch fetchen
    references_raw = msg.headers.get("references", [""])
    in_reply_to_raw = msg.headers.get("in-reply-to", [""])
    if isinstance(references_raw, tuple):
        references_raw = list(references_raw)
    else:
        references_raw = [references_raw] if isinstance(references_raw, str) else list(references_raw)
    if isinstance(in_reply_to_raw, tuple):
        in_reply_to_raw = list(in_reply_to_raw)
    else:
        in_reply_to_raw = [in_reply_to_raw] if isinstance(in_reply_to_raw, str) else list(in_reply_to_raw)
    references = [r for r in (references_raw + in_reply_to_raw) if r]

    if references:
        conversation_history = imap.fetch_thread_history(references)
    else:
        conversation_history = imap.fetch_sender_history(msg.from_ or "")

    draft_text = generate.generate_draft_text(
        from_address=msg.from_ or "",
        subject=msg.subject or "",
        body=body_for_llm,
        config=config,
        client=anthropic_client,
        logger=logger,
        conversation_history=conversation_history,
    )
    raw_bytes = build_reply_draft(
        original=msg,
        draft_text=draft_text,
        own_email=config.own_email_address,
        own_display_name=config.own_display_name,
    )

    # append to IMAP Drafts (client is passed in as arg; append happens outside)
    return raw_bytes, message_id


def _poll_once(config: Config, anthropic_client: Anthropic, logger: logging.Logger) -> None:
    since = _compute_since(config)
    with ImapClient(config, logger=logger) as imap:
        logger.info("poll_start", extra={"since": since.isoformat(), "folder": config.imap_inbox_folder})
        count = 0
        for msg in imap.fetch_new_messages(since=since, own_address=config.own_email_address):
            count += 1
            try:
                result = _process_one(msg, config, anthropic_client, logger, imap)
                if result is not None:
                    raw_bytes, message_id = result
                    imap.append_to_drafts(raw_bytes)
                    state.mark_processed(
                        db_path=config.state_db,
                        message_id=message_id,
                        uid=int(msg.uid) if msg.uid else 0,
                        from_address=msg.from_ or "",
                        subject=msg.subject or "",
                        classification="reply_needed",
                        draft_created=True,
                    )
            except Exception as e:
                logger.exception(
                    "process_failed",
                    extra={"from": msg.from_, "subject": msg.subject, "error": str(e)},
                )
        logger.info("poll_done", extra={"processed": count})


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    try:
        config = load_config()
    except RuntimeError as e:
        # setup basic logging so error is visible
        setup_logging("INFO")
        logging.getLogger("vizpatch").error("config_failed", extra={"error": str(e)})
        return 1

    logger = setup_logging(config.log_level)
    logger.info(
        "startup",
        extra={
            "imap_host": config.imap_host,
            "imap_user": config.imap_user,
            "poll_interval_seconds": config.poll_interval_seconds,
        },
    )
    state.init_db(config.state_db)

    anthropic_client = Anthropic(api_key=config.anthropic_api_key)

    backoff_seconds = config.poll_interval_seconds
    while not _shutdown:
        try:
            _poll_once(config, anthropic_client, logger)
            backoff_seconds = config.poll_interval_seconds  # reset on success
        except Exception as e:
            logger.exception("poll_cycle_failed", extra={"error": str(e)})
            backoff_seconds = min(backoff_seconds * 2, 3600)

        # sleep in small chunks so shutdown-signal wird schnell erkannt
        slept = 0
        while slept < backoff_seconds and not _shutdown:
            time.sleep(min(5, backoff_seconds - slept))
            slept += 5

    logger.info("shutdown_complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
