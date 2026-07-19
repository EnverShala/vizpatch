# Phase 10: Reversible Pseudonymisierung vor LLM-Übermittlung (Variante A) - Research

**Researched:** 2026-07-19
**Domain:** Reversible Regex-Pseudonymisierung (stdlib `re`) + Integration in 5 bestehende LLM-Call-Pfade (agent + webui)
**Confidence:** MEDIUM-HIGH (Codebase-Analyse HIGH, Regex-Muster MEDIUM/ASSUMED — brauchen Fixture-Härtung)

## Summary

Variante A erweitert `agent/src/pii.py` (heute: einseitige, nicht-nummerierte Redaction nur für IBAN/Kreditkarte) zu einem reversiblen Pseudonymisierungs-Baustein mit getypten, nummerierten Platzhaltern (`[EMAIL_1]`, `[TELEFON_1]`, `[IBAN_1]`, `[KARTE_1]`, `[URL_1]`, `[DATUM_1]`) und einem Mapping-Objekt, das ausschließlich im RAM lebt.

Die größte Erkenntnis dieser Recherche betrifft **nicht** die Regex-Muster (die sind Handwerk), sondern die **Integrationsarchitektur**: Der Code hat fünf faktisch unabhängige LLM-Call-Pfade (`classify.py`, `generate.py`, `webui/src/style_extract.py`, `webui/src/chat.py` (Streaming!), `webui/src/chat_tools.py` (agentische Tool-Schleife)), die **nicht** über einen einzigen zentralen Funktionsaufruf laufen — `agent/src/llm.py::llm_call()` ist ein reiner String-zu-String-Dispatcher, der zum Zeitpunkt des Aufrufs bereits den fertig zusammengesetzten Prompt (inkl. `context.md`) erhält. Ein Hook **innerhalb** von `llm_call()` selbst würde D-08 verletzen (`context.md` bleibt roh), weil an dieser Stelle Mail-Inhalt und Firmenwissen bereits zu einem String verschmolzen sind und nicht mehr unterscheidbar sind. Die Pseudonymisierung muss daher **pro Aufrufer** auf den einzelnen Feldern (`from`, `subject`, `body`, `conversation_history`, Chat-`message`/`history`/`mail_context`, Tool-Ergebnis-Bodies) ansetzen, bevor diese Felder in ein Prompt-Template eingesetzt werden — nicht auf dem fertigen Prompt-String.

Eine zweite wichtige Erkenntnis: `webui/src/chat.py::stream_chat()` liefert echte Token-Level-Chunks (Anthropic `messages.stream().text_stream`). Ein naives De-Anonymisieren pro Chunk ist **kaputt**, sobald ein Platzhalter wie `[IBAN_1]` über eine Chunk-Grenze zerrissen wird. Das braucht einen Puffer-Mechanismus. Im Gegensatz dazu liefert die agentische Tool-Schleife (`chat_tools.py::_run_anthropic_tool_loop`) **vollständige** Text-Blöcke pro Runde (non-streaming `messages.create()`), dort ist De-Anonymisieren pro Block unkritisch.

**Primäre Empfehlung:** Neue `Anonymizer`-Klasse in `pii.py` (agent + byte-identische webui-Kopie, analog zum bestehenden Drift-Guard-Muster von `crypto.py`/`llm.py`), instanziert **pro Request** direkt in `classify_email()`, `generate_draft_text()`, `extract_style()`, `run_agentic_chat()` — jeweils lokal, keine Signaturänderung an `llm.llm_call()` nötig. Reihenfolge der Regex-Anwendung: IBAN → Kreditkarte (Luhn) → E-Mail → URL → Datum → Telefon (spezifischste zuerst, damit bereits ersetzte Spans für nachfolgende, permissivere Muster unsichtbar sind).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Regex-Erkennung + Platzhalter-Ersetzung | Agent/Backend-Modul (`pii.py`) | — | Reine Text-Transformation, kein IO, gehört als Utility-Modul neben `classify.py`/`generate.py` |
| Mapping-Verwaltung (RAM, pro Request) | Agent/Backend (`pii.Anonymizer`-Instanz) | — | Lebenszeit ist an EINEN Verarbeitungsvorgang gebunden (ein Mail-Poll-Zyklus-Item, ein Chat-Turn) — kein Shared State, keine DB, kein Cache |
| Anonymisieren vor LLM-Call | Aufrufer-Ebene (`classify.py`/`generate.py`/`chat.py`/`chat_tools.py`/`style_extract.py`) | — | NICHT im Adapter (`llm.py`) selbst, weil dort context.md/Mail-Body bereits verschmolzen sind (siehe Summary) |
| De-Anonymisieren nach LLM-Antwort | Aufrufer-Ebene (dieselben Module) | Streaming-Puffer (`chat.py`) | Muss dieselbe Anonymizer-Instanz wie beim Anonymisieren verwenden (Tag↔Original-Zuordnung) |
| Feature-Flag-Auswertung | `config.py` (Agent) + `agents_io`/`read_env_raw` (WebUI) | — | Bestehendes Muster für `ENABLE_PII_REDACTION`/`ENABLE_STYLE_ADAPTION` 1:1 wiederverwendbar |
| Tool-Argument-De-Anonymisierung | `chat_tools.py` (vor `TOOL_HANDLERS[name](**input)`) | — | Nicht offensichtlich, aber kritisch: LLM-generierte Tool-Argumente (`neuer_text` bei `entwurf_bearbeiten`) können Platzhalter enthalten und MÜSSEN vor Ausführung aufgelöst werden, sonst landet `[IBAN_1]` wörtlich im Kunden-Draft |

## Standard Stack

### Core

Keine neue Abhängigkeit. Variante A ist bewusst stdlib-only (`re`, `dataclasses`/Klassen aus der Standardbibliothek). `agent/pyproject.toml`/`webui`-Requirements bleiben unverändert.

### Package Legitimacy Audit

**Nicht anwendbar** — diese Phase installiert keine externen Pakete (D-01: „Kein Presidio/spaCy, keine schwere Abhängigkeit"). Kein `slopcheck`-Lauf nötig.

## Bestandsaufnahme des existierenden Codes (VERIFIED — in dieser Session gelesen)

### `agent/src/pii.py` (heute)

```python
_IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")   # NUR ohne Leerzeichen
_CC_PATTERN = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")             # + Luhn-Check

def redact(text: str) -> str:
    text = _IBAN_PATTERN.sub("[IBAN_REDACTED]", text)   # EIN globaler Tag, nicht nummeriert, nicht reversibel
    text = _CC_PATTERN.sub(_redact_cc, text)
    return text
```

- `webui/src/pii.py` ist eine **byte-identische Kopie** (Drift-Guard `test_pii_sync.py`, SHA-256-Vergleich, existiert in `webui/tests/` — in `agent/tests/` fehlt aktuell die Gegenstück-Datei; das ist bereits heute so, kein Phase-10-Artefakt, aber sollte beim Anlegen der neuen `pii.py`-Version konsistent nachgezogen werden, falls der Guard bidirektional laufen soll).
- **Kein IBAN-Muster mit Leerzeichen** (`DE89 3704 0044 0532 0130 00` wird heute NICHT erkannt) — Lücke, die ANON-02 explizit schließen soll.
- Kein Telefon-, E-Mail-, URL-, Datum-Muster überhaupt.

### Wo `pii.redact()` heute aufgerufen wird — und wo NICHT (kritische Lücken)

| Ort | Was passiert heute | Lücke für ANON-03 |
|---|---|---|
| `agent/src/main.py:94` — `_process_one` | `body_for_llm = pii.redact(body) if config.enable_pii_redaction else body` — **NUR für den `generate`-Pfad** | `classify_email()` (Zeile 73-79) bekommt den **rohen, unredigierten** `body` — Klassifikation läuft heute komplett ungeschützt |
| `agent/src/generate.py::_build_history_block` | Baut den `{conversation_history}`-Block direkt aus `msg.text`/`msg.html_to_text()` der IMAP-History-Mails | **Keine Redaction überhaupt** — History-Mail-Bodies gehen roh in den Prompt |
| `webui/src/style_extract.py:150` | `bodies.append(pii.redact(body))` — aber **nach** dem Truncate (`body.strip()[:MAX_BODY_CHARS]`, Zeile 149) | Falsche Reihenfolge: ein IBAN/Telefon, das genau an der 800-Zeichen-Grenze liegt, wird ggf. schon vor der Redaction zerschnitten |
| `webui/src/chat.py` (`build_chat_prompt`, `stream_chat`) | **Kein `pii`-Import, keine Redaction überhaupt** | Chat-Message, History, `mail_context` (Betreff/Absender/Body der geöffneten Mail, OUT-03) gehen komplett roh an den LLM |
| `webui/src/chat_tools.py` (`mails_suchen`, `mail_lesen`, `entwuerfe_auflisten`, `entwurf_lesen`) | `body = pii.redact(_mail_body(msg))[:MAX_TOOL_RESULT_BODY_CHARS]` — Redact **vor** Truncate (richtige Reihenfolge!) | Nur IBAN/CC erfasst, nicht reversibel, und die Tool-Loop selbst (`_run_anthropic_tool_loop`) hat keinerlei PII-Behandlung für den `message`/`history`/`mail_context`-Input oder für die finalen Text-Blöcke |

**Wichtigster Einzelfund:** Die Klassifikation läuft heute **komplett ohne** PII-Schutz — das ist kein neues Feature, sondern eine bestehende Lücke, die ANON-03 (Klassifikation ausdrücklich als Pfad genannt) schließen MUSS.

### `agent/src/llm.py` / `webui/src/llm.py` — reiner Dispatcher (VERIFIED)

```python
def llm_call(provider, api_key, model, prompt, max_tokens, temperature) -> str:
    fn = _DISPATCH.get((provider or "").strip().lower(), _call_anthropic)
    text = fn(prompt, model, max_tokens, temperature, api_key)
    ...
    return text
```

Nimmt einen **fertigen Prompt-String** entgegen, kein Wissen über Prompt-Struktur. Byte-identisch mit `webui/src/llm.py` (Drift-Guard `test_llm_sync.py`, SHA-256). **Empfehlung: NICHT anfassen** (siehe Architecture Patterns unten — Begründung).

`webui/src/chat.py::stream_chat()` ist ein **komplett separates** Streaming-Pendant (eigener `_STREAM_DISPATCH`, nutzt `client.messages.stream().text_stream` bei Anthropic) — kein gemeinsamer Code-Pfad mit `llm.py`. `chat_tools.py::_run_anthropic_tool_loop` nutzt wiederum einen **dritten**, eigenständigen Call (`client.messages.create(tools=..., messages=...)`, non-streaming, mit Tool-Use-Schleife). Diese drei Call-Mechanismen teilen sich **keinen** gemeinsamen Wrapper-Punkt im heutigen Code — jede Integration muss einzeln erfolgen.

### `agent/src/classify.py` / `agent/src/generate.py` (VERIFIED)

- `classify.py` importiert `pii` **nicht**. Baut Prompt aus `from_address`, `subject`, `body_snippet` (Body wird zuerst auf 2000 Zeichen getruncated, DANACH formatiert — Truncate passiert VOR jeglicher Pseudonymisierung, muss umgedreht werden).
- `generate.py` importiert `pii` **nicht** (bekommt `body_for_llm` bereits redigiert von `main.py` übergeben, aber `conversation_history`/`from`/`subject` NICHT). Baut `{conversation_history}` aus rohen `MailMessage`-Objekten intern (`_build_history_block`), je Nachricht auf 800 Zeichen getruncated — auch hier Truncate-vor-Redact-Reihenfolge, falsch herum.

### `agent/src/config.py` (VERIFIED)

- `enable_pii_redaction: bool` existiert bereits (env `ENABLE_PII_REDACTION`, Default `true`), wird NUR in `main.py` gelesen, nirgends sonst.
- Etabliertes Muster für einen neuen Flag: analog zu `enable_style_adaption` (Zeile 134/222) — einfaches `bool`-Feld im `Config`-Dataclass mit Default `= True` (für Rückwärtskompatibilität bestehender `Config(...)`-Testkonstruktionen), gelesen via `(env.get("X") or "true").lower() == "true"`.
- **Namenskollision zu klären** (siehe Offene Frage unten): D-07 schlägt `ENABLE_PSEUDONYM` vor („o.ä." — laut CONTEXT.md nicht final benannt), es existiert aber bereits `ENABLE_PII_REDACTION` mit überlappender Bedeutung.

## Architecture Patterns

### System-Architektur: Wo die Pseudonymisierung ansetzt

```
                    ┌─────────────────────────────────────────────┐
                    │  Aufrufer-Ebene (JEDER LLM-Pfad einzeln)     │
                    │  classify.py / generate.py / style_extract.py│
                    │  / chat.py / chat_tools.py                   │
                    │                                               │
  Mail-Body,        │  1. anonymizer = pii.Anonymizer()            │
  Betreff,          │  2. feld_anon = anonymizer.anonymize(feld)   │───┐
  Absender,    ─────▶     (NUR Mail-/Chat-Felder — NICHT context.md/│   │ pseudonymisierter
  History,          │      style.md!)                               │   │ Prompt-String
  Chat-Message      │  3. prompt = template.format(feld_anon, ...) │   │
                    │  4. text = llm.llm_call(prompt=prompt, ...)  │◀──┘
                    │        ODER chat.stream_chat(...)            │
                    │        ODER client.messages.create(tools=..)│
                    │  5. text_klar = anonymizer.deanonymize(text) │───▶ Draft/Chat-Antwort
                    └─────────────────────────────────────────────┘     mit ECHTEN Werten
                                        │
                                        │ (Schritt 2/5 NIE hier:)
                    ┌───────────────────▼───────────────────────┐
                    │  agent/src/llm.py::llm_call(prompt) -> str │  ◀── UNVERÄNDERT.
                    │  webui/src/llm.py (byte-identische Kopie)  │      Reiner Dispatcher,
                    │  sieht NUR den fertigen String — kann      │      sieht bereits
                    │  Mail-Inhalt nicht von context.md           │      context.md+Mail
                    │  unterscheiden (D-08-Konflikt, siehe unten)│      verschmolzen
                    └─────────────────────────────────────────────┘
```

**Warum nicht in `llm.py` selbst?** D-06 will „zentral im Phase-5-LLM-Adapter, greift für alle Pfade". Wörtlich genommen (Code-Änderung in `llm_call()`) würde das bedeuten: `llm_call(prompt)` bekommt den fertigen String (in dem `context.md` bereits per `.format()` eingesetzt ist) und müsste dort blind Regex drüberlaufen lassen. Das verletzt D-08 direkt — ein Firmen-Telefon, eine Firmen-IBAN in den Zahlungshinweisen oder ein Datum in den Öffnungszeiten (`context.md`) würde ebenfalls maskiert, obwohl es laut D-08 roh bleiben soll. Es gibt an dieser Stelle im Code keine Möglichkeit mehr, „Mail-Inhalt" von „context.md-Inhalt" zu unterscheiden, weil `generate.py` beides bereits zu EINEM String zusammengesetzt hat, bevor `llm_call()` ihn sieht.

**Empfehlung (Realisierung der D-06-Absicht, nicht ihr Wortlaut):** „Zentral" heißt: **eine** gemeinsame `pii.py`-Engine (kein duplizierter Regex-Code), aufgerufen von **jedem** der fünf Pfade an der Stelle, wo die einzelnen Felder noch getrennt vorliegen — nicht am Ende in `llm.py`. `llm.py`/`webui/src/llm.py` bleiben dadurch **unverändert** — ein Nebeneffekt: der Byte-Identität-Drift-Guard (`test_llm_sync.py`) bleibt trivial erfüllt, ohne dass man ihn anfassen muss.

Dieser Punkt sollte dem Planner/Nutzer explizit als Abweichung von der wörtlichen D-06-Formulierung transparent gemacht werden (Realisierung der Absicht „zentral + alle Pfade", aber mechanisch pro Aufrufer statt im Adapter selbst).

### Empfohlenes Modul-Design: `pii.py` — `Anonymizer`-Klasse

```python
# agent/src/pii.py (+ byte-identische Kopie webui/src/pii.py)
from __future__ import annotations
import re

# Reihenfolge ist SEMANTIK, nicht Zufall — siehe "Overlap-Handling" unten.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("IBAN",    re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}\b")),
    ("KARTE",   _CC_PATTERN),   # bestehendes Muster + Luhn-Callback wiederverwenden
    ("EMAIL",   re.compile(r"\b[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("URL",     re.compile(r"\b(?:https?://|www\.)[^\s<>\"']+")),
    ("DATUM",   re.compile(r"\b(0?[1-9]|[12]\d|3[01])[.\/](0?[1-9]|1[0-2])[.\/](\d{4}|\d{2})\b")),
    ("TELEFON", re.compile(
        r"\b(?:\+49[ /-]?|0049[ /-]?|0)"
        r"(?:\(?\d{2,5}\)?[ /-]?)"
        r"\d{3,4}(?:[ /-]?\d{2,4}){0,3}\b"
    )),
]

class Anonymizer:
    """Pro Request instanziieren — NIE über Requests hinweg wiederverwenden/persistieren."""

    def __init__(self) -> None:
        self._tag_to_original: dict[str, str] = {}
        self._original_to_tag: dict[str, str] = {}
        self._counters: dict[str, int] = {}

    def _tag_for(self, entity_type: str, original: str) -> str:
        if original in self._original_to_tag:
            return self._original_to_tag[original]
        n = self._counters.get(entity_type, 0) + 1
        self._counters[entity_type] = n
        tag = f"[{entity_type}_{n}]"
        self._original_to_tag[original] = tag
        self._tag_to_original[tag] = original
        return tag

    def anonymize(self, text: str) -> str:
        if not text:
            return text
        for entity_type, pattern in _PATTERNS:
            def _sub(m: re.Match, et=entity_type) -> str:
                # KARTE braucht weiterhin den Luhn-Gate (nur gültige Kartennummern ersetzen)
                if et == "KARTE" and not _luhn_check(re.sub(r"\D", "", m.group(0))):
                    return m.group(0)
                return self._tag_for(et, m.group(0))
            text = pattern.sub(_sub, text)
        return text

    def deanonymize(self, text: str) -> str:
        if not text:
            return text
        # Reihenfolge irrelevant für Korrektheit (siehe Pitfall "Tag-Substring-Kollision"),
        # aber längste zuerst ist defensiv güns­tig bei zukünftigen Tag-Formaten.
        for tag, original in sorted(self._tag_to_original.items(), key=lambda kv: -len(kv[0])):
            text = text.replace(tag, original)
        return text
```

Aufrufer-Muster (Beispiel `generate.py`, analog für die anderen vier Pfade):

```python
def generate_draft_text(from_address, subject, body, config, ..., conversation_history=None):
    anonymizer = pii.Anonymizer()
    if config.enable_pseudonym:
        from_address = anonymizer.anonymize(from_address)
        subject = anonymizer.anonymize(subject)
        body = anonymizer.anonymize(body)
        # _build_history_block MUSS dieselbe anonymizer-Instanz nutzen (Konsistenz:
        # gleicher Wert im Thread-Verlauf UND in der aktuellen Mail -> gleicher Tag)
        history_block = _build_history_block(conversation_history or [], anonymizer)
    else:
        history_block = _build_history_block(conversation_history or [], None)

    # context_md_full / style_md werden NICHT durch anonymizer.anonymize() geschickt (D-08)
    prompt = config.prompt_generate.format(context_md_full=config.context_md, ...)
    draft = llm.llm_call(..., prompt=prompt, ...)
    if config.enable_pseudonym:
        draft = anonymizer.deanonymize(draft)
    return draft.strip()
```

### Overlap-/Präzedenz-Handling (Recherche-Fokus #2)

**Kernprinzip: spezifischste/strukturierteste Muster zuerst, jeweils per `.sub()` sofort ersetzen, bevor das nächste (permissivere) Muster läuft.** Sobald ein Span ersetzt ist, steht dort nur noch `[TYP_N]` — ein rein alphabetischer Tag mit Unterstrich und Ziffer, der von KEINEM der Ziffernketten-orientierten Muster (Telefon, Datum, Kreditkarte) erneut matchen kann. Dadurch entsteht Sicherheit gegen Doppel-Matches **ohne** dass Positions-Tracking (Interval-Merging) nötig ist — die sequentielle `.sub()`-Kette ist bereits ausreichend, WENN die Reihenfolge stimmt:

1. **IBAN** zuerst (strukturell: 2 Buchstaben + 2 Ziffern + alphanumerisch — am eindeutigsten identifizierbar, muss vor Kreditkarte laufen, sonst könnte eine generische 16-20-stellige Ziffernfolge innerhalb einer IBAN fälschlich als Kartennummer geluhnt werden — praktisch unwahrscheinlich, aber IBAN zuerst ist trotzdem korrekt, weil IBANs Buchstaben enthalten und Kreditkarten nicht, es besteht also selten echte Überlappung; Reihenfolge trotzdem beibehalten als Sicherheitsnetz).
2. **Kreditkarte** (Luhn-validiert) — muss vor Telefon laufen: eine 16-stellige Kartennummer mit Leerzeichen sieht einer Telefonnummer mit Ländervorwahl ähnlich; Luhn-Check ist die einzige verlässliche Unterscheidung, muss also VOR dem permissiveren Telefon-Muster greifen.
3. **E-Mail** (enthält `@`, keine Überlappung mit den anderen Typen, kann früh laufen).
4. **URL** (enthält `://` oder `www.`, keine Ziffernketten-Ambiguität, aber: sollte vor Datum laufen, falls eine URL ein Datum als Pfad-Segment enthält, z. B. `https://beispiel.de/2024/07/19/artikel` — sonst würde das Datumsmuster einen Teil der URL herausreißen und die URL kaputt/unvollständig maskieren).
5. **Datum** vor **Telefon**: ein Datum wie `07.12.2024` besteht aus durch Punkte getrennten Zifferngruppen — das breite Telefonmuster (das auch `/`, `-`, `.` als Trenner zulässt, siehe unten) würde sonst Teile eines Datums als Telefonnummer fehlinterpretieren.
6. **Telefon zuletzt** — das mit Abstand permissivste Muster (variable Ländervorwahl, variable Trennzeichen). Läuft es zuerst, reißt es IBANs/Daten/URLs mit Ziffernanteilen an.

**Wichtiger Grenzfall, den Fixtures abdecken müssen:** Eine deutsche Rechnungs-/Kundennummer (rein numerisch, kein Ländercode) kann versehentlich als Telefonnummer erkannt werden (False Positive) — das ist bei Variante A ein akzeptiertes Restrisiko (führt zu Über-Maskierung, nicht zu Daten-Leck — sicherheitshalber vertretbar gemäß D-09 „Rigorosität auf der Input-Seite"), sollte aber in den Fixtures dokumentiert werden, damit es nicht als Bug missverstanden wird.

### Reversibles Mapping-Design (Recherche-Fokus #3)

- **Stabile Nummerierung pro Typ:** ein `dict[str, int]`-Zähler je Entity-Typ (`EMAIL`, `TELEFON`, `IBAN`, `KARTE`, `URL`, `DATUM`), hochgezählt bei jedem NEUEN Wert.
- **Gleicher Wert → gleicher Tag:** Reverse-Lookup `dict[str, str]` (Original-String → Tag) VOR dem Hochzählen prüfen (siehe `_tag_for` oben). **Bekannte Einschränkung:** der Abgleich erfolgt auf dem exakten String-Match des erkannten Rohtexts (inkl. Formatierung) — `+49 30 1234` und `030-1234` gelten als unterschiedliche „Originale" und bekommen unterschiedliche Tags, selbst wenn sie dieselbe Nummer meinen. Für Variante A ist das eine akzeptable, dokumentierte Vereinfachung (kein Normalisierungs-Aufwand für Telefonformate); bei IBAN würde sich eine Whitespace-Normalisierung für den Reverse-Lookup lohnen (IBANs erscheinen oft mehrfach im selben Thread, mal mit, mal ohne Leerzeichen) — als Claude's-Discretion-Verfeinerung optional, kein Blocker.
- **De-Anonymisierung: `str.replace()`, kein Regex.** Das Tag-Format `[TYP_N]` mit **direkt anschließender schließender Klammer** ist entscheidend: `"[IBAN_1]"` ist **kein** Substring von `"[IBAN_10]"` (Zeichen 8 unterscheidet sich: `]` vs. `0`) — die schließende Klammer verhindert Substring-Kollisionen bei zweistelligen Zählern unabhängig von der Ersetzungsreihenfolge. Damit ist die Reihenfolge der `.replace()`-Aufrufe in `deanonymize()` **für Korrektheit irrelevant** (die im Codebeispiel gezeigte Sortierung nach Länge ist defensive Zusatzsicherheit für den Fall künftiger Tag-Format-Änderungen, keine Notwendigkeit für das aktuelle Format).
- **Robustheit bei leichter LLM-Umformung des Tags** (D-09: Pragmatismus auf der Output-Seite): kein Blocker-Aufwand, ABER ein günstiger Zusatz-Sicherheitsnetz ist ein Nachlauf-Regex `\[?(EMAIL|TELEFON|IBAN|KARTE|URL|DATUM)_\d+\]?`, der nach `deanonymize()` auf Reste geprüft wird und bei Treffer NUR eine `logger.warning("possible_placeholder_leak", ...)` auslöst (kein Crash, kein Blockieren des Drafts — der menschliche Review fängt es ab, D-09). Dieses Warn-Signal ist billig zu bauen und gibt operativ sichtbares Feedback, falls die Erkennungsrate in der Praxis schlechter ist als angenommen.

### Streaming-sicheres De-Anonymisieren (`webui/src/chat.py::stream_chat`)

**Kritischer Pitfall, unbedingt einplanen:** `stream_chat()` yielded Text in **beliebigen Chunk-Grenzen** (Anthropic SDK entscheidet die Chunk-Größe, nicht die Anwendung). Ein naives `chunk = anonymizer.deanonymize(chunk)` pro Chunk ist korrekt, SOLANGE kein Tag über zwei Chunks gerissen wird — das ist aber nicht garantiert und wird in der Praxis vorkommen (z. B. `"...Ihre IBAN ist [IBAN_"` als ein Chunk, `"1]"` als nächster).

**Empfohlene Lösung — Puffer mit Klammer-Erkennung:**

```python
def deanonymize_stream(chunks, anonymizer):
    """Streaming-sicherer Wrapper: hält Text nach einer offenen '[' zurück,
    bis entweder ']' folgt (Tag komplett -> deanonymize + yield) oder ein
    Zeichen kommt, das in einem Tag nicht vorkommen kann (z.B. Leerzeichen
    nach einer gewissen Maximallänge -> false positive, direkt yielden)."""
    buffer = ""
    for chunk in chunks:
        buffer += chunk
        # Solange kein offenes "[" ohne schließendes "]" am Ende hängt: alles ausliefern.
        last_open = buffer.rfind("[")
        last_close = buffer.rfind("]")
        if last_open > last_close:
            # potenzieller unvollständiger Tag am Ende -> zurückhalten
            safe_part, buffer = buffer[:last_open], buffer[last_open:]
            if safe_part:
                yield anonymizer.deanonymize(safe_part)
            # Sicherheitsnetz: nie unbegrenzt puffern (defekter/kein Tag) -> ab
            # ~20 Zeichen Pufferlänge ohne schließende Klammer einfach ausliefern
            if len(buffer) > 20:
                yield anonymizer.deanonymize(buffer)
                buffer = ""
        else:
            yield anonymizer.deanonymize(buffer)
            buffer = ""
    if buffer:
        yield anonymizer.deanonymize(buffer)
```

Dieser Wrapper muss um `chat.stream_chat(...)` in `_run_fallback_chat()` (chat_tools.py) gelegt werden. Die **agentische Tool-Schleife braucht das NICHT** (siehe unten), weil sie nicht Token-weise streamt.

### Integration in `chat_tools.py` — die agentische Tool-Schleife (Recherche-Fokus #4, wichtigster Einzelfund)

`_run_anthropic_tool_loop()` (VERIFIED, `webui/src/chat_tools.py` Zeile 1413-1488) läuft über bis zu `MAX_TOOL_ROUNDS=5` Runden mit `client.messages.create(tools=TOOL_SCHEMAS, ...)` (NICHT gestreamt — jede Runde liefert vollständige `content`-Blöcke). Drei separate Integrationspunkte, alle mit **derselben** `Anonymizer`-Instanz (eine Instanz pro Chat-Turn = pro Aufruf von `run_agentic_chat()`, über alle Runden hinweg):

1. **Initiale Nachricht + History + Mail-Kontext** (`_build_initial_messages`): `message`, jede `history`-Turn-`content`, und `mail_context["subject"/"sender"/"body"]` müssen VOR dem Bau der Anthropic-Message-Liste anonymisiert werden. Wichtig: `history` kann bereits **echte** PII aus vorherigen (de-anonymisierten) Antworten enthalten (Browser-seitiger Chat-Verlauf, CHAT-01 — kein Server-State) — diese muss in der NEUEN Runde erneut anonymisiert werden (neue Anonymizer-Instanz pro Aufruf, das ist auch DESHALB richtig so).
2. **Tool-Ergebnisse** (`mails_suchen`/`mail_lesen`/`entwuerfe_auflisten`/`entwurf_lesen` in `chat_tools.py`): ersetzen die heutigen `pii.redact(...)`-Aufrufe 1:1 durch `anonymizer.anonymize(...)` — WICHTIG: dieselbe Anonymizer-Instanz wie Punkt 1 und 3 (nicht pro Tool-Aufruf neu instanziieren!), damit ein in Runde 2 gelesener und in Runde 4 vom LLM zitierter Wert denselben Tag behält. Diese Tool-Ergebnisse werden NIE direkt an den Menschen ausgeliefert (SSE liefert nur `{"type":"tool","label":"🔧 name…"}`, kein Payload) — die reine Umkehrbarkeit ist hier nicht für Anzeige nötig, sondern damit Schritt 3 funktioniert.
3. **Text-Blöcke UND Tool-Input-Argumente, die an den Menschen bzw. an Handler gehen** (kritischster Punkt, leicht zu übersehen):
   - Jeder `block.text` (assistant-Text, wird per SSE an den Betreiber gestreamt) MUSS vor dem `yield` de-anonymisiert werden — sonst sieht der Betreiber `[IBAN_1]` statt der echten IBAN im Chat.
   - Jedes `block.input` eines `tool_use`-Blocks, BEVOR es an `TOOL_HANDLERS[block.name](agent_id, **block.input)` geht, MUSS de-anonymisiert werden. Beispiel: Das LLM entscheidet basierend auf pseudonymisiertem Kontext, `entwurf_bearbeiten(uid=..., neuer_text="Ihre IBAN lautet [IBAN_1].")` aufzurufen — wird dieser Text NICHT de-anonymisiert, bevor er ins RFC-5322-Draft geschrieben wird, landet der wörtliche Platzhalter-String im tatsächlichen Kunden-Entwurf. Das ist ein direkter ANON-04-Verstoß („kein Platzhalter-Leck") und der am leichtesten zu übersehende Integrationspunkt in der gesamten Phase.

### Integration in `style_extract.py` (Recherche-Fokus #4/#5)

`extract_style()` ruft heute `pii.redact()` NACH dem Truncate auf (Reihenfolge-Bug, siehe Bestandsaufnahme). Empfehlung: gleiches Anonymizer-Pattern wie generate.py — EINE Anonymizer-Instanz für alle gesammelten `bodies`, anonymisieren VOR dem `[:MAX_BODY_CHARS]`-Schnitt, danach schneiden. De-Anonymisierung des LLM-Outputs (`style.md`) ist **strenggenommen nicht nötig** (ein Stilprofil braucht keine echten IBANs/Telefonnummern), aber aus Konsistenzgründen (D-05 „Draft/Chat-Antwort enthält die echten Daten" als durchgängiges Prinzip, keine Sonderfälle) und weil es billig ist, wird empfohlen, `anonymizer.deanonymize()` trotzdem einheitlich auf den Rückgabewert anzuwenden — verhindert außerdem, dass ein vom LLM wörtlich zitierter Platzhalter (`"Antworten Sie höflich, z.B. wie in [EMAIL_1]"`) unsinnig in `style.md` landet.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Robuste Named-Entity-Erkennung für Personen/Firmen/Orte | Eigene Heuristik/Regex für „ist das ein Name?" | ANON-06 (spaCy `de_core_news_sm`), separates Inkrement | Regex kann das strukturell nicht (kein Muster für Eigennamen) — bewusst ausgelagert, siehe CONTEXT.md D-Begründung |
| Kryptographisch sicheres Mapping-Storage | Persistentes verschlüsseltes Mapping-File | Reines In-Memory-`dict`, nie serialisiert | D-04: Mapping darf den Server nie in irgendeiner Form (Platte, Log) verlassen — Persistenz wäre ein Rückschritt gegenüber der Anforderung |
| Realistische Fake-Werte statt Tags (Faker-artig) | `faker`-Bibliothek für plausible Fake-IBANs/Namen | Einfache getypte Tags `[IBAN_1]` | In CONTEXT.md bereits explizit erwogen und verworfen (erzwingt gespeichertes Mapping + Verwechslungsrisiko) |

**Key insight:** Der eigentliche Schwierigkeitsgrad dieser Phase liegt nicht in der Regex-Technik, sondern darin, **fünf unabhängige Call-Pfade korrekt und vollständig** zu erfassen, ohne den bestehenden `context.md`-Exemption-Vertrag (D-08) zu brechen und ohne die byte-identischen Drift-Guard-Zwillinge (`llm.py`/`pii.py` agent↔webui) zu verletzen.

## Common Pitfalls

### Pitfall 1: Truncate-vor-Redact statt Redact-vor-Truncate
**Was schiefgeht:** Ein Mail-Body wird zuerst auf N Zeichen gekürzt, DANACH pseudonymisiert — ein PII-Wert, der genau an der Kürzungsgrenze liegt, wird nur teilweise erkannt oder komplett verpasst.
**Warum es passiert:** Bestehender Code (`style_extract.py` Zeile 149-150, `classify.py::_extract_body_snippet`, `generate.py::_truncate_body`) truncatet zuerst aus Kosten-/Prompt-Größen-Gründen, PII-Behandlung kam historisch später dazu.
**Wie vermeiden:** Reihenfolge in ALLEN fünf Pfaden umdrehen: erst `anonymizer.anonymize(text)`, dann Truncate auf die bestehenden Zeichen-Limits (`MAX_BODY_CHARS`, `_HISTORY_BODY_MAX_CHARS`, `MAX_TOOL_RESULT_BODY_CHARS` — letzteres in `chat_tools.py` ist bereits korrekt und dient als Referenzimplementierung).
**Warnsignale:** Test-Fixture mit einem Wert exakt an der Zeichen-Grenze, der nur teilweise durch den Regex erfasst wird.

### Pitfall 2: Streaming-Chunk zerreißt einen Platzhalter
**Was schiefgeht:** `[IBAN_1]` wird über zwei SSE-Chunks verteilt ausgeliefert; ein pro-Chunk-`deanonymize()` findet den Tag nicht (unvollständiger String) und liefert den rohen Platzhalter-Fragment-Text an den Browser.
**Warum es passiert:** Anthropic-Streaming-API liefert Text in variablen Chunk-Größen, die nicht an Tag-Grenzen ausgerichtet sind.
**Wie vermeiden:** Puffer-Wrapper `deanonymize_stream()` (siehe Code-Beispiel oben) um `chat.stream_chat()`.
**Warnsignale:** E2E-Test mit künstlich sehr kleiner (1-Zeichen-)Chunk-Größe im gemockten Stream-Iterator deckt das zuverlässig auf.

### Pitfall 3: Tool-Argumente nicht de-anonymisiert vor Handler-Aufruf
**Was schiefgeht:** `entwurf_bearbeiten`/`entwurf_erstellen` bekommen vom LLM einen `neuer_text`/`text`-Parameter, der noch Platzhalter enthält — der tatsächliche Kunden-Draft enthält dann `[IBAN_1]` statt der echten IBAN.
**Warum es passiert:** Leicht zu übersehen, weil die Tool-Loop-Architektur (D-73..D-80, Phase 9) VOR Phase 10 entstand und keinerlei PII-Bewusstsein für Tool-EINGABEN hatte (nur für Tool-AUSGABEN via `pii.redact()`).
**Wie vermeiden:** In `_run_anthropic_tool_loop`, direkt vor `handler(agent_id, **(block.input or {}))`: alle String-Werte in `block.input` durch `anonymizer.deanonymize(...)` schicken.
**Warnsignale:** Fixture-Test, der einen `entwurf_bearbeiten`-Tool-Call mit einem `[IBAN_1]`-Platzhalter im `neuer_text`-Argument simuliert und prüft, dass der tatsächlich per IMAP APPENDete Draft-Bytes-Inhalt die echte IBAN enthält.

### Pitfall 4: context.md wird versehentlich mitmaskiert
**Was schiefgeht:** Ein Firmen-Telefon, eine Firmen-IBAN (Zahlungshinweise) oder ein Datum (Öffnungszeiten) in `context.md`/`style.md` wird durch einen zu weit gefassten Integrationspunkt (z. B. Anonymisieren des GESAMTEN fertigen Prompt-Strings statt einzelner Felder) ebenfalls durch einen Platzhalter ersetzt — Draft-Qualität bricht (D-08-Verstoß).
**Warum es passiert:** Der naheliegendste, aber falsche Integrationspunkt ist „einfach den fertigen Prompt vor `llm_call()` durch die Regex schicken" — das trifft `context_md_full`/`style_md` gleich mit.
**Wie vermeiden:** Anonymisierung IMMER auf den Einzelfeldern VOR `.format()`, NIE auf dem fertigen Prompt-String (siehe Architecture Patterns).
**Warnsignale:** Regressionstest mit einer `context.md`-Fixture, die bewusst eine Telefonnummer/IBAN/ein Datum enthält (z. B. Öffnungszeiten + Kontonummer für Vorkasse) — Draft-Prompt darf dort KEINEN Platzhalter enthalten.

### Pitfall 5: Klassifikation bleibt ungeschützt
**Was schiefgeht:** `classify_email()` bekommt weiterhin den rohen Body (heutiger Zustand), Pseudonymisierung wird nur für den Draft-Pfad nachgerüstet — ANON-03 wird nur teilweise erfüllt.
**Warum es passiert:** `main.py` unterscheidet heute bewusst zwischen dem an `classify_email` übergebenen `body` (roh) und dem an `generate_draft_text` übergebenen `body_for_llm` (redigiert) — ein leicht zu übersehendes bestehendes Asymmetrie-Muster.
**Wie vermeiden:** `classify.py` bekommt seine EIGENE (oder eine von `main.py` geteilte) Anonymizer-Anwendung auf `from_address`/`subject`/`body`, unabhängig vom Draft-Pfad.
**Warnsignale:** Unit-Test, der `classify_email()` isoliert aufruft und prüft, dass der an `llm.llm_call` übergebene `prompt`-Kwarg keine Rohwerte aus einer PII-haltigen Test-Mail enthält.

### Pitfall 6: Tag-Format mit Substring-Kollision (vermieden, aber dokumentationswürdig)
**Was schiefgeht (hypothetisch, falls Tag-Format je geändert wird):** Ein Tag-Format OHNE eindeutigen Abschluss-Delimiter (z. B. `IBAN_1` ohne Klammern) würde bei `str.replace("IBAN_1", ...)` versehentlich auch den Anfang von `IBAN_10` treffen.
**Warum aktuell kein Problem:** Das in D-02/D-03 festgelegte Format `[TYP_N]` MIT schließender Klammer verhindert das strukturell (siehe Reversibles-Mapping-Abschnitt).
**Wie vermeiden:** Tag-Format NICHT ohne die schließende Klammer verwenden; falls das Format je geändert wird, erneut auf Substring-Sicherheit prüfen.
**Warnsignale:** Test mit ≥10 Werten desselben Typs in einem Text (erzeugt zweistellige Tag-Nummern), der De-Anonymisierung auf Korrektheit prüft.

## Code Examples

### Konkrete Regex-Vorschläge (Recherche-Fokus #1 — [ASSUMED], brauchen Fixture-Härtung)

```python
import re

# --- IBAN: DE + generisch EU, MIT optionalen Leerzeichen alle 4 Zeichen ---
IBAN_PATTERN = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}\b")
# Deckt ab: "DE89370400440532013000" UND "DE89 3704 0044 0532 0130 00"
# Bekannte Lücke: IBANs mit uneinheitlicher Gruppierung (z.B. 3-2-4-Schema
# statt durchgehend 4er-Gruppen) werden ggf. nicht vollständig erfasst —
# in Fixtures mit realistischen (auch unsauber kopierten) Kunden-IBANs testen.

# --- Kreditkarte: bestehendes Muster + Luhn-Check unverändert übernehmen ---
CC_PATTERN = re.compile(r"\b(?:\d[ -]?){12,18}\d\b")
# (Luhn-Check-Funktion aus heutigem pii.py 1:1 wiederverwenden)

# --- E-Mail ---
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
)

# --- URL ---
URL_PATTERN = re.compile(r"\b(?:https?://|www\.)[^\s<>\"']+")

# --- Deutsches Datum: TT.MM.JJJJ / TT.MM.JJ / TT/MM/JJJJ ---
DATE_PATTERN = re.compile(
    r"\b(0?[1-9]|[12]\d|3[01])[.\/](0?[1-9]|1[0-2])[.\/](\d{4}|\d{2})\b"
)

# --- Deutsche Telefonnummer: Festnetz + Mobil, +49/0049/0, diverse Trenner ---
PHONE_PATTERN = re.compile(
    r"\b(?:\+49[ /-]?|0049[ /-]?|0)"
    r"(?:\(?\d{2,5}\)?[ /-]?)"
    r"\d{3,4}(?:[ /-]?\d{2,4}){0,3}\b"
)
# Bekanntes Risiko: False Positives auf lange, ungegliederte Ziffernketten
# (Rechnungs-/Kundennummern) — akzeptiertes Restrisiko (Über-Maskierung,
# kein Daten-Leck). MUSS gegen echte Fixtures (07152 123456, +49 30 1234
# 5678, 0711-123456, (07152) 123456 etc.) kalibriert werden.
```

**Konfidenz dieser Muster: [ASSUMED]** — es handelt sich um Trainingswissen-basierte, gängige Regex-Ansätze für deutsche PII-Formate, NICHT gegen eine externe Quelle (Context7/offizielle Doku) verifiziert, weil es sich um reine stdlib-Regex-Technik ohne Bibliotheks-API handelt, die man nachschlagen könnte. Sie MÜSSEN gegen die in Recherche-Fokus #6 geforderten Fixtures gehärtet werden, bevor sie als „fertig" gelten.

### Test-/Fixture-Strategie (Recherche-Fokus #6)

Bestehendes Testmuster (VERIFIED, `agent/tests/test_pii.py`, `agent/tests/conftest.py`) ist ein einfaches pytest-Modul ohne externe Fixtures — direkt erweiterbar:

```python
# agent/tests/test_pii.py — Erweiterung, ergänzt bestehende Tests
from src.pii import Anonymizer

def test_anonymize_iban_with_spaces_reversible():
    a = Anonymizer()
    text = "IBAN: DE89 3704 0044 0532 0130 00"
    anon = a.anonymize(text)
    assert "DE89 3704 0044 0532 0130 00" not in anon
    assert "[IBAN_1]" in anon
    assert a.deanonymize(anon) == text

def test_same_value_gets_same_tag():
    a = Anonymizer()
    text = "Kontakt: max@kunde.de, nochmal: max@kunde.de"
    anon = a.anonymize(text)
    assert anon.count("[EMAIL_1]") == 2
    assert "[EMAIL_2]" not in anon

def test_different_values_get_incrementing_tags():
    a = Anonymizer()
    anon = a.anonymize("max@kunde.de und peter@kunde.de")
    assert "[EMAIL_1]" in anon and "[EMAIL_2]" in anon

def test_iban_not_split_into_phone_or_date():
    a = Anonymizer()
    anon = a.anonymize("IBAN DE89370400440532013000 am 07.12.2024")
    assert "[IBAN_1]" in anon
    assert "[DATUM_1]" in anon
    # IBAN-Ziffernanteil darf NICHT zusätzlich als TELEFON_x auftauchen
    assert "[TELEFON_1]" not in anon

def test_context_md_style_untouched():
    """Regressionstest für D-08: context.md/style.md dürfen NIE durch den
    Anonymizer laufen — dieser Test dokumentiert den Vertrag auf Modulebene
    (die eigentliche Durchsetzung erfolgt in generate.py, nicht in pii.py)."""
    ...  # siehe generate.py-Integrationstest unten

def test_deanonymize_handles_two_digit_tag_numbers():
    """Regressionstest für Pitfall 6 (Substring-Kollision bei [IBAN_1] vs [IBAN_10])."""
    a = Anonymizer()
    text = " ".join(f"user{i}@kunde.de" for i in range(1, 12))  # erzeugt EMAIL_1..EMAIL_11
    anon = a.anonymize(text)
    assert a.deanonymize(anon) == text
```

**Precision/Recall-Messung (ANON-04-nah, Success-Criterion 4 aus ROADMAP.md):** Eine kleine Fixture-Tabelle (erwartete Treffer je Typ gegen eine Sammlung realistischer Testsätze, ähnlich `agent/tests/fixtures/pre-deployment/*.eml`) reicht für Variante A aus — volle Precision/Recall-Statistik (wie in ANON-06 für NER vorgesehen) ist hier über-engineert; ein einfaches „alle erwarteten Treffer erkannt, keine unerwarteten False Positives in den Kern-Fällen" genügt, ergänzt um dokumentierte akzeptierte Grenzfälle (siehe Pitfall zu Rechnungsnummern).

**Integrationstests je Aufrufer:**
- `test_classify.py`: neuer Test, der prüft, dass `llm.llm_call`-Aufruf-`prompt` bei PII-haltigem `body` KEINE Rohwerte enthält (schließt Pitfall 5).
- `test_generate.py`: prüft (a) `context_md_full`-Segment im Prompt bleibt roh trotz PII-Inhalt (schließt Pitfall 4), (b) `conversation_history`-Bodies werden anonymisiert (schließt bestehende Lücke), (c) LLM-Antwort mit Platzhalter wird korrekt zu echten Werten zurückgewandelt.
- `webui/tests/test_style_extract.py`: Reihenfolge-Fix (Redact/Anonymize VOR Truncate) regressionsabgesichert.
- Neuer Test in `webui/tests` für `chat_tools.py`: simuliert einen zweirundigen Tool-Loop (`mails_suchen` liefert PII-haltigen Body → LLM „zitiert" den Platzhalter in einem `entwurf_erstellen`-Tool-Call → Assertion, dass der tatsächlich gebaute Draft-Bytes-Inhalt die ECHTEN Werte enthält, nicht den Platzhalter) — deckt Pitfall 3 ab, der wichtigste Einzeltest dieser Phase.
- Neuer Test für `chat.py::deanonymize_stream` mit künstlich fragmentiertem Mock-Iterator (`["...[IBA", "N_1]..."]`) — deckt Pitfall 2 ab.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Konkrete Regex-Muster für IBAN/Telefon/E-Mail/URL/Datum (siehe Code-Beispiele) | Code Examples / Architecture Patterns | Falsche/zu lockere Muster → entweder PII-Leck (Under-Detection, sicherheitsrelevant) oder kaputte Drafts durch Over-Maskierung von Nicht-PII (Qualitätsrisiko) — MUSS vor Produktiv-Einsatz gegen Fixtures verifiziert werden |
| A2 | Empfehlung, die Integration NICHT in `llm.py` selbst, sondern pro Aufrufer vorzunehmen (Abweichung von der wörtlichen D-06-Formulierung) | Architecture Patterns | Falls der Nutzer/Planner auf einer wörtlichen `llm.py`-Änderung besteht, entsteht ein echter Zielkonflikt mit D-08 (context.md-Exemption) — sollte VOR der Planung kurz bestätigt werden, ist aber technisch die einzig korrekte Lösung, die beide Entscheidungen gleichzeitig erfüllt |
| A3 | Reverse-Lookup für „gleicher Wert → gleicher Tag" arbeitet auf dem exakten Roh-String (keine Formatnormalisierung für Telefonnummern) | Reversibles Mapping-Design | Geringes Risiko: derselbe Wert in zwei Schreibweisen bekommt zwei Tags — kein Daten-Leck, nur kosmetische Inkonsistenz |
| A4 | Neuer Feature-Flag-Name (`ENABLE_PSEUDONYM` vs. Wiederverwendung von `ENABLE_PII_REDACTION`) — siehe Offene Frage unten | Config-Namensraum | Zwei überlappende, verwirrende Flags in `.env.example`/README, falls nicht vorab entschieden |

## Open Questions (RESOLVED)

1. **Flag-Namensraum: `ENABLE_PII_REDACTION` (bestehend) vs. `ENABLE_PSEUDONYM` (D-07, „o.ä.")**
   - Was wir wissen: `ENABLE_PII_REDACTION` existiert bereits (Default `true`), aber nur für den alten, einseitigen, nicht-nummerierten IBAN/CC-Redact in `main.py`. D-07 schlägt einen NEUEN Namen vor, lässt ihn aber laut Wortlaut ausdrücklich offen.
   - Was unklar ist: Ob Variante A den bestehenden Flag inhaltlich erweitert (gleicher Name, neue/größere Bedeutung: „reversible Pseudonymisierung aller Typen über alle Pfade") oder einen zweiten, parallelen Flag einführt.
   - **RESOLVED (Plan 10-01, `<flag_decision>`):** `ENABLE_PII_REDACTION` wird WIEDERVERWENDET (Bedeutung erweitert auf reversible Pseudonymisierung aller strukturierten Typen); KEIN neuer Flag.
   - Empfehlung: Bestehenden Namen `ENABLE_PII_REDACTION` WIEDERVERWENDEN (Bedeutung erweitern), um KEINE zweite, verwirrende Checkbox/Env-Var im selben Themenfeld zu erzeugen — es gibt heute ohnehin keine WebUI-Checkbox für diesen Flag (nur `.env`), das Risiko einer verwirrenden UI ist gering, aber zwei ähnlich benannte, teils überlappende Flags in `.env.example` + README sind unnötige Komplexität für den nicht-technischen Betreiber (CLAUDE.md: `operator_type: non-technical`). Sollte im Plan-/Discuss-Schritt kurz bestätigt werden.

2. **Sollen die Tool-Ergebnis-Payloads (chat_tools.py) auch für eine mögliche zukünftige direkte SSE-Anzeige de-anonymisiert werden?**
   - Was wir wissen: Aktuell werden Tool-Ergebnisse NIE direkt an die SSE-Oberfläche gestreamt (nur ein Aktivitäts-Label `🔧 name…`), nur der finale Assistant-Text.
   - Was unklar ist: Falls eine spätere Phase Tool-Ergebnisse doch direkt anzeigt (Transparenz-Feature), müsste dort ebenfalls de-anonymisiert werden.
   - **RESOLVED (Plan 10-03):** Fuer Phase 10 ignoriert - Tool-Payloads werden nie direkt per SSE angezeigt (nur ein Aktivitaets-Label); ein Hinweis-Kommentar bleibt im Code, falls eine spaetere Phase Payloads direkt anzeigt.
   - Empfehlung: Für Phase 10 ignorieren (kein aktueller Anzeige-Pfad für rohe Tool-Payloads), aber als Hinweis-Kommentar im Code hinterlassen, falls sich das ändert.

3. **`webui/src/pii.py`-Drift-Guard: fehlt in `agent/tests/`?**
   - Was wir wissen: `webui/tests/test_pii_sync.py` existiert und vergleicht `agent/src/pii.py` ↔ `webui/src/pii.py` per SHA-256. In `agent/tests/` fehlt eine analoge Datei (nur `test_crypto_sync.py` existiert dort laut Dateisystem-Scan).
   - Was unklar ist: Ob das Fehlen beabsichtigt ist (ein Guard reicht, unabhängig davon, in welchem der beiden Test-Verzeichnisse er läuft) oder eine Lücke aus einer früheren Phase.
   - **RESOLVED (Plan 10-01, Task 2):** Die fehlende Kopie `agent/tests/test_pii_sync.py` wird in Plan 10-01 angelegt (byte-identisch zu webui/tests) - Guard-Luecke geschlossen.
   - Empfehlung: Nicht Teil des Phase-10-Scopes, aber bei Gelegenheit (z. B. wenn `pii.py` ohnehin umfangreich geändert wird) die fehlende Kopie in `agent/tests/test_pii_sync.py` ergänzen — kostet nichts, schließt eine Lücke im bestehenden Drift-Guard-Muster.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---|---|---|
| V5 Input Validation | ja | Regex-basierte Erkennung auf begrenzten, bereits vor-getruncateten Textmengen (max. 2000/800/1500 Zeichen je Pfad) — kein ReDoS-Risiko bei den vorgeschlagenen Mustern (keine verschachtelten Quantifizierer), aber bei künftigen Muster-Erweiterungen (ANON-06) erneut prüfen |
| V6 Cryptography | nein | Kein Kryptographie-Bedarf — Mapping ist reiner In-Memory-`dict`, nie serialisiert/gehasht |
| V9 (Communications)/Datenschutz-nahes Prinzip | ja (Kernzweck dieser Phase) | Reduktion des an den externen LLM-Anbieter übermittelten Klartexts für strukturierte PII-Typen |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---|---|---|
| PII-Leck an Cloud-LLM durch übersehene/falsch-negative Regex-Treffer | Information Disclosure | Fixture-Coverage + Warn-Log bei Restresten nach De-Anonymisierung (siehe Pitfall 6/Code-Beispiele); dokumentiertes Restrisiko (Namen bleiben in Variante A ohnehin exponiert, siehe CONTEXT.md) |
| Prompt-Injection aus Mail-Inhalt, die das LLM zur wörtlichen Preisgabe/Wiederholung eines Platzhalter-Mappings verleiten will | Tampering/Information Disclosure | Bereits durch Phase-9-Untrusted-Data-Anker (`_UNTRUSTED_TOOL_RESULT_ANCHOR`) plus D-04 (Mapping verlässt den Server nie, wird nie geloggt/ans LLM übergeben — es existiert serverseitig, das LLM kennt nur die Tags, nicht das Mapping) strukturell ausgeschlossen |
| Tool-Argument-Platzhalter-Leck in echten Kunden-Draft | Information Disclosure (umgekehrt: Pseudonym-Leck statt PII-Leck) | De-Anonymisierung der Tool-Input-Argumente vor Handler-Aufruf (Pitfall 3) |

## Sources

### Primary (HIGH confidence — Codebase, in dieser Session gelesen)
- `agent/src/pii.py`, `webui/src/pii.py` — bestehende Redaction-Logik
- `agent/src/llm.py`, `webui/src/llm.py` — Dispatcher-Design, Drift-Guard
- `agent/src/classify.py`, `agent/src/generate.py`, `agent/src/main.py`, `agent/src/config.py`, `agent/src/imap_client.py`
- `webui/src/chat.py`, `webui/src/chat_tools.py`, `webui/src/style_extract.py`
- `agent/prompts/classify.txt`, `agent/prompts/generate.txt`
- `agent/tests/test_pii.py`, `agent/tests/test_llm.py`, `agent/tests/conftest.py`, `agent/tests/test_classify.py`
- `webui/tests/test_pii_sync.py`, `webui/tests/test_llm_sync.py`
- `.planning/ROADMAP.md` §Phase 10, `.planning/REQUIREMENTS.md` §v1.6, `.planning/config.json`

### Secondary (MEDIUM confidence)
- Keine externen Quellen herangezogen — reine stdlib-Regex-Technik ohne Bibliotheks-API, für die eine Doku-Recherche nötig wäre.

### Tertiary (LOW confidence / ASSUMED)
- Konkrete Regex-Muster (IBAN/Telefon/E-Mail/URL/Datum) — Trainingswissen-basiert, siehe Assumptions Log A1. Fixture-Härtung ist zwingender nächster Schritt in der Implementierung.

## Metadata

**Confidence breakdown:**
- Codebase-/Integrationsarchitektur: HIGH — direkt aus dem Code verifiziert, alle fünf Call-Pfade gelesen
- Regex-Muster: MEDIUM/ASSUMED — plausibel, aber nicht gegen echte Fixtures gehärtet
- Pitfalls (Streaming, Tool-Argumente, Truncate-Reihenfolge): HIGH — direkt aus Code-Analyse abgeleitet, keine Spekulation

**Research date:** 2026-07-19
**Valid until:** Bis zur nächsten strukturellen Änderung an `chat.py`/`chat_tools.py`/`llm.py` (kein Ablaufdatum im klassischen Sinn, da reine Codebase-Analyse — bei signifikanten Refactorings dieser Module vor Phase-10-Umsetzung erneut prüfen)
