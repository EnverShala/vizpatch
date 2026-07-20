"""Review WR-06: keine rohen Exception-Texte nach außen (Info-Leak)."""
import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))


SECRET = "imap.secret-host.internal login denied user=adminX"


def test_mails_suchen_error_is_generic(mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    import src.chat_tools as chat_tools

    agents_io.write_env(
        "info",
        {"IMAP_USER": "a@b.de", "IMAP_PASSWORD": "x", "LLM_API_KEY": "sk-ant", "LLM_PROVIDER": "anthropic"},
    )
    mocker.patch("src.chat_tools.open_agent_mailbox", side_effect=RuntimeError(SECRET))

    result = chat_tools.mails_suchen("info")
    assert result["fehler"] == "IMAP-Verbindung fehlgeschlagen."
    assert "secret-host" not in str(result)
    assert "adminX" not in str(result)


def test_context_generate_error_is_generic(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", {"LLM_API_KEY": "sk-ant-real", "LLM_PROVIDER": "anthropic"})
    mocker.patch("src.crypto.decrypt_value", return_value="sk-ant-real")
    mocker.patch("src.llm_seed.generate", side_effect=RuntimeError(SECRET))

    r = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"agent_id": "info", "firma_input": "Tanke"},
    )
    assert r.status_code == 500
    assert r.json()["detail"] == "LLM-Dienst nicht erreichbar."
    assert "secret-host" not in r.text
    assert "adminX" not in r.text
