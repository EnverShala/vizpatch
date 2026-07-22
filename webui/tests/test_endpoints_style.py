"""Endpoint-Tests fuer /style/relearn + style-Felder im /save (STY-01/03/05).

Analog zu test_endpoints_seed.py: TestClient, Auth-Mock, extract_style()-Mock
statt echter IMAP/LLM-Aufrufe. Deckt zusaetzlich den Esso-Guard ab (D-53/D-54):
migrierte Agenten mit bereits vollstaendigen Credentials duerfen NIE automatisch
lernen, nur der explizite Re-Learn-Button darf das.
"""
import pytest


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    # D-68: config_io (Root-.env) faellt sonst auf den echten Default-Pfad
    # ("/config/.env") zurueck -- seit die Datenschutz-Zustimmung ueber
    # config_io.write_env persistiert wird, muessen auch diese Save-Tests
    # isoliert bleiben (sonst Schreibzugriff auf den echten Host-Pfad).
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))


def _complete_creds() -> dict:
    return {
        "IMAP_USER": "info@example.com",
        "IMAP_PASSWORD": "secret-pw",
        "LLM_API_KEY": "sk-ant-real-key",
        "LLM_PROVIDER": "anthropic",
    }


# --- /style/relearn ---------------------------------------------------------


def test_style_relearn_requires_auth(pw_set_client, tmp_path, monkeypatch):
    """260722-jrq: POST /style/relearn ist kein Add-in-Pfad -> ohne gueltige
    Session (aber gesetztem Passwort) -> 401."""
    _setup_env(tmp_path, monkeypatch)
    response = pw_set_client.post("/style/relearn", data={"agent_id": "info", "style_note": ""})
    assert response.status_code == 401


def test_style_relearn_success_writes_style_md(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", _complete_creds())
    mocker.patch("src.style_extract.extract_style", return_value="## Anrede\nDu…")
    response = authed_client.post(
        "/style/relearn",
        auth=("admin", "pw"),
        data={"agent_id": "info", "style_note": ""},
    )
    assert response.status_code == 200
    assert "Anrede" in response.text
    assert agents_io.read_style_md("info") == "## Anrede\nDu…"


def test_style_relearn_empty_returns_400_with_sty05_hint(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    import src.style_extract as style_extract

    agents_io.write_env("info", _complete_creds())
    mocker.patch(
        "src.style_extract.extract_style",
        side_effect=style_extract.StyleExtractionEmpty("zu wenig verwertbares Material"),
    )
    response = authed_client.post(
        "/style/relearn",
        auth=("admin", "pw"),
        data={"agent_id": "info", "style_note": ""},
    )
    assert response.status_code == 400
    assert "wenig" in response.text.lower()


def test_style_relearn_llm_runtime_error_returns_500(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", _complete_creds())
    mocker.patch("src.style_extract.extract_style", side_effect=RuntimeError("Kein API-Key"))
    response = authed_client.post(
        "/style/relearn",
        auth=("admin", "pw"),
        data={"agent_id": "info", "style_note": ""},
    )
    assert response.status_code == 500


def test_style_relearn_invalid_agent_id_returns_400(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.post(
        "/style/relearn",
        auth=("admin", "pw"),
        data={"agent_id": "../evil", "style_note": ""},
    )
    assert response.status_code == 400


def test_style_relearn_persists_style_note_before_extraction(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", _complete_creds())
    mocker.patch("src.style_extract.extract_style", return_value="## Anrede\nDu…")
    response = authed_client.post(
        "/style/relearn",
        auth=("admin", "pw"),
        data={"agent_id": "info", "style_note": "Ich schreibe locker und modern."},
    )
    assert response.status_code == 200
    assert agents_io.read_style_note("info") == "Ich schreibe locker und modern."


def test_style_relearn_persists_style_note_even_when_extraction_fails(authed_client, mocker, tmp_path, monkeypatch):
    """style_note ueberlebt auch einen fehlschlagenden Re-Learn-Versuch."""
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    import src.style_extract as style_extract

    agents_io.write_env("info", _complete_creds())
    mocker.patch(
        "src.style_extract.extract_style",
        side_effect=style_extract.StyleExtractionEmpty("zu wenig"),
    )
    response = authed_client.post(
        "/style/relearn",
        auth=("admin", "pw"),
        data={"agent_id": "info", "style_note": "Immer freundlich und kurz."},
    )
    assert response.status_code == 400
    assert agents_io.read_style_note("info") == "Immer freundlich und kurz."


# --- /save — style_md / style_note / enable_style_adaption ------------------


def test_save_style_md_writes_atomic(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", _complete_creds())
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={"agent_id": "info", "style_md": "## Anrede\nSie"},
    )
    assert response.status_code == 200
    assert "save-ok" in response.text
    assert agents_io.read_style_md("info") == "## Anrede\nSie"


def test_save_enable_style_adaption_flag(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", _complete_creds())
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={"agent_id": "info", "enable_style_adaption": "false"},
    )
    assert response.status_code in (200, 303)
    env = agents_io.read_env_raw("info")
    assert env.get("ENABLE_STYLE_ADAPTION") == "false"


def test_save_style_without_agent_id_returns_error(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={"agent_id": "", "style_md": "## Anrede\nSie"},
    )
    assert response.status_code == 200
    assert "save-err" in response.text


# --- Auto-Trigger bei Neuanlage-Transition (STY-01) --------------------------


def test_save_auto_triggers_extraction_on_creds_transition(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    # Neuanlage: kein IMAP_USER/IMAP_PASSWORD/LLM_API_KEY vor diesem Request.
    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
    mock_extract = mocker.patch("src.style_extract.extract_style", return_value="## Anrede\nDu…")
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={
            "agent_id": "info",
            "imap_user": "info@example.com",
            "imap_password": "secret-pw",
            "llm_api_key": "sk-ant-real-key",
            "privacy_consent": "on",
        },
    )
    assert response.status_code in (200, 303)
    mock_extract.assert_called_once_with("info")
    assert agents_io.read_style_md("info") == "## Anrede\nDu…"


def test_save_auto_trigger_graceful_on_extraction_failure(authed_client, mocker, tmp_path, monkeypatch):
    """T-06-07: fehlgeschlagene Auto-Extraktion darf den Save nicht blockieren (graceful)."""
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
    mocker.patch("src.style_extract.extract_style", side_effect=RuntimeError("boom"))
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={
            "agent_id": "info",
            "imap_user": "info@example.com",
            "imap_password": "secret-pw",
            "llm_api_key": "sk-ant-real-key",
            "privacy_consent": "on",
        },
    )
    assert response.status_code in (200, 303)
    assert agents_io.read_style_md("info") == ""


def test_save_auto_trigger_skipped_when_disabled_via_flag(authed_client, mocker, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", {"AGENT_ENABLED": "false", "ENABLE_STYLE_ADAPTION": "false"})
    mock_extract = mocker.patch("src.style_extract.extract_style")
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={
            "agent_id": "info",
            "imap_user": "info@example.com",
            "imap_password": "secret-pw",
            "llm_api_key": "sk-ant-real-key",
            "privacy_consent": "on",
        },
    )
    assert response.status_code in (200, 303)
    mock_extract.assert_not_called()


# --- Esso-Guard (D-53/D-54/SC5) ---------------------------------------------


def test_save_migrated_agent_context_save_never_auto_triggers(authed_client, mocker, tmp_path, monkeypatch):
    """Esso-Guard 1 (KRITISCH): Creds sind VOR diesem Request bereits vollstaendig
    -> Speichern eines anderen Fieldsets (context.md) darf extract_style NIE aufrufen."""
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", _complete_creds())
    mock_extract = mocker.patch("src.style_extract.extract_style")
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={"agent_id": "info", "context_md": "# Firma\nNeuer Inhalt", "privacy_consent": "on"},
    )
    assert response.status_code in (200, 303)
    mock_extract.assert_not_called()
    assert agents_io.read_style_md("info") == ""


def test_save_migrated_agent_password_rotation_never_auto_triggers(authed_client, mocker, tmp_path, monkeypatch):
    """Esso-Guard 1, Variante Passwort-Rotation: Creds waren schon vorher komplett."""
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", _complete_creds())
    mock_extract = mocker.patch("src.style_extract.extract_style")
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={"agent_id": "info", "imap_password": "neues-passwort-rotiert", "privacy_consent": "on"},
    )
    assert response.status_code in (200, 303)
    mock_extract.assert_not_called()


def test_save_auto_trigger_skipped_when_style_md_already_exists(authed_client, mocker, tmp_path, monkeypatch):
    """Esso-Guard 2: Cred-Transition passiert, aber style.md existiert schon -> kein Trigger."""
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io

    agents_io.write_env("info", {"AGENT_ENABLED": "false"})
    agents_io.write_style_md_atomic("info", "## Bereits vorhanden")
    mock_extract = mocker.patch("src.style_extract.extract_style")
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        data={
            "agent_id": "info",
            "imap_user": "info@example.com",
            "imap_password": "secret-pw",
            "llm_api_key": "sk-ant-real-key",
            "privacy_consent": "on",
        },
    )
    assert response.status_code in (200, 303)
    mock_extract.assert_not_called()
    assert agents_io.read_style_md("info") == "## Bereits vorhanden"
