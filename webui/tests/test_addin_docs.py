"""Doku-Wächter für das Outlook-Add-in-Betriebs-/Verteilungs-Kapitel (Phase 8, 08-03).

Prüft deterministisch, dass die Betriebs-Doku (README.addin.md,
Caddyfile.example, kunde-env.example, docker-compose.phase4.yml) die
verpflichtenden Inhalte enthält — verhindert stille Doku-Lücken, ohne
subjektive Kriterien zu bewerten (OUT-01/OUT-02/OUT-04).
"""

from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[2]

README_ADDIN = _REPO_ROOT / "deployment" / "README.addin.md"
CADDYFILE_EXAMPLE = _REPO_ROOT / "deployment" / "Caddyfile.example"
KUNDE_ENV_EXAMPLE = _REPO_ROOT / "deployment" / "kunde-env.example"
COMPOSE_PHASE4 = _REPO_ROOT / "deployment" / "docker-compose.phase4.yml"

README_REQUIRED_TERMS = [
    ("reverse_proxy", "reverse-proxy"),  # entweder "reverse_proxy" oder "Reverse-Proxy"
    ("caddy",),
    ("addin_base_url",),
    ("manifest.xml",),
    ("taskpane.html",),
    ("sideloading",),
    ("owa", "outlook im web"),
    ("m365", "admin center"),
    ("frame-ancestors",),
    ("rein lesend", "kein-auto-send"),
]


def _read_lower(path: Path) -> str:
    assert path.exists(), f"Fehlende Datei: {path}"
    return path.read_text(encoding="utf-8").lower()


def test_readme_addin_exists_and_contains_required_terms():
    text = _read_lower(README_ADDIN)
    for variants in README_REQUIRED_TERMS:
        assert any(v in text for v in variants), (
            f"README.addin.md fehlt einer der Begriffe: {variants}"
        )


def test_caddyfile_example_exists_and_contains_reverse_proxy_on_8080():
    text = _read_lower(CADDYFILE_EXAMPLE)
    assert "reverse_proxy" in text
    assert "8080" in text


def test_kunde_env_example_documents_addin_vars():
    text = _read_lower(KUNDE_ENV_EXAMPLE)
    assert "addin_base_url" in text
    assert "addin_frame_ancestors" in text


def test_compose_phase4_is_valid_yaml_and_webui_env_has_addin_base_url():
    assert COMPOSE_PHASE4.exists(), f"Fehlende Datei: {COMPOSE_PHASE4}"
    with COMPOSE_PHASE4.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    webui_env = data["services"]["webui"]["environment"]
    assert "ADDIN_BASE_URL" in webui_env
    assert "ADDIN_FRAME_ANCESTORS" in webui_env
