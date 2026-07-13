"""LLM-Draft-Generation via Anthropic Sonnet."""
from __future__ import annotations

import logging
import re
from typing import Optional

from anthropic import Anthropic

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
    client: Optional[Anthropic] = None,
    logger: Optional[logging.Logger] = None,
    conversation_history: list | None = None,
) -> str:
    """Generate a reply draft text using Anthropic Sonnet, injecting context.md."""
    logger = logger or logging.getLogger("vizpatch.generate")
    client = client or Anthropic(api_key=config.anthropic_api_key)

    company_name = _extract_company_name(config.context_md)
    history_block = _build_history_block(conversation_history or [])
    prompt = config.prompt_generate.format(
        **{
            "company_name": company_name,
            "context_md_full": config.context_md,
            "conversation_history": history_block,
            "from": from_address,
            "subject": subject,
            "body": body.strip(),
        }
    )

    response = client.messages.create(
        model=config.model_draft,
        max_tokens=config.llm_max_tokens_draft,
        temperature=config.llm_temperature_draft,
        messages=[{"role": "user", "content": prompt}],
    )
    draft = response.content[0].text if response.content else ""

    logger.info(
        "draft_generated",
        extra={
            "from": from_address,
            "subject": subject[:100],
            "draft_length": len(draft),
        },
    )
    return draft.strip()
