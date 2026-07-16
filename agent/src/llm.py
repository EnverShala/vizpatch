"""LLM-Adapter: routet einen Single-Prompt-Aufruf zu Anthropic, OpenAI oder Google.

Reiner Dispatcher — keine Prompt-Bau-Logik, keine Fehlerklassen-Übersetzung.
`classify.py`/`generate.py` rufen ausschließlich `llm_call(...)`, nie mehr die
SDKs direkt. OpenAI- und Google-SDKs werden per Lazy-Import innerhalb der
jeweiligen `_call_*`-Funktion geladen, damit ein reiner Anthropic-Kunde keine
ungenutzten Import-Fehler riskiert. api_key wird NIE in Log-Statements
eingebettet (T-05-08).
"""
from __future__ import annotations

import logging
from typing import Callable

from anthropic import Anthropic


logger = logging.getLogger("vizpatch.llm")


def _call_anthropic(prompt: str, model: str, max_tokens: int, temperature: float, api_key: str) -> str:
    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text if response.content else ""


def _call_openai(prompt: str, model: str, max_tokens: int, temperature: float, api_key: str) -> str:
    from openai import OpenAI  # lazy import

    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    return resp.choices[0].message.content or ""


def _call_google(prompt: str, model: str, max_tokens: int, temperature: float, api_key: str) -> str:
    from google import genai  # lazy import
    from google.genai import types  # lazy import

    client = genai.Client(api_key=api_key)
    resp = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    return resp.text or ""


_DISPATCH: dict[str, Callable[[str, str, int, float, str], str]] = {
    "anthropic": _call_anthropic,
    "openai": _call_openai,
    "google": _call_google,
}


def llm_call(
    provider: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    """Routet einen Single-Prompt-Aufruf zum konfigurierten Provider.

    Unbekannter/leerer Provider fällt auf Anthropic zurück (kein Crash),
    analog zum MODEL_DEFAULTS.get(provider, MODEL_DEFAULTS["anthropic"])-Idiom
    in config.py.
    """
    fn = _DISPATCH.get((provider or "").strip().lower(), _call_anthropic)
    text = fn(prompt, model, max_tokens, temperature, api_key)
    logger.info("llm_call_done", extra={"provider": provider, "model": model})
    return text
