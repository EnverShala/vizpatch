import pytest
from fastapi.testclient import TestClient


# Review CR-01: die Same-Origin-Middleware lehnt state-aendernde Requests ohne
# passenden Origin/Referer ab. Ein echter Browser sendet bei Form-POSTs immer
# Origin; der TestClient tut das nicht von allein. Deshalb bekommen die Fixtures
# einen Default-Origin passend zur TestClient-Host (`testserver`) — genau wie ein
# same-origin-Browser. Tests, die Cross-Origin/CSRF pruefen, ueberschreiben Origin
# bzw. Referer pro Request explizit.
TEST_ORIGIN = "http://testserver"


@pytest.fixture
def client():
    from src.main import app
    with TestClient(app, headers={"Origin": TEST_ORIGIN}) as c:
        yield c


@pytest.fixture
def authed_client(monkeypatch):
    monkeypatch.setenv("WEBUI_USER", "admin")
    monkeypatch.setenv("WEBUI_PASSWORD", "pw")
    from src.main import app
    with TestClient(app, headers={"Origin": TEST_ORIGIN}) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_docker_client_cache():
    import src.docker_ctrl as docker_ctrl
    docker_ctrl._client = None
    yield
    docker_ctrl._client = None


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    from src.main import limiter
    from src import auth
    limiter.reset()
    auth._reset_login_tracking()
    yield
    limiter.reset()
    auth._reset_login_tracking()


@pytest.fixture(autouse=True)
def reset_chat_tools_session_authorization():
    """Session-Autorisierung für die Papierkorb-Werkzeuge (`chat_tools.
    _authorized_move_sessions`) ist ein reiner In-Memory-Prozess-Zustand — ohne
    Reset könnten sich Tests über den module-level `set` hinweg beeinflussen,
    auch wenn unterschiedliche VIZPATCH_SECRET_KEY_FILE-Werte je Test das in der
    Praxis bereits verhindern (andere HMAC-Digests). Explizit + robust."""
    import src.chat_tools as chat_tools
    chat_tools._authorized_move_sessions.clear()
    yield
    chat_tools._authorized_move_sessions.clear()
