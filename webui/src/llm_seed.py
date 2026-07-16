import logging
import os
from pathlib import Path

from anthropic import Anthropic

logger = logging.getLogger(__name__)

MAX_INPUT_LENGTH = 5000


def generate(firma_input: str, api_key: str, model: str | None = None) -> str:
    """Context-KI-Assistent (Sonnet). Key-Quelle ist der Aufrufer (main.py:
    entschlüsselter LLM_API_KEY des aktiven Agenten, Anthropic-only — Pitfall 6).
    """
    prompt_path = Path(os.getenv("WEBUI_SEED_PROMPT", "/app/prompts/context-seed.txt"))
    if len(firma_input) > MAX_INPUT_LENGTH:
        raise ValueError(f"Input too long: {len(firma_input)} > {MAX_INPUT_LENGTH}")
    if not api_key:
        raise RuntimeError("Kein API-Key übergeben")
    template = prompt_path.read_text(encoding="utf-8")
    prompt = template.replace("{firma_input}", firma_input)
    resolved_model = model or os.getenv("MODEL_DRAFT") or "claude-sonnet-4-6"
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model=resolved_model,
        max_tokens=2000,
        temperature=0.5,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    logger.info(
        "context_seed_generated",
        extra={"input_length": len(firma_input), "output_length": len(text), "model": resolved_model},
    )
    return text
