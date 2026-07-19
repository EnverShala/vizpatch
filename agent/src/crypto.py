"""Fernet-Verschlüsselung für Secret-Werte in der .env (SEC-01/02).

Kapselt Key-Erzeugung (`/config/.secret_key`, chmod 600), `encrypt_value`/
`decrypt_value` mit `enc:`-Prefix und tolerante Legacy-Klartext-Behandlung.
Kein Master-Passwort (D-48) — die Key-Datei liegt im selben Config-Bind-Mount,
der ohnehin komplett gebackupt wird.

SYNC-KONTRAKT (Review WR-06): Diese Datei existiert absichtlich BYTE-IDENTISCH
als `agent/src/crypto.py` UND `webui/src/crypto.py` — zwei getrennte
Docker-Images, bewusst KEIN Shared-Package. Jede Änderung MUSS in beiden
Dateien identisch erfolgen (Prefix, Key-Pfad und Fehlerübersetzung sind ein
Cross-Service-Kontrakt: WebUI verschlüsselt, Agent entschlüsselt).
`tests/test_crypto_sync.py` in beiden Services schlägt fehl, sobald die
Kopien auseinanderlaufen.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

ENC_PREFIX = "enc:"


def _key_file() -> Path:
    return Path(os.getenv("VIZPATCH_SECRET_KEY_FILE", "/config/.secret_key"))


def _load_or_create_key() -> bytes:
    path = _key_file()
    if path.exists():
        return path.read_bytes()
    key = Fernet.generate_key()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(key)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except PermissionError:
        pass
    return key


def load_or_create_key() -> bytes:
    """Öffentlicher Accessor auf den persistenten Fernet-Key (Review IN-05):
    Aufrufer AUSSERHALB dieses Moduls (z.B. webui/src/chat_tools.py, das daraus
    einen zweckgebundenen HMAC-Key ableitet) nutzen DIESE Funktion — eine
    interne Umbenennung von `_load_or_create_key` bricht so keinen Fremdcode."""
    return _load_or_create_key()


def encrypt_value(plaintext: str) -> str:
    if not plaintext or plaintext.startswith(ENC_PREFIX):
        return plaintext
    token = Fernet(_load_or_create_key()).encrypt(plaintext.encode("utf-8")).decode("ascii")
    return f"{ENC_PREFIX}{token}"


def decrypt_value(value: str) -> str:
    if not value or not value.startswith(ENC_PREFIX):
        return value  # Klartext-Legacy oder leer — unverändert zurückgeben
    token = value[len(ENC_PREFIX):]
    try:
        return Fernet(_load_or_create_key()).decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise RuntimeError(
            "Secret konnte nicht entschlüsselt werden (InvalidToken). "
            "Ursache meist: Key-Datei /config/.secret_key fehlt oder wurde ersetzt, "
            "oder der .env-Wert wurde manuell verändert. Siehe SEC-03-Doku (Reset-Pfad)."
        ) from e


def is_encrypted(value: str) -> bool:
    return bool(value) and value.startswith(ENC_PREFIX)
