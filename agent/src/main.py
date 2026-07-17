"""Polling-Loop-Entry-Point. Verdrahtet alle Module."""
from __future__ import annotations

import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from dataclasses import replace

from . import classify, generate, pii, state, status_writer
from .config import Config, DecryptionError, discover_agents, load_agent_config
from .draft import build_reply_draft
from .imap_client import ImapClient
from .logging_setup import setup_logging


_shutdown = False


def _handle_sigterm(signum, frame):
    global _shutdown
    logging.getLogger("vizpatch").info("shutdown_requested", extra={"signal": signum})
    _shutdown = True


class _AgentLoggerAdapter(logging.LoggerAdapter):
    """LoggerAdapter, der self.extra (agent_id) mit Call-Site-extra MERGT statt es zu
    verwerfen (Python-Default-process() überschreibt sonst kwargs["extra"] komplett).
    Damit trägt JEDER Log-Record der Agent-Verarbeitung die agent_id (T-05-30).
    """

    def process(self, msg, kwargs):
        extra = kwargs.get("extra") or {}
        kwargs["extra"] = {**self.extra, **extra}
        return msg, kwargs


def _compute_since(config: Config) -> datetime:
    """Compute the 'since' timestamp for IMAP fetch:
    - First run: now - BACKFILL_DAYS
    - Later:     first_run_at - 1h overlap
    """
    first_run = state.get_or_set_first_run(config.state_db)
    if first_run.tzinfo is None:
        first_run = first_run.replace(tzinfo=timezone.utc)
    return min(first_run - timedelta(hours=1), datetime.now(timezone.utc) - timedelta(days=config.backfill_days))


def _process_one(msg, config: Config, logger: logging.Logger, imap: "ImapClient") -> None:
    """Process a single email: classify, generate draft if needed, append to Drafts."""
    # CR-01: Default MUSS ein String sein — ein Listen-Default wie [""] ist truthy,
    # rutscht am Skip-Guard vorbei und crasht später in sqlite
    # ("type 'list' is not supported"). imap-tools liefert Header-Werte je nach
    # Version als tuple ODER list — beide Container-Typen normalisieren.
    raw_message_id = msg.headers.get("message-id", "")
    if isinstance(raw_message_id, (tuple, list)):
        raw_message_id = raw_message_id[0] if raw_message_id else ""
    message_id = (raw_message_id or "").strip()
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
        logger=logger,
        conversation_history=conversation_history,
    )
    raw_bytes = build_reply_draft(
        original=msg,
        draft_text=draft_text,
        own_email=config.own_email_address,
        own_display_name=config.own_display_name,
    )

    # append to IMAP Drafts (append happens outside)
    return raw_bytes, message_id


def _imap_timeout_seconds() -> float:
    return float(os.getenv("IMAP_TIMEOUT_SECONDS", "60"))


def _poll_once(config: Config, logger: logging.Logger) -> None:
    since = _compute_since(config)
    with ImapClient(config, logger=logger, timeout=_imap_timeout_seconds()) as imap:
        logger.info("poll_start", extra={"since": since.isoformat(), "folder": config.imap_inbox_folder})
        count = 0
        for msg in imap.fetch_new_messages(since=since, own_address=config.own_email_address):
            count += 1
            try:
                result = _process_one(msg, config, logger, imap)
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


CONFIG_WAIT_SECONDS = 30


def _agent_data_root() -> Path:
    return Path(os.getenv("AGENT_DATA_ROOT", "/data"))


def _status_file_for(agent_id: str) -> Path:
    return _agent_data_root() / "agents" / agent_id / "agent_status.json"


# Drafts-Resolution-Cache: agent_id -> (env_mtime, folder, detection_source).
# Verhindert, dass jeder Poll-Zyklus erneut per IMAP-Verbindung probt — Invalidierung
# erfolgt anhand der mtime der Agent-.env-Datei (ändert sich z.B. bei explizitem
# IMAP_DRAFTS_FOLDER-Save im WebUI).
_drafts_cache: dict[str, tuple[float, str, str]] = {}


def _resolve_drafts_folder(
    config: Config, agent_dir: Path, status_file: Path, logger: logging.Logger
) -> tuple[Config, str]:
    """Resolution-Chain für den Drafts-Ordner (pro Agent):
      1. User hat IMAP_DRAFTS_FOLDER explizit gesetzt → respektieren
      2. IMAP SPECIAL-USE Auto-Discovery (\\Drafts-Flag), Ergebnis pro agent_id gecacht
      3. Statischer Provider-Default (bereits in config.imap_drafts_folder)
    Schreibt das Ergebnis in die STATUS-DATEI DIESES Agenten.

    Returns (config, detection_source) — die Source wird von _run_cycle an den
    Erfolgs-Status-Write durchgereicht, damit sie NICHT von einem generischen
    Wert überschrieben wird (Review WR-02: die WebUI rendert die grüne
    "automatisch erkannt"-Bestätigung nur für special-use/provider/explicit).
    """
    if config.imap_drafts_folder_explicit:
        status_writer.write_status(
            drafts_folder=config.imap_drafts_folder,
            detection_source="explicit",
            status_file=status_file,
        )
        return config, "explicit"

    env_path = agent_dir / ".env"
    try:
        env_mtime = env_path.stat().st_mtime
    except OSError:
        env_mtime = 0.0

    cached = _drafts_cache.get(config.agent_id)
    if cached is not None and cached[0] == env_mtime:
        _, folder, source = cached
        status_writer.write_status(drafts_folder=folder, detection_source=source, status_file=status_file)
        return replace(config, imap_drafts_folder=folder), source

    detected: str | None = None
    try:
        with ImapClient(config, logger=logger, timeout=_imap_timeout_seconds()) as imap:
            detected = imap.detect_drafts_folder()
    except Exception as e:
        logger.warning("drafts_folder_probe_failed", extra={"error": str(e), "agent_id": config.agent_id})

    if detected:
        folder, source = detected, "special-use"
    else:
        folder, source = config.imap_drafts_folder, "provider"

    _drafts_cache[config.agent_id] = (env_mtime, folder, source)
    logger.info("drafts_folder_resolved", extra={"folder": folder, "source": source, "agent_id": config.agent_id})
    status_writer.write_status(drafts_folder=folder, detection_source=source, status_file=status_file)
    return replace(config, imap_drafts_folder=folder), source


def _fail_agent(agent_id: str, status_file: Path, logger: logging.Logger, error: Exception) -> None:
    """Loggt + isoliert einen fehlgeschlagenen Agenten: error + last_cycle in DESSEN
    status_file, kein Re-Raise — der Gesamt-Zyklus läuft für die übrigen Agenten weiter
    (T-05-29/T-05-30/T-05-10, MA-03).
    """
    logger.error("agent_cycle_failed", extra={"agent_id": agent_id, "error": str(error)})
    status_writer.write_status(
        error=str(error),
        status_file=status_file,
        last_cycle=datetime.now(timezone.utc).isoformat(),
    )


def _run_cycle(logger: logging.Logger) -> None:
    """Ein Poll-Zyklus: verarbeitet ALLE Agenten unter AGENTS_CONFIG_ROOT sequentiell.

    discover_agents() wird INNERHALB des Zyklus aufgerufen (frisch pro Durchlauf) —
    ein neuer/aktivierter Agent wird ohne Container-Restart ab dem nächsten Zyklus
    verarbeitet. Ein Fehler EINES Agenten (Auth/IMAP/LLM/Decrypt, inkl. Timeout) wird
    geloggt + isoliert; die übrigen Agenten laufen im selben Zyklus weiter.
    """
    for agent_id, agent_dir in discover_agents():
        if _shutdown:
            return

        agent_logger = _AgentLoggerAdapter(logger, {"agent_id": agent_id})
        status_file = _status_file_for(agent_id)

        try:
            cfg = load_agent_config(agent_id, agent_dir)
            if not cfg.agent_enabled:
                agent_logger.debug("agent_disabled_skip", extra={"agent_id": agent_id})
                continue
            state.init_db(cfg.state_db)
            cfg, drafts_source = _resolve_drafts_folder(cfg, agent_dir, status_file, agent_logger)
            _poll_once(cfg, agent_logger)
        except DecryptionError as e:
            _fail_agent(agent_id, status_file, agent_logger, e)
            continue
        except RuntimeError as e:
            _fail_agent(agent_id, status_file, agent_logger, e)
            continue
        except Exception as e:
            _fail_agent(agent_id, status_file, agent_logger, e)
            continue
        else:
            # WR-02: die echte detection_source (special-use/provider/explicit)
            # aus der Resolution durchreichen — ein generisches "ok" würde die
            # WebUI-Bestätigung "Drafts-Ordner automatisch erkannt" unterdrücken.
            status_writer.write_status(
                drafts_folder=cfg.imap_drafts_folder,
                detection_source=drafts_source,
                error=None,
                status_file=status_file,
                last_cycle=datetime.now(timezone.utc).isoformat(),
            )


def _wait_for_agents(logger: logging.Logger) -> None:
    """Wartet idle, solange KEIN Agent existiert, dessen Config ladbar UND aktiv ist.

    Generalisiert die alte Single-Config-Wait-Loop: 0 konfigurierte/aktive Agenten
    bedeuten "warten", nicht "crashen" — der Container kann sofort mit Compose
    hochgezogen werden, bevor im WebUI der erste Agent angelegt wurde.
    """
    while not _shutdown:
        agents = discover_agents()
        ready = 0
        for agent_id, agent_dir in agents:
            try:
                cfg = load_agent_config(agent_id, agent_dir)
            except (DecryptionError, RuntimeError) as e:
                # WR-03: Fehler SICHTBAR machen statt still weiterzuwarten — sonst
                # hängt ein einziger Agent mit kaputtem Fernet-Token (SEC-03-Fall)
                # oder fehlendem Pflichtfeld ewig in "Wartet auf nächsten Zyklus",
                # ohne dass je ein error in seine agent_status.json geschrieben wird.
                # _fail_agent isoliert den Fehler pro Agent; der Wait-Loop (und damit
                # alle übrigen Agenten) läuft normal weiter.
                _fail_agent(agent_id, _status_file_for(agent_id), logger, e)
                continue
            if cfg.agent_enabled:
                ready += 1

        if ready > 0:
            return

        logger.info(
            "waiting_for_agents",
            extra={"found": len(agents), "active": ready, "retry_in_seconds": CONFIG_WAIT_SECONDS},
        )
        slept = 0
        while slept < CONFIG_WAIT_SECONDS and not _shutdown:
            time.sleep(min(5, CONFIG_WAIT_SECONDS - slept))
            slept += 5


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGINT, _handle_sigterm)

    # Basic-Logging vor Config-Load — damit Wait-Loop-Meldungen sichtbar sind
    setup_logging("INFO")
    boot_logger = logging.getLogger("vizpatch")

    _wait_for_agents(boot_logger)
    if _shutdown:
        return 0

    logger = setup_logging(os.getenv("LOG_LEVEL", "INFO"))
    poll_interval_seconds = int(os.getenv("POLL_INTERVAL_SECONDS", "300"))
    logger.info("startup", extra={"poll_interval_seconds": poll_interval_seconds})

    backoff_seconds = poll_interval_seconds
    while not _shutdown:
        try:
            _run_cycle(logger)
            backoff_seconds = poll_interval_seconds  # reset on success
        except Exception as e:
            # Sollte praktisch nie greifen (jeder Agent ist per try/except isoliert) —
            # verbleibende Absicherung gegen Fehler AUSSERHALB der Agent-Schleife selbst.
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
