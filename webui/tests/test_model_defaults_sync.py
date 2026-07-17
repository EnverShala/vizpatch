"""Drift-Guard: webui/src/style_extract.py::MODEL_DRAFT_DEFAULTS MUSS mit der
Draft-Spalte von agent/src/config.py::MODEL_DEFAULTS übereinstimmen (D-55).

Kein Import von agent/src/config.py (agent-only, relative Imports/Deps die die
WebUI nicht hat) — stattdessen AST-Parse der Datei, analog zum
crypto/pii/llm-Byte-Sync-Muster, nur auf Werte statt Bytes. Skippt, wenn
agent/src/config.py nicht im Dateisystem liegt (Docker-Image-Build, nur ein
Service im Container).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENT_CONFIG = _REPO_ROOT / "agent" / "src" / "config.py"


def _load_agent_model_defaults() -> dict:
    source = _AGENT_CONFIG.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "MODEL_DEFAULTS":
            return ast.literal_eval(node.value)
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if getattr(target, "id", None) == "MODEL_DEFAULTS":
                    return ast.literal_eval(node.value)
    raise AssertionError("MODEL_DEFAULTS nicht in agent/src/config.py gefunden")


def test_model_draft_defaults_match_agent_config():
    if not _AGENT_CONFIG.exists():
        pytest.skip(
            "agent/src/config.py nicht im Dateisystem (Docker-Image-Build) — "
            "Sync-Check läuft nur im Repo-Checkout/CI."
        )
    import src.style_extract as style_extract

    agent_model_defaults = _load_agent_model_defaults()
    for provider, defaults in agent_model_defaults.items():
        webui_draft = style_extract.MODEL_DRAFT_DEFAULTS.get(provider)
        assert webui_draft == defaults["draft"], (
            f"Draft-Modell für Provider '{provider}' ist in "
            f"webui/src/style_extract.py ({webui_draft!r}) und "
            f"agent/src/config.py ({defaults['draft']!r}) unterschiedlich. "
            "MODEL_DRAFT_DEFAULTS bitte synchron halten (D-55)."
        )
