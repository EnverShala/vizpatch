"""Schreibstil-Extraktion (D-52..D-57, STY-01/04/05).

Reine Service-Funktion `extract_style(agent_id) -> str`: holt die letzten N
gesendeten Mails des Agenten per IMAP (WebUI verbindet sich selbst, D-53),
filtert auf echte Antworten, redigiert PII, kombiniert mit der optionalen
manuellen Stil-Angabe des Betreibers und destilliert per LLM (Draft-Modell
des Agenten, D-55, provider-agnostischer Adapter aus llm.py) genau EIN
`style.md`. Crasht nie — fehlendes/leeres Material führt zu
`StyleExtractionEmpty` statt einer Exception aus dem IMAP/LLM-Stack (STY-05).

api_key/IMAP-Passwort werden NIE in Log-Statements eingebettet (T-05-08-Muster).
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from imap_tools import MailBox, MailBoxUnencrypted

from . import crypto, llm, pii
from .agents_io import read_env_raw, read_style_note
from .provider_config import resolve_imap_config

logger = logging.getLogger(__name__)

# Draft-Modell-Spiegel der agent-config MODEL_DEFAULTS-Draft-Spalte (D-55).
# Drift-Guard: webui/tests/test_model_defaults_sync.py hält diese Werte
# konsistent mit agent/src/config.py::MODEL_DEFAULTS.
MODEL_DRAFT_DEFAULTS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-5.1",
    "google": "gemini-2.5-pro",
}

MAX_BODY_CHARS = 800
MAX_STYLE_MD_CHARS = 4000
MIN_USABLE_MAILS = 3
DEFAULT_STYLE_SAMPLE_COUNT = 30
_IMAP_TIMEOUT_SECONDS = 20.0


class StyleExtractionError(RuntimeError):
    """Allgemeiner Fehler bei der Stil-Extraktion (fehlender Key, LLM-Fehler)."""


class StyleExtractionEmpty(RuntimeError):
    """Zu wenig verwertbares Material (weder Mails noch Freitext) — STY-05.

    Wird von der Endpoint-Schicht (Plan 06.03) in einen typisierten Hinweis
    im WebUI übersetzt, statt als generischer 500er durchzuschlagen.
    """


def _is_real_reply(msg) -> bool:
    """Claude's Discretion (06-CONTEXT.md): echte Antwort-Mail =
    kein Fwd/Wg, In-Reply-To vorhanden ODER Subject startswith 're:'/'aw:',
    UND Body-Länge nach strip >= 40 Zeichen und mindestens 2 Wörter
    (verwirft Ein-Wort-Antworten wie 'Danke.')."""
    subject = (msg.subject or "").strip().lower()
    if subject.startswith("fwd:") or subject.startswith("wg:"):
        return False

    body = msg.text or (re.sub(r"<[^>]+>", " ", msg.html).strip() if msg.html else "") or ""
    body = body.strip()
    if len(body) < 40:
        return False
    if len(body.split()) < 2:
        return False

    in_reply_to = msg.headers.get("in-reply-to") if hasattr(msg, "headers") else None
    if isinstance(in_reply_to, (tuple, list)):
        in_reply_to = in_reply_to[0] if in_reply_to else ""
    has_in_reply_to = bool((in_reply_to or "").strip())
    is_reply_subject = subject.startswith("re:") or subject.startswith("aw:")

    return has_in_reply_to or is_reply_subject


def _detect_sent_folder(mailbox, fallback: str) -> str:
    """SPECIAL-USE-Erkennung (RFC 6154) analog `detect_drafts_folder()`
    (agent/src/imap_client.py) — \\Sent statt \\Drafts. Fallback bei
    fehlender Announcement oder Fehler."""
    try:
        for folder_info in mailbox.folder.list():
            flags = tuple(str(f) for f in (folder_info.flags or ()))
            if any("Sent" in f for f in flags):
                logger.info(
                    "sent_folder_detected_via_special_use",
                    extra={"folder": folder_info.name, "flags": flags},
                )
                return folder_info.name
    except Exception as e:
        logger.warning("special_use_sent_detection_failed", extra={"error": str(e)})
    return fallback


def _resolve_imap_connection_settings(env: dict) -> dict:
    """Analog config._build_config: IMAP_HOST-Override > resolve_imap_config."""
    imap_host_override = (env.get("IMAP_HOST") or "").strip()
    imap_user = (env.get("IMAP_USER") or "").strip()
    if imap_host_override:
        return {
            "host": imap_host_override,
            "port": int(env.get("IMAP_PORT") or "993"),
            "ssl": (env.get("IMAP_USE_SSL") or "true").lower() == "true",
            "sent": (env.get("IMAP_SENT_FOLDER") or "").strip() or "Sent",
        }
    cfg = dict(resolve_imap_config(imap_user))
    cfg["sent"] = (env.get("IMAP_SENT_FOLDER") or "").strip() or cfg["sent"]
    return cfg


def _fetch_sent_mail_bodies(
    env: dict, imap_password: str, sample_count: int, enable_pseudonym: bool = True
) -> tuple[list[str], "pii.Anonymizer | None"]:
    """Holt bis zu `sample_count` echte Antwort-Mails aus dem Gesendet-Ordner,
    pseudonymisiert (reversibel, ANON-03) VOR dem Truncate, truncated je Body.
    Crasht nie (T-06-03): fehlender/leerer Sent-Ordner oder gescheiterte
    IMAP-Verbindung -> leere Liste, analog `fetch_sender_history` im Agent.

    Gibt zusätzlich die verwendete `Anonymizer`-Instanz zurück (oder `None`
    bei deaktiviertem Flag), damit `extract_style` denselben Mapping-Kontext
    für die De-Anonymisierung des LLM-Outputs wiederverwenden kann (D-05).
    """
    imap_user = (env.get("IMAP_USER") or "").strip()
    imap_sent_folder_explicit = (env.get("IMAP_SENT_FOLDER") or "").strip()
    messages: list = []
    anonymizer = pii.Anonymizer() if enable_pseudonym else None

    try:
        settings = _resolve_imap_connection_settings(env)
        mailbox_cls = MailBox if settings["ssl"] else MailBoxUnencrypted
        with mailbox_cls(
            host=settings["host"], port=settings["port"], timeout=_IMAP_TIMEOUT_SECONDS
        ) as mailbox:
            mailbox.login(imap_user, imap_password)
            sent_folder = imap_sent_folder_explicit or _detect_sent_folder(mailbox, settings["sent"])
            try:
                mailbox.folder.set(sent_folder)
                messages = list(
                    mailbox.fetch(reverse=True, mark_seen=False, limit=sample_count * 3)
                )
            except Exception as e:
                logger.warning("style_sent_fetch_failed", extra={"folder": sent_folder, "error": str(e)})
                messages = []
    except Exception as e:
        logger.warning("style_imap_connect_failed", extra={"error": str(e)})
        messages = []

    usable = [m for m in messages if _is_real_reply(m)][:sample_count]

    bodies: list[str] = []
    for msg in usable:
        body = msg.text or (re.sub(r"<[^>]+>", " ", msg.html).strip() if msg.html else "") or ""
        body = body.strip()
        # Pitfall 1 (10-RESEARCH.md): erst pseudonymisieren, DANN schneiden —
        # sonst wird ein PII-Wert genau an der MAX_BODY_CHARS-Grenze zerrissen.
        if enable_pseudonym and anonymizer is not None:
            body = anonymizer.anonymize(body)
        bodies.append(body[:MAX_BODY_CHARS])
    return bodies, anonymizer


def extract_style(agent_id: str) -> str:
    """Destilliert style.md aus Gesendet-Mails + optionalem Freitext (D-52).

    Reine Service-Funktion — keine Docker-/Endpoint-Logik (Plan 06.03 ruft dies
    aus /style/generate + /style/relearn). ValueError propagiert unverändert
    bei invalidem agent_id (agents_io._agent_dir-Guard, T-06-04).
    """
    env = read_env_raw(agent_id)

    raw_key = (env.get("LLM_API_KEY") or "").strip()
    if not raw_key:
        raise StyleExtractionError("Kein API-Key für diesen Agenten gespeichert")
    api_key = crypto.decrypt_value(raw_key)

    raw_password = (env.get("IMAP_PASSWORD") or "").strip()
    imap_password = crypto.decrypt_value(raw_password) if raw_password else ""

    provider = (env.get("LLM_PROVIDER") or "anthropic").strip().lower()
    model = (env.get("MODEL_DRAFT") or "").strip() or MODEL_DRAFT_DEFAULTS.get(
        provider, MODEL_DRAFT_DEFAULTS["anthropic"]
    )

    sample_count = int(os.getenv("STYLE_SAMPLE_COUNT") or str(DEFAULT_STYLE_SAMPLE_COUNT))

    # ANON-03: Default AN, "aus" = Verhalten wie vor Phase 10 (Klartext-Rückfall).
    enable_pseudonym = (env.get("ENABLE_PII_REDACTION") or "true").strip().lower() != "false"

    bodies, anonymizer = _fetch_sent_mail_bodies(env, imap_password, sample_count, enable_pseudonym)
    style_note = read_style_note(agent_id)

    if len(bodies) < MIN_USABLE_MAILS and not style_note.strip():
        raise StyleExtractionEmpty(
            "Zu wenig verwertbare gesendete Mails und keine manuelle Stil-Angabe — "
            "kein Schreibstil-Profil erzeugt."
        )

    prompt_path = Path(os.getenv("WEBUI_STYLE_EXTRACT_PROMPT", "/app/prompts/style-extract.txt"))
    template = prompt_path.read_text(encoding="utf-8")
    sent_mails_block = "\n\n---\n\n".join(bodies) if bodies else "[keine verwertbaren Mails]"
    prompt = template.format(
        sent_mails=sent_mails_block,
        manual_style_note=style_note.strip() or "[keine Angabe]",
    )

    text = llm.llm_call(
        provider,
        api_key,
        model,
        prompt,
        1500,
        0.3,
    )
    logger.info(
        "style_extracted",
        extra={"input_mail_count": len(bodies), "output_length": len(text), "model": model},
    )
    # D-05-Konsistenz: kein wörtlich zitierter Platzhalter im style.md-Output.
    if enable_pseudonym and anonymizer is not None:
        text = anonymizer.deanonymize(text)
    return text.strip()[:MAX_STYLE_MD_CHARS]
