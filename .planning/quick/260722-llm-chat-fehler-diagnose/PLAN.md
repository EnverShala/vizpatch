---
slug: llm-chat-fehler-diagnose
created: 2026-07-22
---

# Quick-Task: Konkrete LLM-Fehlerdiagnose im Agenten-Chat

## Problem (Kunde, 2026-07-22)

Beim Deployment-Test beim Kunden meldet die WebUI im Agenten-Chat:
`[Fehler beim LLM-Aufruf — LLM-Dienst nicht erreichbar.]`
— obwohl ein funktionierender API-Key verwendet wurde.

## Diagnose

Die Meldung stammt aus `webui/src/chat_tools.py:2516`, dem `except Exception`-
Sammelfänger um `client.messages.create` (Zeile 2507). Der Key wurde bereits
erfolgreich Fernet-entschlüsselt (2491 `Anthropic(api_key=...)`), also ist der
Key korrekt — der **API-Aufruf selbst** wirft. Der Sammelfänger maskiert JEDE
Ausnahme (Verbindung, Auth, Modell, Rate-Limit) als „nicht erreichbar", der
echte Grund steht nur im Log (`agentic_chat_llm_call_failed`).

Bei „Key funktioniert woanders, aber beim Kunden nicht" ist die wahrscheinlichste
Ursache ein Netzwerkproblem (`APIConnectionError`): kein Outbound-HTTPS zu
`api.anthropic.com`, Proxy-Zwang oder DNS/TLS-Interception im Kundennetz.

## Lösung

Fehlerklassifikation statt Sammelmeldung: neue Helferfunktion
`describe_llm_error(exc)` übersetzt Anthropic-/Netzwerk-Ausnahmen in konkrete,
betreiber-lesbare deutsche Meldungen (Verbindung / Auth 401 / Berechtigung 403 /
Modell 404 / Rate-Limit 429 / sonstiger HTTP-Status) — ohne Secrets/Stacktraces.
Der Chat-Fehlerpfad nutzt sie, sodass die WebUI beim Kunden den echten Grund
zeigt statt im Log graben zu müssen.

Rückwärtskompatibel: unbekannte Ausnahmen ergeben weiterhin „LLM-Dienst nicht
erreichbar." (bestehendes Verhalten/Tests bleiben grün).

## Tasks

1. `describe_llm_error(exc)` in `chat_tools.py` (+ Anthropic-Exception-Importe).
2. Chat-Fehlerpfad (`except Exception`) nutzt die Helferfunktion; Log-Event um
   `error_type` erweitert.
3. Test: jede Fehlerklasse → passende Meldung; generische Ausnahme → Fallback.

## Verify

- `python -m pytest tests/test_chat_tools.py -x` grün, keine Regression.
