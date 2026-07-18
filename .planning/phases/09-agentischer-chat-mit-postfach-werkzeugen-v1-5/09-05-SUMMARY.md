---
phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5
plan: 05
subsystem: chat
tags: [ast-scan, no-auto-send, dsgvo, avv, drift-guard]

requires:
  - phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5
    provides: "09-01..09-04: vollständiger Werkzeugsatz (mails_suchen/mail_lesen/entwuerfe_auflisten/entwurf_lesen/entwurf_bearbeiten/mail_in_papierkorb/entwurf_in_papierkorb) in TOOL_SCHEMAS/TOOL_HANDLERS"
provides:
  - "Struktureller Kein-Auto-Send-Wächter (AST-Scan): chat_tools.py importiert/nutzt nachweislich keine SMTP-/Send-API (kein smtplib-Import, kein sendmail/send_message/SMTP(...)-Aufruf) — immun gegen False-Positives aus erklärenden Docstring-Erwähnungen wie 'kein SMTP (D-77)'"
  - "Wortgrenzen-Scan über TOOL_SCHEMAS-Namen+descriptions gegen verbotene Sende-Muster (send/senden/versend/smtp/reply/verschick), mit Allowlist für legitime No-Send-Formulierungen und den IMAP-Header-Namen In-Reply-To"
  - "TOOL_HANDLERS/TOOL_SCHEMAS-Whitelist-Assertion: exakt die 7 erlaubten Werkzeuge, kein Sende-Tool"
  - "_datenschutz.html Ziffer 6 + AVV-CHECKLIST.md §6.2 auf die tatsächlichen v1.5-Fähigkeiten angeglichen (D-81): suchen/lesen, Entwurf umformulieren, Papierkorb-Move nach Bestätigung, Kein-Auto-Send"
  - "Phase-9-Abschluss-Verifikation: volle webui-Suite + 5 Drift-Guard-Sync-Suiten grün, keine Änderung an geschützten Zwillingen/agent/"
affects: []

tech-stack:
  added: []
  patterns:
    - "AST-basierter struktureller Kein-Auto-Send-Wächter statt reinem Text-/Zeilen-Grep: ast.parse erfasst Docstrings/Kommentare nur als String-Konstanten, nie als Import-/Call-Knoten — dadurch immun gegen genau die Art False-Positive, die ein '#'-Zeilenfilter (wie ursprünglich für diesen Task angedacht) an einer realen Docstring-Zeile ('kein Sende-Pfad, kein SMTP (D-77)') ausgelöst hätte."
    - "Wortgrenzen-Regex (\\b) statt reinem Substring-Test beim Scan der Tool-Beschreibungen: verhindert False-Positives durch deutsche Komposita, die eine verbotene Zeichenkette als Teilwort enthalten (z. B. 'Absender' enthält 'send', aber keinen eigenständigen Wortanfang 'send'). Kombiniert mit einer expliziten Allowlist für gewollte No-Send-Formulierungen ('Sendet NICHTS', 'Kein-Auto-Send') und den legitimen Fachbegriff 'In-Reply-To' (enthält 'reply' als eigenständiges Wort zwischen Bindestrichen, ist aber der IMAP-Threading-Header-Name, kein Sende-Hinweis)."
    - "Jeder Scan-Helfer kommt mit einem Positiv-Fall (realer Code/Werkzeugsatz bleibt clean), einem Negativ-Fall (ein injiziertes Sende-Muster wird tatsächlich erkannt — kein Blindgänger) und einer Gegenprobe (bewusste No-Send-Hinweise/Kommentare lösen keinen False-Positive aus) — Muster aus Phase 8 (test_addin_readonly.py) fortgeführt."

key-files:
  created: []
  modified:
    - webui/tests/test_chat_tools.py
    - webui/src/templates/_datenschutz.html
    - .planning/phases/02-deployment-beim-kunden/AVV-CHECKLIST.md

key-decisions:
  - "AST-Scan statt der im Plan wörtlich vorgeschlagenen '#'-Kommentarzeilen-Filterung für den Quelltext-Wächter: chat_tools.py enthält eine reale Docstring-Zeile ('kein Sende-Pfad, kein SMTP (D-77)', Zeile 438) — das ist KEIN '#'-Kommentar, sondern Teil eines Docstrings. Ein naiver Zeilenfilter (`lstrip().startswith('#')`) hätte diese Zeile NICHT ausgeschlossen und den Wächter beim ersten Lauf selbst-invalidiert (SMTP-Substring-Match auf der eigenen erklärenden Docstring). Der AST-Scan prüft stattdessen echte Import-/Call-Knoten und ignoriert Docstring-Inhalte strukturell korrekt, ohne eine Sonderbehandlung für diese eine Zeile zu brauchen."
  - "Wortgrenzen-Regex statt reinem Substring-Scan für die TOOL_SCHEMAS-Beschreibungs-Prüfung: ein naiver `in`-Substring-Test hätte auf 'Absender' (enthält 'send') und 'In-Reply-To' (enthält 'reply' zwischen Bindestrichen) false-positiv angeschlagen — beide sind bereits in den realen Werkzeug-Beschreibungen aus 09-01..09-04 vorhanden. `\\b`-Wortanfangs-Grenzen + eine kleine Allowlist gewollter No-Send-Formulierungen lösen das, ohne die Erkennungsfähigkeit für ein tatsächlich hinzugefügtes Sende-Werkzeug zu schwächen (durch dedizierte Negativ-Fall-Tests belegt)."
  - "Datenschutz-Ziffer-6-Angleichung listet die drei Fähigkeiten explizit als `<ul>` statt in einem Fließtext-Satz (Abweichung vom bisherigen Prosa-Stil des Dokuments) — bessere Lesbarkeit für die konkreten, rechtlich relevanten Einzelaktionen (suchen/lesen, umformulieren, Papierkorb-Move mit Bestätigungspflicht), die künftig einzeln zitierfähig sein müssen (z. B. für die AVV-Abstimmung mit dem Betreiber)."

requirements-completed: [CTOOL-05]

duration: 40min
completed: 2026-07-18
---

# Phase 9 Plan 5: Struktureller Kein-Auto-Send-Wächter + Datenschutz/AVV-Angleichung Summary

**AST-basierter Kein-Auto-Send-Wächter (kein smtplib/SMTP/sendmail/send_message strukturell im Werkzeugsatz) plus Angleichung der Datenschutzerklärung Ziffer 6 und AVV-Checkliste §6.2 auf die tatsächlichen v1.5-Fähigkeiten (suchen/lesen, Entwurf umformulieren, Papierkorb-Move nur nach Bestätigung) — letzter Plan der Phase 9, volle 368/3-Suite grün.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-07-18 (nach 09-04-Abschluss)
- **Completed:** 2026-07-18
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- `_scan_ast_for_forbidden_smtp_send_api(source_text)`: strukturelle AST-Analyse von `chat_tools.py` — findet echte `import smtplib`-Statements und `sendmail(...)`/`send_message(...)`/`SMTP(...)`/`SMTP_SSL(...)`-Aufrufe, ignoriert Docstrings/Kommentare naturgemäß (kein Import-/Call-Knoten). 3 Tests: Positiv-Fall (realer Quelltext clean), Negativ-Fall (injiziertes `import smtplib` + `.sendmail(...)` wird erkannt), Gegenprobe (die reale Docstring-Erwähnung „kein SMTP (D-77)" löst keinen False-Positive aus — genau die Lücke, die ein reiner `#`-Kommentarfilter gehabt hätte).
- `_scan_tool_schemas_for_forbidden_send_patterns(schemas)`: Wortgrenzen-Scan (`\b`) über `TOOL_SCHEMAS`-Namen+descriptions gegen `send`/`senden`/`versend`/`smtp`/`reply`/`verschick`, mit Allowlist für „Sendet NICHTS"/„kein Senden"/„Kein-Auto-Send"/„In-Reply-To". 3 Tests: Positiv-Fall (realer Werkzeugsatz clean), Negativ-Fall (ein `mail_senden`-Tool mit „Versendet … per SMTP"-Beschreibung wird erkannt), Gegenprobe (die gewollten No-Send-Hinweise triggern nichts).
- `test_tool_handlers_whitelist_is_exactly_the_seven_allowed_tools_no_send_tool`: `set(TOOL_HANDLERS)` == `set(schema["name"] for schema in TOOL_SCHEMAS)` == exakt die sieben erlaubten (nicht-sendenden) Werkzeuge — kein zusätzliches, insbesondere kein Sende-Werkzeug registriert.
- `_datenschutz.html` Ziffer 6 benennt jetzt konkret: (a) Mails/Entwürfe durchsuchen und lesen (read-only, PII-redigiert vor KI-Übermittlung), (b) Entwurf umformulieren (neue Fassung im Entwürfe-Ordner, alte in den Papierkorb), (c) Mails/Entwürfe in den Papierkorb verschieben (kein endgültiges Löschen, reversibel, nur nach ausdrücklicher Bestätigung im Chat) — Kein-Auto-Send bleibt explizit und uneingeschränkt erwähnt.
- `AVV-CHECKLIST.md` §6.2 bekommt einen neuen Checklisten-Punkt „Agentische Postfach-Werkzeuge (Phase 9)" mit demselben Verarbeitungszweck (suchen/lesen/umformulieren/Papierkorb-Move mit Bestätigungspflicht, Kein-Auto-Send), Muster-/Prüf-Hinweis-Rahmen des Dokuments unverändert beibehalten.
- Phasen-Abschluss-Verifikation: volle webui-Suite **368 passed / 3 skipped** (Baseline 361/3 + 7 neue Tests), alle 5 Drift-Guard-Sync-Suiten grün, `git diff` gegen `webui/src/{llm.py,pii.py,crypto.py,provider_config.py}` + `agent/` leer.

## Task Commits

1. **Task 1: Struktureller Kein-Auto-Send-Wächter-Test (CTOOL-05/D-77)** - `639b58d` (test)
2. **Task 2: Datenschutzerklärung Ziffer 6 + AVV-Checkliste §6.2 an tatsächliche Fähigkeiten angleichen (D-81)** - `a38bb3d` (docs)
3. **Task 3: Phasen-Abschluss-Verifikation** — kein eigener Commit (reine Verifikation ohne Code-/Doku-Änderung, Ergebnisse siehe unten)

**Plan metadata:** commit folgt (docs: complete plan)

## Files Created/Modified

- `webui/tests/test_chat_tools.py` — 7 neue Tests: AST-basierter SMTP-/Send-API-Scan (Positiv/Negativ/Gegenprobe), Wortgrenzen-Scan der TOOL_SCHEMAS-Beschreibungen gegen Sende-Muster (Positiv/Negativ/Gegenprobe), Whitelist-Assertion für die exakten 7 erlaubten Werkzeuge
- `webui/src/templates/_datenschutz.html` — Ziffer 6 komplett neu formuliert: konkrete Werkzeug-Fähigkeiten als Liste statt allgemeiner Prosa, Papierkorb-Move mit Bestätigungspflicht explizit benannt, Kein-Auto-Send-Absatz verschärft
- `.planning/phases/02-deployment-beim-kunden/AVV-CHECKLIST.md` — §6.2 um „Agentische Postfach-Werkzeuge (Phase 9)"-Punkt ergänzt

## Decisions Made

Siehe `key-decisions` im Frontmatter oben. Zentral: **AST-Scan statt Text-Zeilenfilter** für den Quelltext-Wächter (die im Plan wörtlich vorgeschlagene `lstrip().startswith('#')`-Filterung hätte an einer echten Docstring-Zeile in `chat_tools.py` selbst-invalidiert) und **Wortgrenzen-Regex statt Substring-Test** für den Beschreibungs-Scan (verhindert False-Positives durch „Absender"/„In-Reply-To" in den bereits bestehenden Tool-Beschreibungen aus 09-01..09-04).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Naive Text-/Substring-Scans hätten sich an realem Code/Beschreibungen selbst-invalidiert — auf AST- bzw. Wortgrenzen-Scans umgestellt**
- **Found during:** Task 1 (Implementierung des Kein-Auto-Send-Wächters)
- **Issue:** Der Plan spezifizierte wörtlich eine `'#'`-Kommentarzeilen-Filterung für den Quelltext-Scan und einen reinen Substring-Scan (`pattern in haystack`) für die TOOL_SCHEMAS-Beschreibungen. Beim Implementieren zeigte sich: (a) `chat_tools.py` enthält an Zeile 438 eine Docstring-Erwähnung „kein Sende-Pfad, kein SMTP (D-77)" — kein `'#'`-Kommentar, ein naiver Zeilenfilter hätte das nicht ausgeschlossen und den Test sofort rot gemacht; (b) die realen Tool-Beschreibungen aus 09-01..09-04 enthalten bereits „Absender" (enthält Substring „send") und „In-Reply-To" (enthält Substring „reply") — ein reiner Substring-Scan hätte hier ebenfalls false-positiv angeschlagen, noch bevor irgendein echtes Sende-Werkzeug hinzugefügt wurde.
- **Fix:** Quelltext-Scan auf `ast.parse` + Walk über `Import`/`ImportFrom`/`Call`-Knoten umgestellt (ignoriert Docstrings/Kommentare strukturell, kein Sonderfall nötig). Beschreibungs-Scan auf Wortgrenzen-Regex (`\bpattern`) umgestellt + kleine Allowlist für „Sendet NICHTS"/„Kein-Auto-Send"/„In-Reply-To", die vor dem Scan aus dem Text entfernt wird.
- **Files modified:** `webui/tests/test_chat_tools.py`
- **Verification:** `test_guard_ast_scan_ignores_smtp_mentioned_only_in_docstrings_or_comments`, `test_guard_ignores_allowed_no_send_negations_in_description`, `test_chat_tools_source_has_no_smtp_or_send_api_structurally`, `test_no_tool_schema_name_or_description_matches_forbidden_send_patterns` — alle grün; volle Suite 368/3.
- **Committed in:** `639b58d`

---

**Total deviations:** 1 auto-fixed (Rule 1 — Korrektur eines False-Positive-Risikos in der Plan-Spezifikation selbst, kein Scope-Creep).
**Impact on plan:** Die Kern-Wahrheit aus dem Plan (struktureller Nachweis, kein Sende-Werkzeug im Werkzeugsatz) ist vollständig erfüllt — robuster als die wörtliche Spezifikation, ohne dass die Erkennungsfähigkeit für ein tatsächlich hinzugefügtes Sende-Werkzeug/SMTP-Aufruf sinkt (durch dedizierte Negativ-Fall-Tests belegt).

## Issues Encountered

None.

## Verification (re-run at Summary-time)

- `cd webui && python -m pytest tests/test_chat_tools.py -x -q` → **70 passed**
- `cd webui && python -m pytest -q` → **368 passed, 3 skipped** (Baseline 361/3 + 7 neue Tests)
- `cd webui && python -m pytest tests/test_llm_sync.py tests/test_pii_sync.py tests/test_crypto_sync.py tests/test_provider_config_sync.py tests/test_model_defaults_sync.py -q` → 5 passed (Drift-Guard unverändert grün)
- `git diff --name-only HEAD~3 HEAD -- webui/src/llm.py webui/src/pii.py webui/src/crypto.py webui/src/provider_config.py agent/` → leer (D-73-Drift-Guard unangetastet)
- `grep -n "smtplib\|send_message\|TOOL_HANDLERS" webui/tests/test_chat_tools.py` → mehrere Treffer, Wächter belegt
- `grep -ni "Papierkorb\|Bestätigung\|umformul\|kein.*sende" webui/src/templates/_datenschutz.html` → mehrere Treffer in Ziffer 6
- `grep -n "Phase 9\|Papierkorb\|Bestätigung" .planning/phases/02-deployment-beim-kunden/AVV-CHECKLIST.md` → neuer §6.2-Punkt belegt
- `cd webui && python -m pytest tests/test_endpoints_datenschutz.py -q` → 8 passed (Datenschutz-Rendering unverändert grün)

**CTOOL-Requirements-Abdeckung (Phase 9 komplett):**

| Requirement | Abgedeckt durch | Status |
|---|---|---|
| CTOOL-01 (Tool-Use-Loop) | 09-01 (`run_agentic_chat`, Anthropic-Schleife + Fallback) | ✅ |
| CTOOL-02 (Read-only-Werkzeuge) | 09-01 (`mails_suchen`) + 09-02 (`mail_lesen`/`entwuerfe_auflisten`/`entwurf_lesen`) | ✅ |
| CTOOL-03 (Entwurf bearbeiten) | 09-03 (`entwurf_bearbeiten`, Threading erhalten, APPEND→MOVE) | ✅ |
| CTOOL-04 (Destruktive Papierkorb-Tools) | 09-04 (`mail_in_papierkorb`/`entwurf_in_papierkorb`, HMAC-Token-Gate) | ✅ |
| CTOOL-05 (Kein-Auto-Send strukturell + Doku-Angleichung) | 09-05 (dieser Plan) | ✅ |

Der Anthropic-Tool-Use-Pfad ist end-to-end (mit gemocktem `anthropic.Anthropic`-Client über alle 5 Pläne) bewiesen — inkl. Mehrrunden-Flows, Endlosschutz (`MAX_TOOL_ROUNDS`), Bestätigungs-Gate über zwei Chat-Runden hinweg. OpenAI/Google laufen über `_run_fallback_chat` sauber auf den rein beratenden Chat aus Phase 7 zurück (kein Absturz, kein Tool-Zugriff) — best effort, keine volle Tool-Use-Parität zugesichert (bewusst, siehe 09-CONTEXT.md `<deferred>`).

## User Setup Required

None - keine externe Service-Konfiguration nötig.

## Next Phase Readiness

- **CTOOL-05 vollständig erfüllt, Phase 9 (Agentischer Chat mit Postfach-Werkzeugen, v1.5) damit code-komplett und verifiziert.**
- Kein-Auto-Send bleibt strukturell garantiert (AST-Wächter + Wortgrenzen-Schema-Scan als dauerhafte Regressionswächter, nicht nur Konvention).
- Rechtstexte (Datenschutz Ziffer 6, AVV §6.2) spiegeln jetzt die tatsächlichen v1.5-Fähigkeiten — bleiben als „Muster/Entwurf" gekennzeichnet, finale rechtliche Prüfung bleibt Betreiber-Pflicht (unverändert).
- Keine Blocker. Nächster sinnvoller Schritt laut STATE.md/PROJECT.md: Fokus zurück auf den Esso-Rollout (Deployment-Paket, DSGVO/AVV-Abschluss mit Anthropic, Vor-Ort-Termin) statt weiterem Feature-Ausbau.

---
*Phase: 09-agentischer-chat-mit-postfach-werkzeugen-v1-5*
*Completed: 2026-07-18*

## Self-Check: PASSED

- FOUND: webui/tests/test_chat_tools.py
- FOUND: webui/src/templates/_datenschutz.html
- FOUND: .planning/phases/02-deployment-beim-kunden/AVV-CHECKLIST.md
- FOUND commit: 639b58d (Task 1)
- FOUND commit: a38bb3d (Task 2)
