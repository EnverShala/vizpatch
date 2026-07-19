"""LLM-Draft-Generation via den LLM-Adapter."""
from __future__ import annotations

import logging
import re
from typing import Optional

from . import llm, pii
from .config import Config


def _extract_company_name(context_md: str) -> str:
    """Try to extract company name from first H1 heading in context.md."""
    match = re.search(r"^#\s+(?:Firmen-Kontext für\s+)?(.+?)$", context_md, re.MULTILINE)
    if match:
        return match.group(1).strip().rstrip(".")
    return "der Firma"


_HISTORY_BODY_MAX_CHARS = 800


def _truncate_body(body: str, max_chars: int = _HISTORY_BODY_MAX_CHARS) -> str:
    if len(body) <= max_chars:
        return body
    return body[:max_chars] + "\n[... gekürzt ...]"


def _build_history_block(history: list, anonymizer: "pii.Anonymizer | None" = None) -> str:
    """Baut den {conversation_history}-Prompt-Block aus MailMessage-Liste.

    Pitfall 1 (Redact-vor-Truncate): anonymisiert VOR dem Zeichen-Limit-Schnitt.
    Nutzt dieselbe Anonymizer-Instanz wie der Aufrufer (generate_draft_text),
    damit ein Wert, der in aktueller Mail UND History vorkommt, denselben
    Tag traegt.
    """
    if not history:
        return ""
    lines: list[str] = []
    for msg in history:
        from_field = msg.from_ or "?"
        subject_field = msg.subject or "?"
        body = (msg.text or msg.html_to_text() or "").strip()
        if anonymizer is not None:
            # Nicht nur der Body, auch Absender/Betreff historischer Mails
            # sind Mail-Inhalt (nicht context.md) und muessen mit derselben
            # Instanz maskiert werden, sonst leckt z.B. die Absender-E-Mail
            # unmaskiert im Prompt (T-10-01).
            from_field = anonymizer.anonymize(from_field)
            subject_field = anonymizer.anonymize(subject_field)
            body = anonymizer.anonymize(body)
        body_snippet = _truncate_body(body)
        lines.append(
            f"Von: {from_field}\n"
            f"Datum: {msg.date}\n"
            f"Betreff: {subject_field}\n\n"
            f"{body_snippet}"
        )
    return "\n\n---\n\n".join(lines)


def generate_draft_text(
    from_address: str,
    subject: str,
    body: str,
    config: Config,
    logger: Optional[logging.Logger] = None,
    conversation_history: list | None = None,
) -> str:
    """Generate a reply draft text via den konfigurierten LLM-Provider, injecting context.md."""
    logger = logger or logging.getLogger("vizpatch.generate")

    # ANON-03/04/05: Mail-Felder (from/subject/body/history) werden feldweise
    # VOR dem .format() anonymisiert (D-06-Design: Aufrufer-Ebene statt
    # llm.py). context.md/style.md laufen NIE durch den Anonymizer (D-08).
    anonymizer = pii.Anonymizer()
    if config.enable_pii_redaction:
        from_address = anonymizer.anonymize(from_address)
        subject = anonymizer.anonymize(subject)
        body = anonymizer.anonymize(body)
        history_block = _build_history_block(conversation_history or [], anonymizer)
    else:
        history_block = _build_history_block(conversation_history or [], None)

    company_name = _extract_company_name(config.context_md)
    # style.md ist nachrangig zu context.md (Hierarchie in prompts/generate.txt
    # verankert) — bei deaktiviertem Flag oder fehlendem Profil bleibt der
    # Platzhalter leer, NIE "None" (STY-02-Kontrakt: byte-gleich zum heutigen
    # Verhalten wenn kein Profil vorliegt).
    style_block = config.style_md if config.enable_style_adaption else ""
    prompt = config.prompt_generate.format(
        **{
            "company_name": company_name,
            "context_md_full": config.context_md,
            "style_md": style_block,
            "conversation_history": history_block,
            "from": from_address,
            "subject": subject,
            "body": body.strip(),
        }
    )

    draft = llm.llm_call(
        provider=config.llm_provider,
        api_key=config.llm_api_key,
        model=config.model_draft,
        prompt=prompt,
        max_tokens=config.llm_max_tokens_draft,
        temperature=config.llm_temperature_draft,
    )

    if config.enable_pii_redaction:
        draft = anonymizer.deanonymize(draft)
        # D-09 Defense-in-Depth: Nachlauf-Warnung bei uebrig gebliebenen
        # Platzhaltern, kein Abbruch — der menschliche Draft-Review faengt es ab.
        pii.warn_residual_placeholders(draft, logger)

    logger.info(
        "draft_generated",
        extra={
            "from": from_address,
            "subject": subject[:100],
            "draft_length": len(draft),
        },
    )
    return draft.strip()
