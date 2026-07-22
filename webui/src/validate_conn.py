"""Live-Verbindungs-/Zugangsprüfung beim Agent-Speichern.

Prüft die ÜBERMITTELTEN (noch nicht persistierten) Zugangsdaten gegen die echten
Dienste, damit kein „kaputter" Agent gespeichert wird (Betreiber-Wunsch: hart
blockieren statt einen nicht funktionierenden Agenten zu speichern):

- IMAP: echter Login gegen den aufgelösten Host, kurzer Timeout.
- LLM:  günstiger Auth+Netz-Aufruf (``models.list()``) mit dem übermittelten Key.
        Fängt genau das beim Kunden aufgetretene Problem ab (api.anthropic.com
        wegen Firewall/Proxy nicht erreichbar), bevor der Agent gespeichert wird.

KEIN SMTP — das Produkt versendet nie (nur Entwürfe via IMAP APPEND).
Secrets (Passwort/API-Key) werden NIE geloggt.
"""
from __future__ import annotations

import logging
import socket

from imap_tools import MailBox, MailBoxUnencrypted

from .chat_tools import _agent_imap_settings, describe_llm_error

logger = logging.getLogger("vizpatch.validate_conn")

# Kurzer Probe-Timeout: lang genug für langsame Provider, kurz genug, dass ein
# falscher Host / geblockter Port den Speichern-Request nicht minutenlang hängen
# lässt.
IMAP_PROBE_TIMEOUT = 15.0
LLM_PROBE_TIMEOUT = 15.0


class ConnectionCheckError(Exception):
    """Verbindungs-/Zugangsprüfung fehlgeschlagen. `str(e)` ist eine betreiber-
    lesbare deutsche Meldung OHNE Secrets — direkt für die WebUI verwendbar."""


def check_imap(env: dict) -> None:
    """Login-Probe mit IMAP_USER/IMAP_PASSWORD (Klartext im `env`-dict) gegen den
    via `_agent_imap_settings` aufgelösten Host. `IMAP_PASSWORD` MUSS Klartext
    sein (bereits entschlüsselt). Wirft `ConnectionCheckError` bei jedem
    Fehlschlag; kehrt bei erfolgreichem Login stillschweigend zurück."""
    user = (env.get("IMAP_USER") or "").strip()
    password = (env.get("IMAP_PASSWORD") or "").strip()
    if not user or not password:
        raise ConnectionCheckError("IMAP-Benutzer und -Passwort dürfen nicht leer sein.")

    try:
        settings = _agent_imap_settings(env)
    except RuntimeError as e:
        # resolve_imap_config: Domain nicht auto-detektierbar (keine statische
        # Tabelle, kein MX-Treffer) — die Meldung nennt bereits den IMAP_HOST-Hinweis.
        raise ConnectionCheckError(str(e)) from e

    host, port, ssl = settings["host"], settings["port"], settings["ssl"]
    mailbox_cls = MailBox if ssl else MailBoxUnencrypted
    try:
        # imap_tools verbindet bereits im Konstruktor -> Host/Netz-Fehler fallen
        # hier an, Auth-Fehler erst bei login().
        with mailbox_cls(host=host, port=port, timeout=IMAP_PROBE_TIMEOUT) as mb:
            mb.login(user, password)
    except (socket.timeout, socket.gaierror, ConnectionError, OSError) as e:
        logger.warning(
            "imap_conn_check_unreachable",
            extra={"host": host, "port": port, "error": str(e), "error_type": type(e).__name__},
        )
        raise ConnectionCheckError(
            f"IMAP-Server nicht erreichbar ({host}:{port}) — Host/Port/Netzwerk prüfen."
        ) from e
    except Exception as e:
        # imaplib.IMAP4.error o.ä. bei abgelehnter Anmeldung (kein Socket-Fehler).
        logger.warning(
            "imap_conn_check_login_failed",
            extra={"host": host, "error_type": type(e).__name__},
        )
        raise ConnectionCheckError(
            "IMAP-Anmeldung fehlgeschlagen — Benutzer/Passwort (bzw. App-Passwort) prüfen."
        ) from e


def check_llm(provider: str, api_key: str) -> None:
    """Günstige Auth+Netz-Probe (``models.list()``) mit dem übermittelten Key.
    Wirft `ConnectionCheckError` bei jedem Fehlschlag. Anthropic-Fehler werden
    über `describe_llm_error` konkret klassifiziert (Verbindung / Auth / usw.);
    OpenAI/Google best-effort."""
    provider = (provider or "anthropic").strip().lower()
    api_key = (api_key or "").strip()
    if not api_key:
        raise ConnectionCheckError("Kein API-Key vorhanden.")

    try:
        if provider == "openai":
            from openai import OpenAI

            OpenAI(api_key=api_key, timeout=LLM_PROBE_TIMEOUT, max_retries=0).models.list()
        elif provider == "google":
            from google import genai

            list(genai.Client(api_key=api_key).models.list())
        else:  # anthropic + Fallback für unbekannte Provider
            from anthropic import Anthropic

            Anthropic(api_key=api_key, timeout=LLM_PROBE_TIMEOUT, max_retries=0).models.list()
    except ImportError as e:
        raise ConnectionCheckError(
            f"LLM-Provider '{provider}' nicht verfügbar (SDK fehlt)."
        ) from e
    except ConnectionCheckError:
        raise
    except Exception as e:
        logger.warning(
            "llm_conn_check_failed",
            extra={"provider": provider, "error": str(e), "error_type": type(e).__name__},
        )
        raise ConnectionCheckError(f"LLM-Zugang fehlgeschlagen — {describe_llm_error(e)}") from e
