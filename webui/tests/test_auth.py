def test_healthz_still_open(client):
    response = client.get("/healthz")
    assert response.status_code == 200

def test_missing_auth_returns_401(authed_client):
    response = authed_client.get("/_auth_check")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers

def test_correct_auth_returns_200(authed_client):
    response = authed_client.get("/_auth_check", auth=("admin", "pw"))
    assert response.status_code == 200
    assert response.json() == {"ok": True}

def test_wrong_password_returns_401(authed_client):
    response = authed_client.get("/_auth_check", auth=("admin", "wrong"))
    assert response.status_code == 401
