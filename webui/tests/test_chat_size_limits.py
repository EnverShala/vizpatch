"""Review WR-03: Groessen-Limits fuer Chat message/history + Hart-Kappung."""
import pytest

from src import chat_tools


@pytest.fixture
def cfg(tmp_path, monkeypatch):
    monkeypatch.setenv("WEBUI_CONFIG_ROOT", str(tmp_path / "config"))
    monkeypatch.setenv("WEBUI_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    return tmp_path


def test_chat_send_rejects_oversize_message(authed_client, cfg):
    r = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "x" * 8001},
    )
    assert r.status_code == 422


def test_chat_send_rejects_oversize_history(authed_client, cfg):
    r = authed_client.post(
        "/chat/info/send",
        auth=("admin", "pw"),
        data={"message": "hi", "history": "y" * 200_001},
    )
    assert r.status_code == 422


def test_build_initial_messages_caps_message():
    msgs = chat_tools._build_initial_messages(None, "m" * 20000, None)
    # Letzte Nachricht ist der aktuelle user-Turn.
    assert len(msgs[-1]["content"]) <= chat_tools.MAX_MESSAGE_CHARS
