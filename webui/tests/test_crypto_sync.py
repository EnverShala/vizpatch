"""Drift-Guard für den crypto.py-Sync-Kontrakt (Review WR-06).

`agent/src/crypto.py` und `webui/src/crypto.py` sind BEWUSST zwei identische
Kopien: Deployment sind zwei getrennte Docker-Images, ein Shared-Package ist
eine absichtliche Nicht-Entscheidung. Der Fernet-Kontrakt (enc:-Prefix,
Key-Pfad /config/.secret_key, InvalidToken→RuntimeError) ist cross-service:
die WebUI verschlüsselt, der Agent entschlüsselt. Dieser Test schlägt fehl,
sobald die Kopien auseinanderlaufen. Im Docker-Image (nur ein Service im
Dateisystem) wird er geskippt — der Guard greift im Repo-Checkout/CI.

Diese Testdatei existiert ebenfalls identisch in beiden Services.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENT_COPY = _REPO_ROOT / "agent" / "src" / "crypto.py"
_WEBUI_COPY = _REPO_ROOT / "webui" / "src" / "crypto.py"


def test_crypto_module_copies_are_byte_identical():
    if not (_AGENT_COPY.exists() and _WEBUI_COPY.exists()):
        pytest.skip(
            "Schwester-Service nicht im Dateisystem (Docker-Image-Build) — "
            "Sync-Check läuft nur im Repo-Checkout/CI."
        )

    agent_hash = hashlib.sha256(_AGENT_COPY.read_bytes()).hexdigest()
    webui_hash = hashlib.sha256(_WEBUI_COPY.read_bytes()).hexdigest()
    assert agent_hash == webui_hash, (
        "agent/src/crypto.py und webui/src/crypto.py sind auseinandergelaufen — "
        "der Fernet-Kontrakt (enc:-Prefix, Key-Pfad, Fehlerübersetzung) MUSS in "
        "beiden Services identisch bleiben. Änderung bitte in BEIDE Dateien übernehmen."
    )
