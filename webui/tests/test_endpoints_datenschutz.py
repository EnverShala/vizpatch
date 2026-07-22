"""Tests fuer die Datenschutz-Zustimmung (D-68): GET /datenschutz, die
Pflicht-Checkbox in index.html und die serverseitige Durchsetzung in /save.

Analog zu test_endpoints_config.py / test_endpoints_style.py: TestClient,
Auth-Mock, temp-Config-Fixtures statt der echten /config.
"""
from unittest.mock import MagicMock


def _setup_env(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("WEBUI_ENV_PATH", str(tmp_path / "root.env"))


def _mock_docker_running(mocker):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {"State": {"StartedAt": "2026-07-12T10:00:00Z"}}
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)
    return mock_client


# --- GET /datenschutz --------------------------------------------------------


def test_datenschutz_requires_auth(pw_set_client, tmp_path, monkeypatch):
    """260722-jrq: voller GET ohne gueltige Session -> 303 auf /login."""
    _setup_env(tmp_path, monkeypatch)
    response = pw_set_client.get("/datenschutz", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_datenschutz_page_contains_core_dsgvo_sections(authed_client, tmp_path, monkeypatch):
    _setup_env(tmp_path, monkeypatch)
    response = authed_client.get("/datenschutz", auth=("admin", "pw"))
    assert response.status_code == 200
    html = response.text
    assert "Verantwortlicher" in html
    assert "KI-Diensten" in html
    assert "Ihre Rechte" in html


# --- index.html: Pflicht-Checkbox -------------------------------------------


def test_agent_edit_partial_has_required_privacy_consent_checkbox(authed_client, tmp_path, monkeypatch):
    """UMBAU (Task 2): die Datenschutz-Checkbox lebt nicht mehr auf `/`, sondern
    im per-Agent-Popup-Partial (GET /agents/{id}/edit)."""
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"IMAP_USER": "test@x.de"})
    response = authed_client.get("/agents/info/edit", auth=("admin", "pw"))
    assert response.status_code == 200
    html = response.text
    assert 'name="privacy_consent"' in html
    assert "Datenschutzbestimmungen" in html
    # required-Attribut fuer die clientseitige Blockade
    checkbox_start = html.index('name="privacy_consent"')
    surrounding = html[max(0, checkbox_start - 200):checkbox_start + 50]
    assert "required" in surrounding


def test_agent_edit_partial_shows_consent_timestamp_and_prechecked_when_already_accepted(
    authed_client, tmp_path, monkeypatch
):
    _setup_env(tmp_path, monkeypatch)
    import src.agents_io as agents_io
    import src.config_io as config_io
    agents_io.write_env("info", {"IMAP_USER": "test@x.de"})
    config_io.write_env({
        "PRIVACY_CONSENT_ACCEPTED": "true",
        "PRIVACY_CONSENT_AT": "2026-07-17T10:00:00+00:00",
        "PRIVACY_CONSENT_VERSION": "2026-07-17",
    })
    response = authed_client.get("/agents/info/edit", auth=("admin", "pw"))
    html = response.text
    assert "Zugestimmt am 2026-07-17T10:00:00+00:00" in html
    checkbox_start = html.index('name="privacy_consent"')
    surrounding = html[checkbox_start:checkbox_start + 200]
    assert "checked" in surrounding


# --- POST /save: serverseitige Durchsetzung ---------------------------------


def test_save_agent_fields_without_consent_and_not_persisted_fails(
    authed_client, mocker, tmp_path, monkeypatch
):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {})
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={"agent_id": "info", "imap_user": "u@x.de", "imap_password": "secret-pw"},
    )
    assert response.status_code == 200
    assert "save-err" in response.text
    assert "Datenschutzbestimmungen" in response.text
    raw = agents_io.read_env_raw("info")
    assert raw.get("IMAP_USER") != "u@x.de"


def test_save_agent_fields_with_consent_persists_and_saves(
    authed_client, mocker, tmp_path, monkeypatch
):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    import src.config_io as config_io
    agents_io.write_env("info", {"LLM_PROVIDER": "anthropic"})
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={
            "agent_id": "info",
            "imap_user": "u@x.de",
            "imap_password": "secret-pw",
            "privacy_consent": "on",
        },
    )
    assert response.status_code == 200
    assert "save-ok" in response.text
    raw = agents_io.read_env_raw("info")
    assert raw["IMAP_USER"] == "u@x.de"
    root_env = config_io.read_env_raw()
    assert root_env["PRIVACY_CONSENT_ACCEPTED"] == "true"
    assert root_env["PRIVACY_CONSENT_AT"]
    assert root_env["PRIVACY_CONSENT_VERSION"] == "2026-07-17"


def test_save_agent_fields_with_already_persisted_consent_does_not_need_checkbox_again(
    authed_client, mocker, tmp_path, monkeypatch
):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    import src.config_io as config_io
    agents_io.write_env("info", {"LLM_PROVIDER": "anthropic"})
    config_io.write_env({
        "PRIVACY_CONSENT_ACCEPTED": "true",
        "PRIVACY_CONSENT_AT": "2026-07-01T09:00:00+00:00",
        "PRIVACY_CONSENT_VERSION": "2026-07-17",
    })
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={"agent_id": "info", "imap_user": "u@x.de", "imap_password": "secret-pw"},
    )
    assert response.status_code == 200
    assert "save-ok" in response.text
    raw = agents_io.read_env_raw("info")
    assert raw["IMAP_USER"] == "u@x.de"
    # Zeitstempel bleibt unverändert -- keine erneute Zustimmung nötig
    root_env = config_io.read_env_raw()
    assert root_env["PRIVACY_CONSENT_AT"] == "2026-07-01T09:00:00+00:00"


def test_save_non_agent_section_not_blocked_by_missing_consent(
    authed_client, mocker, tmp_path, monkeypatch
):
    _setup_env(tmp_path, monkeypatch)
    _mock_docker_running(mocker)
    response = authed_client.post(
        "/save",
        auth=("admin", "pw"),
        headers={"HX-Request": "true"},
        data={"agent_id": "", "autostart_enabled": "true"},
    )
    assert response.status_code == 200
    assert "save-ok" in response.text
