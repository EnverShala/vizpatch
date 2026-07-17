"""LLM-Draft-Generation via den LLM-Adapter."""
from __future__ import annotations

import logging
import re
from typing import Optional

from . import llm
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


def _build_history_block(history: list) -> str:
    """Baut den {conversation_history}-Prompt-Block aus MailMessage-Liste."""
    if not history:
        return ""
    lines: list[str] = []
    for msg in history:
        body = msg.text or msg.html_to_text() or ""
        body_snippet = _truncate_body(body.strip())
        lines.append(
            f"Von: {msg.from_ or '?'}\n"
            f"Datum: {msg.date}\n"
            f"Betreff: {msg.subject or '?'}\n\n"
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

    company_name = _extract_company_name(config.context_md)
    history_block = _build_history_block(conversation_history or [])
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

    logger.info(
        "draft_generated",
        extra={
            "from": from_address,
            "subject": subject[:100],
            "draft_length": len(draft),
        },
    )
    return draft.strip()
