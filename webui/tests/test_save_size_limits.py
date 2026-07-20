"""Review IN-04: /save begrenzt context_md/style_md serverseitig auf 64 KB."""
import pytest

HX = {"HX-Request": "true"}


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))
    return tmp_path


def _agent(agents_io):
    agents_io.write_env("info", {"AGENT_ENABLED": "false"})


def test_context_md_over_64kb_rejected(authed_client, cfg):
    import src.agents_io as agents_io

    _agent(agents_io)
    big = "x" * (64 * 1024 + 1)
    r = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers=HX,
        data={"agent_id": "info", "context_md": big, "privacy_consent": "true"},
    )
    assert r.status_code == 200
    assert "64 KB" in r.text or "zu groß" in r.text
    assert agents_io.read_context_md("info") == ""  # nichts geschrieben


def test_style_md_over_64kb_rejected(authed_client, cfg):
    import src.agents_io as agents_io

    _agent(agents_io)
    big = "y" * (64 * 1024 + 1)
    r = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers=HX,
        data={"agent_id": "info", "style_md": big},
    )
    assert r.status_code == 200
    assert "64 KB" in r.text or "zu groß" in r.text
    assert agents_io.read_style_md("info") == ""


def test_style_md_within_limit_saved(authed_client, cfg):
    import src.agents_io as agents_io

    _agent(agents_io)
    ok = "Locker, du-Ansprache."
    r = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers=HX,
        data={"agent_id": "info", "style_md": ok},
    )
    assert r.status_code == 200
    assert agents_io.read_style_md("info") == ok
