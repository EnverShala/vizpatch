from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest
from cryptography.fernet import Fernet, InvalidToken


def test_encrypt_value_returns_prefixed_token(tmp_path, monkeypatch):
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    import src.crypto as crypto
    result = crypto.encrypt_value("geheim")
    assert result.startswith(crypto.ENC_PREFIX)
    assert result != "geheim"


def test_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    import src.crypto as crypto
    encrypted = crypto.encrypt_value("geheim")
    assert crypto.decrypt_value(encrypted) == "geheim"


def test_legacy_plaintext_passthrough(tmp_path, monkeypatch):
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    import src.crypto as crypto
    assert crypto.decrypt_value("klartext-ohne-prefix") == "klartext-ohne-prefix"


def test_encrypt_empty_and_already_encrypted_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    import src.crypto as crypto
    assert crypto.encrypt_value("") == ""
    assert crypto.encrypt_value("enc:xyz") == "enc:xyz"


def test_is_encrypted(tmp_path, monkeypatch):
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(tmp_path / ".secret_key"))
    import src.crypto as crypto
    assert crypto.is_encrypted("enc:abc") is True
    assert crypto.is_encrypted("klartext") is False


def test_key_created_on_first_call_and_reused_on_second(tmp_path, monkeypatch):
    key_file = tmp_path / ".secret_key"
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(key_file))
    import src.crypto as crypto
    assert not key_file.exists()
    crypto.encrypt_value("erster-aufruf")
    assert key_file.exists()
    first_key = key_file.read_bytes()
    crypto.encrypt_value("zweiter-aufruf")
    second_key = key_file.read_bytes()
    assert first_key == second_key


@pytest.mark.skipif(sys.platform == "win32", reason="chmod 600 not supported on Windows")
def test_key_file_chmod_600(tmp_path, monkeypatch):
    key_file = tmp_path / ".secret_key"
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(key_file))
    import src.crypto as crypto
    crypto.encrypt_value("wert")
    mode = os.stat(key_file).st_mode & 0o777
    assert mode == 0o600


def test_decrypt_with_wrong_key_raises_runtime_error(tmp_path, monkeypatch):
    key_file = tmp_path / ".secret_key"
    monkeypatch.setenv("VIZPATCH_SECRET_KEY_FILE", str(key_file))
    import src.crypto as crypto
    encrypted = crypto.encrypt_value("geheim")

    # Key ersetzen — simuliert gelöschten/ersetzten Key
    key_file.write_bytes(Fernet.generate_key())

    with pytest.raises(RuntimeError, match="Secret konnte nicht entschlüsselt werden"):
        crypto.decrypt_value(encrypted)
