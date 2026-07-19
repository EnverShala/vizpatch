"""Drift-Guard für den pii.py-Sync-Kontrakt (Phase 6, Plan 06.02).

`agent/src/pii.py` und `webui/src/pii.py` sind BEWUSST zwei identische
Kopien: Deployment sind zwei getrennte Docker-Images, ein Shared-Package ist
eine absichtliche Nicht-Entscheidung (siehe `agent/src/crypto.py` ↔
`webui/src/crypto.py` + `test_crypto_sync.py`, Review WR-06). Die WebUI
braucht `redact()` für die Schreibstil-Extraktion (STY-04): jeder gesendete
Mail-Body läuft VOR dem Extraktions-Prompt durch dieselbe Redaction-Logik
wie im Agent. Dieser Test schlägt fehl, sobald die Kopien auseinanderlaufen.
Im Docker-Image (nur ein Service im Dateisystem) wird er geskippt — der
Guard greift im Repo-Checkout/CI.

Diese Testdatei existiert ebenfalls identisch in beiden Services.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENT_COPY = _REPO_ROOT / "agent" / "src" / "pii.py"
_WEBUI_COPY = _REPO_ROOT / "webui" / "src" / "pii.py"


def test_pii_module_copies_are_byte_identical():
    if not (_AGENT_COPY.exists() and _WEBUI_COPY.exists()):
        pytest.skip(
            "Schwester-Service nicht im Dateisystem (Docker-Image-Build) — "
            "Sync-Check läuft nur im Repo-Checkout/CI."
        )

    agent_hash = hashlib.sha256(_AGENT_COPY.read_bytes()).hexdigest()
    webui_hash = hashlib.sha256(_WEBUI_COPY.read_bytes()).hexdigest()
    assert agent_hash == webui_hash, (
        "agent/src/pii.py und webui/src/pii.py sind auseinandergelaufen — "
        "die PII-Redaction-Logik (IBAN/Kreditkarten-Regex) MUSS in beiden "
        "Services identisch bleiben. Änderung bitte in BEIDE Dateien übernehmen."
    )
