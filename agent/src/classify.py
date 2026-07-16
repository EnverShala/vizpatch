"""LLM-Klassifikation: REPLY_NEEDED vs. IGNORE via den LLM-Adapter."""
from __future__ import annotations

import logging
from typing import Literal, Optional

from . import llm
from .config import Config


Classification = Literal["REPLY_NEEDED", "IGNORE"]

MAX_BODY_CHARS = 2000


def _extract_body_snippet(body: str) -> str:
    if not body:
        return ""
    body = body.replace("\r\n", "\n").strip()
    if len(body) > MAX_BODY_CHARS:
        return body[:MAX_BODY_CHARS] + "\n[... truncated ...]"
    return body


def _parse_response(text: str) -> Classification:
    """Extract REPLY_NEEDED or IGNORE from LLM response (be lenient about whitespace/case)."""
    upper = text.strip().upper()
    if "REPLY_NEEDED" in upper:
        return "REPLY_NEEDED"
    if "IGNORE" in upper:
        return "IGNORE"
    # Fallback: unentschieden → sicherheitshalber IGNORE (kein Draft besser als falscher Draft)
    return "IGNORE"


def classify_email(
    from_address: str,
    subject: str,
    body: str,
    config: Config,
    logger: Optional[logging.Logger] = None,
) -> Classification:
    """Classify an email as REPLY_NEEDED or IGNORE using den konfigurierten LLM-Provider."""
    logger = logger or logging.getLogger("vizpatch.classify")

    body_snippet = _extract_body_snippet(body)
    prompt = config.prompt_classify.format(
        **{"from": from_address, "subject": subject, "body_snippet": body_snippet}
    )

    text = llm.llm_call(
        provider=config.llm_provider,
        api_key=config.llm_api_key,
        model=config.model_classify,
        prompt=prompt,
        max_tokens=20,
        temperature=0.0,
    )
    classification = _parse_response(text)

    logger.info(
        "classified",
        extra={
            "from": from_address,
            "subject": subject[:100],
            "classification": classification,
            "raw_response": text[:50],
        },
    )
    return classification
