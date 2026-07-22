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
    """Session-Login (260722-jrq): WEBUI_PASSWORD wird bcrypt-gehasht gesetzt,
    danach stellt EIN POST /login eine echte Session her — der TestClient
    persistiert den `vizpatch_session`-Cookie ueber alle Folgerequests dieser
    Instanz hinweg (kein Basic-Auth mehr, WEBUI_USER entfaellt). Ein zusaetzlich
    mitgeschickter `auth=(...)`-Basic-Header in Bestandstests wird schlicht
    ignoriert."""
    from src import auth
    monkeypatch.setenv("WEBUI_PASSWORD", auth.hash_password("pw"))
    from src.main import app
    with TestClient(app, headers={"Origin": TEST_ORIGIN}) as c:
        r = c.post("/login", data={"password": "pw"}, follow_redirects=False)
        assert r.status_code == 303
        yield c


@pytest.fixture
def pw_set_client(monkeypatch):
    """WEBUI_PASSWORD ist gesetzt, aber es existiert KEINE Session (kein
    POST /login) — fuer Tests, die pruefen, dass gesicherte Routen ohne
    gueltige Session abgewiesen werden (401 bei POST, 303 bei vollem GET),
    waehrend das Passwort bereits konfiguriert ist (sonst wuerde der
    Setup-Zwang auf /setup umleiten, statt die Session-Durchsetzung zu
    pruefen)."""
    from src import auth
    monkeypatch.setenv("WEBUI_PASSWORD", auth.hash_password("pw"))
    from src.main import app
    with TestClient(app, headers={"Origin": TEST_ORIGIN}) as c:
        yield c


@pytest.fixture(autouse=True)
def _stub_connection_checks(request, monkeypatch):
    """Die Live-Verbindungsprüfung (IMAP-Login + LLM-models.list) beim POST /save
    wird in Tests standardmäßig zu No-Ops gemacht: Endpoint-Tests prüfen die
    Formular-/Speicherlogik, nicht die echte Konnektivität, und dürfen kein
    Netzwerk anfassen. Tests, die die Prüfung selbst testen wollen, setzen den
    Marker `@pytest.mark.real_conn_check` — dann bleibt die echte Implementierung
    aktiv (und mockt bei Bedarf MailBox/Anthropic gezielt selbst)."""
    if request.node.get_closest_marker("real_conn_check"):
        return
    import src.validate_conn as validate_conn

    monkeypatch.setattr(validate_conn, "check_imap", lambda *a, **k: None)
    monkeypatch.setattr(validate_conn, "check_llm", lambda *a, **k: None)


@pytest.fixture(autouse=True)
def reset_docker_client_cache():
    import src.docker_ctrl as docker_ctrl
    docker_ctrl._client = None
    yield
    docker_ctrl._client = None


@pytest.fixture(autouse=True)
def reset_sessions():
    """Der Session-Store (`auth._sessions`) ist wie `_login_failures`/
    `_login_lockouts` ein reiner In-Memory-Prozess-Zustand — ohne Reset
    koennten sich Tests ueber den module-level `set` hinweg beeinflussen."""
    from src import auth
    auth._sessions.clear()
    yield
    auth._sessions.clear()


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


@pytest.fixture(autouse=True)
def reset_pending_uploads():
    """Phase 12 (ATT-02): der Pending-Upload-Store (`chat_tools._pending_uploads`)
    ist analog zu `_authorized_move_sessions` ein reiner In-Memory-Prozess-
    Zustand — ohne Reset könnten sich Tests über den module-level `dict` hinweg
    beeinflussen."""
    import src.chat_tools as chat_tools
    chat_tools._pending_uploads.clear()
    yield
    chat_tools._pending_uploads.clear()
