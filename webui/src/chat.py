"""Provider-agnostischer Streaming-Adapter für den Agenten-Chat (Phase 7, CHAT-01/03).

Webui-only Streaming-Sibling zu `llm.py` (siehe 07-01-PLAN.md design_note): `llm.py`
ist ein byte-identischer Drift-Guard-Zwilling von `agent/src/llm.py` (WR-06) und
NICHT-streamend — eine Streaming-Funktion dort würde den Sync-Kontrakt brechen und
agent-seitige Änderungen erzwingen (der Agent chattet nie, out of scope). Dieses
Modul übernimmt dieselbe Provider-Routing-Mechanik + Provider/Key GENAU des
gewählten Agenten (D-59-Intent), aber als eigenständige, webui-only Streaming-Variante
(D-62). `llm.py` bleibt unangetastet.

Für diesen Walking-Skeleton (Plan 07-01) nimmt `stream_chat` einen einzelnen
Single-Turn-`prompt`-String — keine History, kein System-Prompt (kommt in 07-02/07-03).

api_key wird NIE in Log-Statements eingebettet (T-05-08/T-07-02-Muster wie llm.py).
"""
from __future__ import annotations

import logging
from typing import Callable, Iterator

from anthropic import Anthropic

from . import crypto
from .agents_io import read_env_raw
from .style_extract import MODEL_DRAFT_DEFAULTS

logger = logging.getLogger("vizpatch.chat")


class ChatConfigError(RuntimeError):
    """Agent hat keinen nutzbaren LLM-Key konfiguriert (Endpoint-Schicht übersetzt dies zu 400)."""


def resolve_chat_target(agent_id: str) -> tuple[str, str, str]:
    """Liest Provider/Key/Modell GENAU des gewählten Agenten (D-59-Intent).

    `ValueError` propagiert unverändert bei invalidem `agent_id`
    (agents_io._agent_dir-Guard, T-07-01). Fehlender Key -> `ChatConfigError`.
    """
    env = read_env_raw(agent_id)

    raw_key = (env.get("LLM_API_KEY") or "").strip()
    if not raw_key:
        raise ChatConfigError(f"Kein API-Key für Agent {agent_id!r} gespeichert")
    api_key = crypto.decrypt_value(raw_key)

    provider = (env.get("LLM_PROVIDER") or "anthropic").strip().lower()
    model = (env.get("MODEL_DRAFT") or "").strip() or MODEL_DRAFT_DEFAULTS.get(
        provider, MODEL_DRAFT_DEFAULTS["anthropic"]
    )
    return provider, api_key, model


def _stream_anthropic(
    prompt: str, model: str, max_tokens: int, temperature: float, api_key: str
) -> Iterator[str]:
    client = Anthropic(api_key=api_key)
    with client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        for text in stream.text_stream:
            yield text


def _stream_openai(
    prompt: str, model: str, max_tokens: int, temperature: float, api_key: str
) -> Iterator[str]:
    """Call-Shape analog llm.py::_call_openai (WR-01): kein `temperature`-Argument,
    `max_completion_tokens` statt `max_tokens` (GPT-5-/o-Klasse)."""
    from openai import OpenAI  # lazy import

    client = OpenAI(api_key=api_key)
    stream = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=max_tokens,
        stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


def _stream_google(
    prompt: str, model: str, max_tokens: int, temperature: float, api_key: str
) -> Iterator[str]:
    from google import genai  # lazy import
    from google.genai import types  # lazy import

    client = genai.Client(api_key=api_key)
    stream = client.models.generate_content_stream(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
        ),
    )
    for chunk in stream:
        if chunk.text:
            yield chunk.text


_STREAM_DISPATCH: dict[str, Callable[[str, str, int, float, str], Iterator[str]]] = {
    "anthropic": _stream_anthropic,
    "openai": _stream_openai,
    "google": _stream_google,
}


def stream_chat(
    provider: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
) -> Iterator[str]:
    """Streamt einen Single-Turn-Prompt provider-agnostisch (Walking-Skeleton, D-62).

    Unbekannter/leerer Provider fällt auf Anthropic zurück (kein Crash),
    analog `llm.py::llm_call`.
    """
    fn = _STREAM_DISPATCH.get((provider or "").strip().lower(), _stream_anthropic)
    for chunk in fn(prompt, model, max_tokens, temperature, api_key):
        yield chunk
    logger.info("chat_stream_done", extra={"provider": provider, "model": model})
