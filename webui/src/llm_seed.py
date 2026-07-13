import logging
import os
from pathlib import Path

from anthropic import Anthropic

logger = logging.getLogger(__name__)

MAX_INPUT_LENGTH = 5000


def generate(firma_input: str) -> str:
    prompt_path = Path(os.getenv("WEBUI_SEED_PROMPT", "/app/prompts/context-seed.txt"))
    if len(firma_input) > MAX_INPUT_LENGTH:
        raise ValueError(f"Input too long: {len(firma_input)} > {MAX_INPUT_LENGTH}")
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    template = prompt_path.read_text(encoding="utf-8")
    prompt = template.replace("{firma_input}", firma_input)
    model = os.getenv("MODEL_DRAFT", "claude-sonnet-4-6")
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=2000,
        temperature=0.5,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    logger.info("context_seed_generated", extra={"input_length": len(firma_input), "output_length": len(text), "model": model})
    return text
