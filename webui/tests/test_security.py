from unittest.mock import MagicMock


def _mock_docker_running(mocker):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {"State": {"StartedAt": "2026-07-12T10:00:00Z"}}
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)


def test_context_generate_rate_limited_after_10_calls(authed_client, mocker, tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    _mock_docker_running(mocker)
    import src.agents_io as agents_io
    agents_io.write_env("info", {"LLM_API_KEY": "sk-ant-real-key", "LLM_PROVIDER": "anthropic"})
    mocker.patch("src.llm_seed.generate", return_value="# Seed")
    for _ in range(10):
        r = authed_client.post(
            "/context/generate",
            auth=("admin", "pw"),
            data={"agent_id": "info", "firma_input": "Tanke"},
        )
        assert r.status_code == 200
    blocked = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"agent_id": "info", "firma_input": "Tanke"},
    )
    assert blocked.status_code == 429


def test_login_lockout_after_5_failures(authed_client, mocker):
    _mock_docker_running(mocker)
    for _ in range(5):
        r = authed_client.get("/_auth_check", auth=("admin", "wrong"))
        assert r.status_code == 401
    locked = authed_client.get("/_auth_check", auth=("admin", "pw"))
    assert locked.status_code == 429
    assert "Retry-After" in locked.headers


def test_security_headers_present(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("Referrer-Policy") == "same-origin"
    csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp


def test_login_failures_do_not_lock_on_missing_credentials(authed_client, mocker):
    _mock_docker_running(mocker)
    for _ in range(6):
        r = authed_client.get("/_auth_check")
        assert r.status_code == 401
    ok = authed_client.get("/_auth_check", auth=("admin", "pw"))
    assert ok.status_code == 200


# --- Pfad-abhängige CSP für Add-in-/Embed-Pfade (Phase 8, Plan 08-01, T-08-01/T-08-02) ---


def test_addin_taskpane_relaxed_csp_no_x_frame_options(authed_client, tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    response = authed_client.get("/addin/taskpane.html", auth=("admin", "pw"))
    assert response.status_code == 200
    assert "X-Frame-Options" not in response.headers
    csp = response.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors" in csp
    assert "'self'" in csp
    assert "https://outlook.office.com" in csp
    assert "https://appsforoffice.microsoft.com" in csp


def test_chat_embed_relaxed_csp_no_x_frame_options(authed_client, tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    import src.agents_io as agents_io

    agents_io.write_env("info", {"LLM_API_KEY": "sk-ant-test", "LLM_PROVIDER": "anthropic"})
    response = authed_client.get("/chat/info/embed", auth=("admin", "pw"))
    assert response.status_code == 200
    assert "X-Frame-Options" not in response.headers
    csp = response.headers.get("Content-Security-Policy", "")
    assert "'self'" in csp
    assert "https://outlook.office.com" in csp
    # /chat/*/embed bekommt KEINE office.js-CDN-Freigabe (T-08-03) — nur die Taskpane.
    assert "https://appsforoffice.microsoft.com" not in csp


def test_addin_frame_ancestors_env_override(authed_client, tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    monkeypatch.setenv("ADDIN_FRAME_ANCESTORS", "'self' https://custom.example.com")
    response = authed_client.get("/addin/taskpane.html", auth=("admin", "pw"))
    assert response.status_code == 200
    csp = response.headers.get("Content-Security-Policy", "")
    assert "https://custom.example.com" in csp
    assert "https://outlook.office.com" not in csp


def test_addin_taskpane_without_auth_returns_401(authed_client):
    response = authed_client.get("/addin/taskpane.html")
    assert response.status_code == 401


def test_healthz_strict_policy_unaffected_by_addin_changes(client):
    """Regressionstest (T-08-02): /healthz behält weiterhin die strikte Policy —
    identisch zu test_security_headers_present, hier explizit im Add-in-Kontext
    dokumentiert."""
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.headers.get("X-Frame-Options") == "DENY"
    csp = response.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in csp
