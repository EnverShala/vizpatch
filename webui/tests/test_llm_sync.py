"""Drift-Guard für den llm.py-Sync-Kontrakt (Phase 6, Plan 06.02).

`agent/src/llm.py` und `webui/src/llm.py` sind BEWUSST zwei identische
Kopien: Deployment sind zwei getrennte Docker-Images, ein Shared-Package ist
eine absichtliche Nicht-Entscheidung (siehe `agent/src/crypto.py` ↔
`webui/src/crypto.py` + `test_crypto_sync.py`, Review WR-06). Die WebUI
braucht den provider-agnostischen `llm_call(...)`-Adapter für die
Schreibstil-Extraktion (D-55): derselbe Anthropic/OpenAI/Google-Dispatch wie
im Agent. Dieser Test schlägt fehl, sobald die Kopien auseinanderlaufen. Im
Docker-Image (nur ein Service im Dateisystem) wird er geskippt — der Guard
greift im Repo-Checkout/CI.

Diese Testdatei existiert ebenfalls identisch in beiden Services.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENT_COPY = _REPO_ROOT / "agent" / "src" / "llm.py"
_WEBUI_COPY = _REPO_ROOT / "webui" / "src" / "llm.py"


def test_llm_module_copies_are_byte_identical():
    if not (_AGENT_COPY.exists() and _WEBUI_COPY.exists()):
        pytest.skip(
            "Schwester-Service nicht im Dateisystem (Docker-Image-Build) — "
            "Sync-Check läuft nur im Repo-Checkout/CI."
        )

    agent_hash = hashlib.sha256(_AGENT_COPY.read_bytes()).hexdigest()
    webui_hash = hashlib.sha256(_WEBUI_COPY.read_bytes()).hexdigest()
    assert agent_hash == webui_hash, (
        "agent/src/llm.py und webui/src/llm.py sind auseinandergelaufen — "
        "der provider-agnostische LLM-Adapter MUSS in beiden Services "
        "identisch bleiben. Änderung bitte in BEIDE Dateien übernehmen."
    )
