---
plan_id: 03-llm
title: LLM-Klassifikation und Draft-Generierung
wave: 2
depends_on: [01-skeleton]
requirements:
  - AGT-03
  - AGT-04
files_modified:
  - agent/src/classify.py
  - agent/src/generate.py
autonomous: true
---

# Plan 03: LLM-Klassifikation und Draft-Generierung

**Ziel:** Zwei Module, jedes mit einer Funktion die einen Anthropic-Call macht:
- `classify.run(msg, prompt_template, api_key, model) -> "REPLY_NEEDED" | "IGNORE"`
- `generate.run(msg, context_md, prompt_template, api_key, model, max_tokens, temperature) -> str`

**Parallel zu Plan 02** — beide hängen nur an Plan 01.

## Verifikation

- `python -c "from src.classify import classify_email"` läuft ohne ImportError
- `python -c "from src.generate import generate_draft_text"` läuft ohne ImportError
- Beide Funktionen können unittest-mäßig mit Mock-Anthropic-Client aufgerufen werden

---

<task id="3.1" type="execute">
<action>
`agent/src/classify.py` schreiben — synchroner Anthropic-Call für Ja/Nein-Klassifikation. Body auf 2000 Zeichen begrenzen bevor an LLM.

```python
"""LLM-Klassifikation: REPLY_NEEDED vs. IGNORE via Anthropic Haiku."""
from __future__ import annotations

import logging
from typing import Literal, Optional

from anthropic import Anthropic

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
    client: Optional[Anthropic] = None,
    logger: Optional[logging.Logger] = None,
) -> Classification:
    """Classify an email as REPLY_NEEDED or IGNORE using Anthropic Haiku."""
    logger = logger or logging.getLogger("kea.classify")
    client = client or Anthropic(api_key=config.anthropic_api_key)

    body_snippet = _extract_body_snippet(body)
    prompt = config.prompt_classify.format(
        **{"from": from_address, "subject": subject, "body_snippet": body_snippet}
    )

    response = client.messages.create(
        model=config.model_classify,
        max_tokens=20,
        temperature=0.0,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text if response.content else ""
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
```
</action>
<read_first>
- `agent/src/config.py`
- `agent/prompts/classify.txt`
- https://docs.claude.com/en/api/messages (Anthropic Messages API)
</read_first>
<acceptance_criteria>
- `agent/src/classify.py` existiert
- Exportiert `classify_email(from_address, subject, body, config, client=None, logger=None) -> "REPLY_NEEDED" | "IGNORE"`
- Body-Snippet auf 2000 Zeichen truncated
- Bei unklarem LLM-Response returns "IGNORE" als Sicherheits-Default
- `max_tokens=20`, `temperature=0.0` gesetzt für deterministische Klassifikation
- Logging-Event `classified` mit Extra-Fields
- Injectable Client-Parameter für Tests (Dependency Injection)
</acceptance_criteria>
</task>

<task id="3.2" type="execute">
<action>
`agent/src/generate.py` schreiben — Draft-Text-Generierung mit Sonnet, injiziert `context.md`.

```python
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


def generate_draft_text(
    from_address: str,
    subject: str,
    body: str,
    config: Config,
    client: Optional[Anthropic] = None,
    logger: Optional[logging.Logger] = None,
) -> str:
    """Generate a reply draft text using Anthropic Sonnet, injecting context.md."""
    logger = logger or logging.getLogger("kea.generate")
    client = client or Anthropic(api_key=config.anthropic_api_key)

    company_name = _extract_company_name(config.context_md)
    prompt = config.prompt_generate.format(
        **{
            "company_name": company_name,
            "context_md_full": config.context_md,
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
```
</action>
<read_first>
- `agent/src/config.py`
- `agent/prompts/generate.txt`
- `agent/context.md.example`
- https://docs.claude.com/en/api/messages
</read_first>
<acceptance_criteria>
- `agent/src/generate.py` existiert
- Exportiert `generate_draft_text(from_address, subject, body, config, client=None, logger=None) -> str`
- Extrahiert Firmenname aus erstem H1-Heading in `context.md`
- Injektiert `context.md`-Vollinhalt in Prompt via `{context_md_full}`-Placeholder
- Verwendet `config.model_draft` (default `claude-sonnet-4-6`)
- Verwendet `config.llm_max_tokens_draft` und `config.llm_temperature_draft`
- Logging-Event `draft_generated` mit `draft_length`
- Injectable Client-Parameter für Tests
</acceptance_criteria>
</task>

## must_haves

- `classify_email(...)` liefert `"REPLY_NEEDED"` oder `"IGNORE"`, robust bei unklarem LLM-Response
- `generate_draft_text(...)` liefert einen Klartext-String, `context.md` ist im Prompt enthalten
- Beide Module akzeptieren einen `client`-Parameter für Testbarkeit (Mock-Injection)
