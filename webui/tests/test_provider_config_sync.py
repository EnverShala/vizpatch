"""Drift-Guard für den provider_config.py-Sync-Kontrakt (Phase 6, Plan 06.02).

`agent/src/provider_config.py` und `webui/src/provider_config.py` sind
BEWUSST zwei identische Kopien: Deployment sind zwei getrennte Docker-Images,
ein Shared-Package ist eine absichtliche Nicht-Entscheidung (siehe
`agent/src/crypto.py` ↔ `webui/src/crypto.py` + `test_crypto_sync.py`, Review
WR-06). Die WebUI braucht `resolve_imap_config(email)` als Fallback für die
Sent-Ordner-Erkennung bei der Schreibstil-Extraktion (D-53/T-06-04-Nachbar).
Nachträglich duplizierte Abhängigkeit von `style_extract.py` (Rule-3-Fix,
06.02-SUMMARY.md — im Plan nicht explizit als Duplikat benannt, aber vom
selben etablierten Muster gefordert). Dieser Test schlägt fehl, sobald die
Kopien auseinanderlaufen. Im Docker-Image (nur ein Service im Dateisystem)
wird er geskippt — der Guard greift im Repo-Checkout/CI.

Diese Testdatei existiert ebenfalls identisch in beiden Services.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENT_COPY = _REPO_ROOT / "agent" / "src" / "provider_config.py"
_WEBUI_COPY = _REPO_ROOT / "webui" / "src" / "provider_config.py"


def test_provider_config_module_copies_are_byte_identical():
    if not (_AGENT_COPY.exists() and _WEBUI_COPY.exists()):
        pytest.skip(
            "Schwester-Service nicht im Dateisystem (Docker-Image-Build) — "
            "Sync-Check läuft nur im Repo-Checkout/CI."
        )

    agent_hash = hashlib.sha256(_AGENT_COPY.read_bytes()).hexdigest()
    webui_hash = hashlib.sha256(_WEBUI_COPY.read_bytes()).hexdigest()
    assert agent_hash == webui_hash, (
        "agent/src/provider_config.py und webui/src/provider_config.py sind "
        "auseinandergelaufen — die IMAP-Provider-Tabelle MUSS in beiden "
        "Services identisch bleiben. Änderung bitte in BEIDE Dateien übernehmen."
    )
