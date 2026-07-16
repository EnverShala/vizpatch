"""Provider-Autodetect aus dem API-Key-Prefix (D-51, LLM-01).

Reine Funktion ohne Seiteneffekte — läuft auf dem Klartext-Key VOR der
Fernet-Verschlüsselung (D-51: "Die Erkennung läuft auf dem Klartext-Key VOR
der Fernet-Verschlüsselung.").
"""
from __future__ import annotations


def detect_llm_provider(api_key: str) -> str | None:
    """sk-ant- -> anthropic; AIza -> google; sonst sk- -> openai; kein Treffer -> None."""
    key = (api_key or "").strip()
    if not key:
        return None
    if key.startswith("sk-ant-"):
        return "anthropic"
    if key.startswith("AIza"):
        return "google"
    if key.startswith("sk-"):
        return "openai"
    return None
