def test_healthz_returns_ok(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_healthz_no_auth_required(client):
    response = client.get("/healthz")
    assert "WWW-Authenticate" not in response.headers
