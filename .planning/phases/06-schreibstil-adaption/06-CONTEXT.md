# Phase 6: Schreibstil-Adaption pro Agent (v1.3) - Context

**Gathered:** 2026-07-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Jeder Agent übernimmt automatisch den Schreibstil des Postfachbesitzers — dem Firmen-Kontext getreu. Beim Agent-Setup extrahiert ein einmaliger LLM-Lauf aus den letzten ~30 Mails des Gesendet-Ordners **plus einer optionalen manuellen Stil-Angabe des Betreibers** ein Stil-Profil (`/config/agents/<id>/style.md`). Das Profil wird bei jedem Draft zusätzlich zu `context.md` injiziert — mit fester Prompt-Hierarchie: **context.md bestimmt WAS gesagt wird (fachlich führend), style.md nur WIE**. Im WebUI ist das Profil pro Agent sichtbar, editierbar und per „Schreibstil neu lernen"-Button neu generierbar.

**Nicht in dieser Phase:** Kein Learning-Loop, kein Fine-Tuning, keine periodische Auto-Aktualisierung des Profils (bestätigt in der Discussion 2026-07-17: Extraktion läuft genau einmal beim Setup + manuell per Button — der Agent liest style.md nur, er schreibt es nie). Kein Auto-Send. Keine Änderung am Multi-Agent-/Verschlüsselungs-Fundament aus Phase 5.

</domain>

<decisions>
## Implementation Decisions

### D-52: Zwei Stil-Quellen, kombiniert in EINEM LLM-Call (locked, Nutzer-Entscheidung 2026-07-17)
Es gibt zwei Eingabequellen für die Stil-Extraktion:
1. Die letzten N gesendeten Mails (Default 30, `STYLE_SAMPLE_COUNT`) aus dem Gesendet-Ordner.
2. Ein **optionales Freitext-Feld im WebUI**, in dem der Betreiber seinen Schreibstil kurz beschreiben oder ein Beispiel einfügen kann (nicht Pflicht, darf leer bleiben) — vor allem für neue/leere Postfächer gedacht.

Beide Quellen gehen als Input in **einen** Extraktions-Call: Das LLM destilliert aus gesendeten Mails + manueller Angabe genau EIN `style.md`. Bei leerem/fehlendem Gesendet-Ordner entsteht das Profil nur aus der manuellen Angabe; sind beide Quellen leer, entsteht kein Profil (graceful, Hinweis im WebUI — STY-05 unverändert).
**Why:** Ein Profil, eine Wahrheit — keine widersprüchlichen Blöcke im Prompt; leere Postfächer sind trotzdem versorgt.

### D-53: Extraktion läuft in der WebUI, synchron (locked, Nutzer-Entscheidung 2026-07-17)
Die Stil-Extraktion (Setup + „Schreibstil neu lernen"-Button) läuft im WebUI-Prozess: Die WebUI holt die letzten ~30 gesendeten Mails selbst per IMAP (**imap-tools wird WebUI-Dependency**) und ruft das LLM direkt über den Phase-5-Adapter-Ansatz (Provider/Key des Agenten) — analog zum Context-KI-Assistenten (`llm_seed.py`). Ergebnis erscheint sofort im Formular (HTMX-Indikator, ~30–60 s Wartezeit akzeptiert).
**Konsequenz (Esso-Guard gratis):** Extraktion passiert ausschließlich bei Agent-Anlage und Button-Klick in der WebUI — bestehende/migrierte Agenten (Esso) lernen nie ungefragt; kein Marker-Flag, kein Agent-seitiger Setup-Hook nötig (SC5 per Design erfüllt).

### D-54: Einmaligkeit + Re-Learn-Semantik (locked)
Das Profil entsteht genau einmal beim Agent-Setup (Default an via `ENABLE_STYLE_ADAPTION=true`). Danach ändert es sich nur auf zwei Wegen: (a) Betreiber editiert `style.md` direkt im WebUI-Fieldset (Section-Save), (b) Betreiber klickt „Schreibstil neu lernen" — Bestätigung nötig, Extraktion läuft erneut über die dann aktuellen gesendeten Mails + aktuelles Freitext-Feld und **überschreibt** das Profil. Der Agent-Container fasst `style.md` nie an, er liest es nur beim Draften.

### D-55: Extraktion mit dem Draft-Modell (locked, Nutzer-Entscheidung 2026-07-17)
Die Extraktion nutzt das pro Provider fest verdrahtete **Draft-Modell** (Anthropic → Sonnet-Klasse; OpenAI/Google-Äquivalente aus Phase 5, D-49). Kein eigenes Modell-Feld. Begründung: Stil-Analyse ist die Stärke der größeren Modelle, der Call läuft nur bei Setup/Button — einmalige Kosten, Qualität zählt.

### D-56: style.md mit festem Abschnitts-Schema (locked, Nutzer-Entscheidung 2026-07-17)
`style.md` hat vorgegebene Markdown-Überschriften: **Anrede, Du/Sie, Grußformel, Satzlänge, Formalität, typische Wendungen**. Das LLM füllt nur die Abschnitte. Vorhersagbar im Prompt, für den Betreiber leicht editierbar.

### D-57: Per-Agent-Isolation, Klartext wie context.md (locked, Nutzer bestätigt 2026-07-17)
`style.md` liegt pro Agent in `/config/agents/<id>/` neben `.env` + `context.md` — **keine Sammeldateien**. Die Fernet-Verschlüsselung (Phase 5, D-48) gilt weiterhin nur für Secrets in der `.env`; `style.md` ist wie `context.md` Klartext-Markdown (kein Secret, muss editierbar bleiben). Das optionale Freitext-Feld (Stil-Beschreibung) wird ebenfalls pro Agent gespeichert (Ablageort: Claude's Discretion, z. B. eigene Datei oder Abschnitt).

### Claude's Discretion (ausdrücklich delegiert 2026-07-17)
- **Mail-Filter:** Was zählt als „echte Antwort-Mail" (In-Reply-To vorhanden, Mindestlänge, kein `Fwd:`/Weiterleitung, keine Ein-Wort-Antworten) — STY-04-Rahmen gilt
- **Mindestanzahl** verwertbarer Mails, unterhalb derer statt eines schlechten Profils ein Hinweis erscheint (sofern kein manueller Stil-Text vorliegt)
- **UI-Platzierung** des optionalen Freitext-Felds (im style-Fieldset vs. eigenes Fieldset) und des Re-Learn-Buttons
- **`ENABLE_STYLE_ADAPTION`-Verhalten** im Detail (wo der Schalter sitzt, was er bei `false` genau unterdrückt)
- Ablageort/Format der gespeicherten manuellen Stil-Angabe (muss Re-Learn überleben)
- Prompt-Design der Extraktion (externalisiert analog `prompts/classify.txt`/`generate.txt`, z. B. `prompts/style-extract.txt`) und der style-Injection-Block in `prompts/generate.txt` inkl. Hierarchie-Formulierung (context.md = WAS, style.md = nur WIE)
- Sent-Ordner-Erkennung: SPECIAL-USE `\Sent` + Provider-Config-Fallback (Mechanik von `detect_drafts_folder()` übernehmen)
- Längen-Deckel für style.md und Truncation der Mail-Bodies vor dem Extraktions-Call

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & Requirements
- `.planning/ROADMAP.md` — Phase-6-Sektion (Goal, 5 Success Criteria, Hauptrisiken)
- `.planning/REQUIREMENTS.md` — STY-01…STY-05

### Phase-5-Fundament (Erweiterungsbasis, MUSS vor Planung gelesen werden)
- `.planning/phases/05-multi-llm-multi-agent-verschl-sselung-v1-2/05-CONTEXT.md` — D-46…D-51 (Ein-Container-Modell, /config/agents/<id>/-Layout, Fernet, LLM-Adapter, Provider-Autodetect)
- `agent/src/llm.py` — LLM-Adapter `llm_call(...)` (Extraktion nutzt denselben Provider/Key/Modell-Mechanismus)
- `agent/src/config.py` — `imap_sent_folder` (`IMAP_SENT_FOLDER`, Provider-Fallback), `_resolve_model_defaults`, `load_agent_config`, `discover_agents`
- `webui/src/agents_io.py` — per-Agent-I/O-Muster (`read_context_md`/`write_context_md_atomic` → Vorlage für style.md-I/O)
- `webui/src/llm_seed.py` + `webui/src/llm_detect.py` — WebUI-seitiger LLM-Call-Pfad (Muster für den Extraktions-Call)
- `webui/src/main.py` — Routes inkl. `/context/generate` (Muster für den Re-Learn-Endpoint), Section-Save-Fluss `/save`

### Injection-Pfad im Agent
- `agent/src/generate.py` — Prompt-Bau aus `prompts/generate.txt` (bekommt den style-Block, STY-02)
- `agent/prompts/generate.txt` — bestehendes Prompt-Template (Hierarchie context > style dort verankern)
- `agent/src/pii.py` — `redact()` läuft über Gesendet-Mails VOR dem LLM-Call (STY-03/STY-04)
- `agent/src/imap_client.py` — `detect_drafts_folder()` (SPECIAL-USE-Mechanik als Vorlage für `\Sent`-Erkennung), `fetch_sender_history` (liest bereits aus dem Sent-Ordner)

### WebUI-Formular
- `webui/src/templates/index.html` — Fieldset-/Section-Save-Muster (style-Fieldset + Freitext-Feld + Re-Learn-Button einhängen)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `detect_drafts_folder()` (agent/src/imap_client.py:61): SPECIAL-USE-Erkennung (RFC 6154) ist 1:1 auf das `\Sent`-Flag übertragbar
- `pii.redact()`: direkt einsetzbar für die Gesendet-Mails vor dem Extraktions-Call
- `agents_io.read_context_md`/`write_context_md_atomic`: exaktes Muster für style.md-Read/Write pro Agent
- `llm_seed.py`-Pfad in der WebUI: Muster für „WebUI ruft LLM synchron und schreibt Ergebnis ins Formular"
- `config.imap_sent_folder` + `provider_config.py`: Sent-Ordner-Name je Provider existiert bereits (IONOS-Korrektur aus Phase 2 inklusive)

### Established Patterns
- Section-Save via HTMX (Phase 4): style-Fieldset speichert unabhängig vom Rest des Formulars
- Prompts externalisiert in `agent/prompts/*.txt` bzw. `webui/prompts/*.txt` — Extraktions-Prompt folgt dieser Konvention
- Zwei-Stufen-Bestätigung (Zero-Reset/Löschen): Vorlage für die Re-Learn-Bestätigung
- Fehler-Isolation pro Agent (Phase 5): fehlendes/leeres style.md darf den Draft-Pfad nie brechen

### Integration Points
- `generate.py` → Prompt-Template bekommt einen optionalen `{style_md}`-Block (leer = Verhalten wie heute, STY-02)
- `webui/src/main.py` → neuer Endpoint für Re-Learn + style-Section im `/save`-Fluss
- **Neu:** imap-tools wird WebUI-Dependency (`webui/` pyproject/requirements + Dockerfile) — die WebUI verbindet sich für die Extraktion selbst per IMAP

</code_context>

<specifics>
## Specific Ideas

- Freitext-Feld-Zweck wörtlich vom Nutzer: „man soll seinen schreibstil evtl im webui kurz erklären können oder ein beispiel einfügen können (nicht required, das feld kann man auch leer lassen, ist optional) […] vor allem für neue/leere postfächer gedacht"
- Nutzer-Bestätigung: jeder Agent bleibt vollständig isoliert („keine sammeldateien") — style.md, Freitext-Angabe und State strikt pro Agent
- A/B-Nachweis (SC2): Draft mit vs. ohne Stil-Profil unterscheidet sich sichtbar im Ton, nicht im Fach-Inhalt — Fixture-Fälle für die Hierarchie-Prüfung (lockerer Ton darf Beschwerde-Antworten nicht übersteuern)

</specifics>

<deferred>
## Deferred Ideas

- Periodische/automatische Stil-Aktualisierung (Learning-Loop) — vom Nutzer erfragt, bewusst NICHT in Phase 6 (Nicht-Ziel „kein Learning-Loop"); falls je gewünscht, eigene Phase mit expliziter Betreiber-Zustimmung
- Verschlüsselung von style.md — aktuell Klartext wie context.md; nur falls der Nutzer es später ausdrücklich will

</deferred>

---

*Phase: 06-schreibstil-adaption*
*Context gathered: 2026-07-17 via /gsd-discuss-phase 6 (interaktiv, 4 Entscheidungsrunden)*
