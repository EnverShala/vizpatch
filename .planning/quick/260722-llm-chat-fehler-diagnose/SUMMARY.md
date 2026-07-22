---
slug: llm-chat-fehler-diagnose
status: complete
date: 2026-07-22
commit: f0b1701
---

# Summary: Konkrete LLM-Fehlerdiagnose im Agenten-Chat

## Auslöser

Kunden-Deployment-Test: WebUI-Agenten-Chat meldete
`[Fehler beim LLM-Aufruf — LLM-Dienst nicht erreichbar.]` trotz funktionierendem
API-Key.

## Root Cause

Der `except Exception`-Sammelfänger in `webui/src/chat_tools.py` um
`client.messages.create` maskierte JEDE Ausnahme als „nicht erreichbar". Der Key
war bereits erfolgreich Fernet-entschlüsselt (an `Anthropic(api_key=...)`
übergeben), also korrekt — der API-Aufruf selbst schlug fehl. Wahrscheinlichste
Ursache bei „Key funktioniert woanders, aber nicht beim Kunden": Netzwerk/
Firewall/Proxy (kein Outbound-HTTPS zu `api.anthropic.com`). Der echte Grund war
nur im Docker-Log sichtbar.

## Änderung

- `describe_llm_error(exc)` in `chat_tools.py`: klassifiziert Anthropic-/
  Netzwerk-Ausnahmen → konkrete deutsche Meldung (Verbindung / Auth 401 /
  Berechtigung 403 / Modell 404 / Rate-Limit 429 / sonstiger HTTP-Status),
  ohne Secrets/Stacktraces. Prüfreihenfolge: Status-Unterklassen vor
  `APIStatusError`, `APIConnectionError` separat.
- Chat-Fehlerpfad nutzt die Funktion; Log-Event um `error_type` erweitert.
- Unbekannte Ausnahmen → unveränderte Fallback-Meldung (rückwärtskompatibel).
- 3 neue Tests (`test_chat_tools.py`): Klassen-Mapping, generischer Fallback,
  Integration über `run_agentic_chat` (APIConnectionError → spezifische Meldung,
  kein Key-Leak).

## Verifikation

- `tests/test_chat_tools.py`: 149 passed (inkl. 3 neue).
- Vorbestehende, unabhängige Fehler in `test_endpoints_style.py` /
  `test_rate_limits.py` (auf Baseline ohne diese Änderung reproduziert) — nicht
  Teil dieses Tasks.

## Nächster Schritt (Kunde)

Betreiber testet erneut im Chat: Die UI zeigt jetzt den echten Fehlertyp.
Bei „Verbindung zu api.anthropic.com fehlgeschlagen" → Outbound-HTTPS/Proxy des
Kundenservers prüfen.
