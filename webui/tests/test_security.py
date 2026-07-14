from unittest.mock import MagicMock


def _mock_docker_running(mocker):
    mock_container = MagicMock()
    mock_container.status = "running"
    mock_container.attrs = {"State": {"StartedAt": "2026-07-12T10:00:00Z"}}
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container
    mocker.patch("docker.from_env", return_value=mock_client)


def test_context_generate_rate_limited_after_10_calls(authed_client, mocker):
    _mock_docker_running(mocker)
    mocker.patch("src.llm_seed.generate", return_value="# Seed")
    for _ in range(10):
        r = authed_client.post(
            "/context/generate",
            auth=("admin", "pw"),
            data={"firma_input": "Tanke"},
        )
        assert r.status_code == 200
    blocked = authed_client.post(
        "/context/generate",
        auth=("admin", "pw"),
        data={"firma_input": "Tanke"},
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
