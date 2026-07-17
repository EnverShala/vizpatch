# Phase 6: Schreibstil-Adaption pro Agent (v1.3) - Pattern Map

**Mapped:** 2026-07-17
**Files analyzed:** 13 (neu + geändert)
**Analogs found:** 13 / 13

## File Classification

| Neue/geänderte Datei | Rolle | Data Flow | Nächster Analog | Match-Qualität |
|---|---|---|---|---|
| `webui/src/style_extract.py` (neu) | service | request-response (IMAP-Fetch + synchroner LLM-Call) | `webui/src/llm_seed.py` + `agent/src/imap_client.py` (`detect_drafts_folder`, `fetch_sender_history`) | role-match (kombiniert zwei Analoge) |
| `webui/prompts/style-extract.txt` (neu) | config/prompt-template | transform | `webui/prompts/context-seed.txt` | exact |
| `webui/src/agents_io.py` (geändert: `read_style_md`/`write_style_md_atomic`, `read_style_note`/`write_style_note`) | service (per-Agent-I/O) | file-I/O | `agents_io.read_context_md`/`write_context_md_atomic` (dieselbe Datei) | exact |
| `webui/src/main.py` (geändert: neuer Endpoint `/style/generate`, `/style/relearn`, style-Felder in `/save`) | route/controller | request-response | Route `/context/generate` + `_save_response`-Fluss in derselben Datei | exact |
| `webui/src/templates/index.html` (geändert: style-Fieldset + Freitext + Re-Learn-Button) | component (Jinja-Template) | request-response (HTMX Section-Save) | context.md-Fieldset (Zeilen 171-189) + Zero-Reset-Zwei-Stufen-Bestätigung (Zeilen 252-264) in derselben Datei | exact |
| `webui/pyproject.toml` (geändert: `imap-tools` als Dependency) | config | - | `agent/pyproject.toml` (`imap-tools>=1.7,<2.0`) | exact |
| `agent/src/config.py` (geändert: `style_md`-Feld, `enable_style_adaption`-Flag) | config/model | file-I/O + CRUD-Read | `context_md`-Feld + `enable_pii_redaction`-Flag (dieselbe Datei) | exact |
| `agent/src/generate.py` (geändert: `{style_md}`-Injection) | service | transform (Prompt-Bau) | `_build_history_block` + `generate_draft_text` (dieselbe Datei) | exact |
| `agent/prompts/generate.txt` (geändert: Hierarchie-Block context.md > style.md) | config/prompt-template | transform | bestehendes Template (dieselbe Datei) | exact |
| `webui/src/sent_folder.py` ODER Funktion in `style_extract.py` (neu: `\Sent`-SPECIAL-USE-Erkennung) | utility | request-response (IMAP-Probe) | `agent/src/imap_client.py::detect_drafts_folder()` | exact (Flag-Name austauschen) |
| `agent/tests/test_generate_with_style.py` (neu) | test | - | `agent/tests/test_generate_with_history.py` | exact |
| `webui/tests/test_style_extract.py` (neu) | test | - | `webui/tests/test_llm_seed.py` | exact |
| `webui/tests/test_endpoints_style.py` (neu) | test | - | `webui/tests/test_endpoints_seed.py` | exact |

## Pattern Assignments

### `webui/src/style_extract.py` (service, request-response)

**Analog 1 (LLM-Call-Pfad):** `webui/src/llm_seed.py`

**Kompletter Analog-Inhalt** (`webui/src/llm_seed.py:1-37`):
```python
import logging
import os
from pathlib import Path

from anthropic import Anthropic

logger = logging.getLogger(__name__)

MAX_INPUT_LENGTH = 5000


def generate(firma_input: str, api_key: str, model: str | None = None) -> str:
    """Context-KI-Assistent (Sonnet). Key-Quelle ist der Aufrufer (main.py:
    entschlüsselter LLM_API_KEY des aktiven Agenten, Anthropic-only — Pitfall 6).
    """
    prompt_path = Path(os.getenv("WEBUI_SEED_PROMPT", "/app/prompts/context-seed.txt"))
    if len(firma_input) > MAX_INPUT_LENGTH:
        raise ValueError(f"Input too long: {len(firma_input)} > {MAX_INPUT_LENGTH}")
    if not api_key:
        raise RuntimeError("Kein API-Key übergeben")
    template = prompt_path.read_text(encoding="utf-8")
    prompt = template.replace("{firma_input}", firma_input)
    resolved_model = model or os.getenv("MODEL_DRAFT") or "claude-sonnet-4-6"
    client = Anthropic(api_key=api_key)
    message = client.messages.create(
        model=resolved_model,
        max_tokens=2000,
        temperature=0.5,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "".join(block.text for block in message.content if block.type == "text")
    logger.info(
        "context_seed_generated",
        extra={"input_length": len(firma_input), "output_length": len(text), "model": resolved_model},
    )
    return text
```

**Übertragbar auf `style_extract.py`:**
- Gleicher Aufbau: Prompt-Template laden, Platzhalter ersetzen, `Anthropic(api_key=api_key)`-Client bauen, `messages.create(...)`, Text-Blöcke joinen, strukturiertes Logging.
- **Abweichung laut D-55:** Modell ist NICHT hart `claude-sonnet-4-6`, sondern das pro Provider aufgelöste **Draft-Modell** — dafür `agent/src/llm.py::llm_call(...)` direkt wiederverwenden (Provider-Dispatch inkl. OpenAI/Google), NICHT den Anthropic-only-Pfad von `llm_seed.py` kopieren. Siehe Shared-Pattern „LLM-Adapter" unten.
- **Abweichung laut D-52:** zwei Eingabequellen (Mails + Freitext) werden VOR dem Call zu einem Prompt-Input zusammengeführt — kein einfaches `template.replace(...)`, sondern Format-String mit zwei Platzhaltern (`{sent_mails}`, `{manual_style_note}`), analog zu `agent/src/generate.py::generate_draft_text` (`.format(**{...})`, siehe unten).

**Analog 2 (IMAP-Fetch der letzten N gesendeten Mails):** `agent/src/imap_client.py::fetch_sender_history` (Zeilen 153-184)
```python
def fetch_sender_history(
    self, from_address: str, days: int = 30, max_messages: int = 6
) -> list[MailMessage]:
    """Absender-Fallback: FROM x in INBOX, TO x in Sent, max 30 Tage."""
    assert self._mailbox is not None, "Use inside 'with' block"
    since = (datetime.utcnow() - timedelta(days=days)).date()
    results: list[MailMessage] = []
    for folder, query in [
        (self.config.imap_inbox_folder, AND(from_=from_address, date_gte=since)),
        (self.config.imap_sent_folder,  AND(to=from_address,   date_gte=since)),
    ]:
        try:
            self._mailbox.folder.set(folder)
            for msg in self._mailbox.fetch(query, mark_seen=False, charset="UTF-8"):
                results.append(msg)
        except Exception:
            self.logger.warning("history_fetch_failed", extra={"folder": folder})
    ...
```
**Übertragbar:** Gleiches `with MailBox(...) as mailbox: mailbox.folder.set(sent_folder); mailbox.fetch(AND(...), mark_seen=False, reverse=True)`-Muster, begrenzt auf `STYLE_SAMPLE_COUNT` (Default 30) neueste Mails statt Datumsfenster. `imap-tools` wird dafür WebUI-Dependency (siehe unten, `webui/pyproject.toml`).

**Fehler-Isolation (Established Pattern, Phase 5):** fehlender/leerer Sent-Ordner darf laut D-52 nicht crashen — Try/Except analog zu `fetch_sender_history`, Ergebnis "kein Profil, Hinweis im WebUI" (STY-05).

---

### `webui/prompts/style-extract.txt` (config/prompt-template)

**Analog:** `webui/prompts/context-seed.txt` (komplett, 43 Zeilen s.o.)

**Übertragbares Muster:**
- Feste Instruktion "Antworte NUR mit dem Markdown-Inhalt", keine Erklärungen davor/danach
- Feste Sektionen-Struktur vorgeben (hier: **Anrede, Du/Sie, Grußformel, Satzlänge, Formalität, typische Wendungen** — D-56), das LLM füllt nur die Abschnitte
- Platzhalter-Konvention `[in eckigen Klammern]` bei fehlender Information — analog anwendbar wenn zu wenig Mail-Material vorliegt
- Zwei Input-Platzhalter statt einem: `{sent_mails}` (redigierter Mail-Text) und `{manual_style_note}` (Freitext-Feld, ggf. leer)

---

### `webui/src/agents_io.py` — neue Funktionen `read_style_md`/`write_style_md_atomic`

**Analog:** `read_context_md`/`write_context_md_atomic` (dieselbe Datei, Zeilen 130-143)
```python
def read_context_md(agent_id: str) -> str:
    context_path = _context_path(agent_id)
    if context_path.exists():
        return context_path.read_text(encoding="utf-8")
    return ""


def write_context_md_atomic(agent_id: str, content: str) -> None:
    context_path = _context_path(agent_id)
    context_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = context_path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, context_path)
```
**1:1 übertragbar** — neuer Pfad-Helper `_style_path(agent_id) -> Path` analog zu `_context_path` (Zeilen 63-64: `_agent_dir(agent_id) / "context.md"` → `_agent_dir(agent_id) / "style.md"`), gleiches Atomic-Write-Muster (`.tmp` + `os.replace`). Kein Fernet-Encrypt nötig (D-57: style.md ist Klartext wie context.md, kein Eintrag in `SECRET_KEYS`).

**Für die manuelle Freitext-Stil-Angabe** (Ablageort Claude's Discretion, D-57): gleiches Muster erneut anwenden, z.B. `_style_note_path(agent_id) -> _agent_dir(agent_id) / "style_note.md"` mit `read_style_note`/`write_style_note_atomic` — muss laut D-54 einen Re-Learn überleben, also eigene Datei statt Teil von `style.md` (das der Re-Learn überschreibt).

---

### `webui/src/main.py` — neuer Endpoint `/style/generate` (+ Re-Learn-Bestätigung)

**Analog:** Route `/context/generate` (dieselbe Datei, Zeilen 218-254)
```python
@app.post("/context/generate")
@limiter.limit("10/minute")
def context_generate(
    request: Request,
    agent_id: str = Form(...),
    firma_input: str = Form(..., max_length=5000),
    user: str = Depends(auth.require_auth),
):
    try:
        env = agents_io.read_env_raw(agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid agent_id")

    provider = (env.get("LLM_PROVIDER") or "").strip()
    if provider != "anthropic":
        raise HTTPException(
            status_code=400,
            detail=(
                "Der Context-Assistent nutzt Anthropic — dieser Agent verwendet "
                f"{provider or 'keinen erkannten Provider'}. context.md bitte manuell pflegen "
                "oder einen Anthropic-Key hinterlegen."
            ),
        )
    raw_key = (env.get("LLM_API_KEY") or "").strip()
    if not raw_key:
        raise HTTPException(status_code=400, detail="Kein API-Key für diesen Agenten gespeichert")

    try:
        api_key = crypto.decrypt_value(raw_key)
        seed_text = llm_seed.generate(firma_input, api_key=api_key)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="LLM service error")
    return PlainTextResponse(seed_text)
```
**Übertragbar:**
- Gleiche Fehler-Kaskade: invalid agent_id → 400, kein Key → 400, `ValueError` (Input zu lang) → 400, `RuntimeError` (LLM-Fehler) → 500, generischer Fallback → 500
- **Wichtige Abweichung (D-55):** KEIN Anthropic-only-Gate mehr — style.md-Extraktion nutzt den `llm.llm_call(...)`-Adapter (Provider-agnostisch), der Non-Anthropic-Block (Zeilen 231-240) entfällt für den Style-Endpoint
- Rate-Limit `@limiter.limit(...)` übernehmen (Extraktion ist teurer/langsamer — ggf. enger takten, z.B. `5/minute`, wegen 30-60s IMAP+LLM-Laufzeit)
- HTMX-Indikator während 30-60s Wartezeit: analog zum bestehenden `generateContext(btn)`-JS-Muster in `index.html` (Zeilen 220-248) — Button disabled + Text "⏳ Generiere…" während `fetch(...)`

**Re-Learn-Bestätigung — Analog:** Zwei-Stufen-Bestätigung Zero-Reset (`main.py:382-402`, Route `/reset`)
```python
@app.post("/reset")
def reset_all_endpoint(
    confirmation: str = Form(""),
    user: str = Depends(auth.require_auth),
):
    if confirmation != "LÖSCHEN":
        return RedirectResponse(
            f"/?error={quote('Zero-Reset abgebrochen: Bestätigungswort war nicht ‚LÖSCHEN‘.')}",
            status_code=303,
        )
    ...
```
**Übertragbar auf Re-Learn:** clientseitiges `confirm(...)` im Button (JS `onclick`/`hx-confirm`, wie schon bei `/update/pull` in `index.html:268`) reicht hier vermutlich aus (kein Tippen von "LÖSCHEN" nötig, da Re-Learn nicht destruktiv im Sinne von Datenverlust ist, sondern nur Überschreiben eines wieder-generierbaren Profils) — Claude's Discretion laut D-54/CONTEXT.md „UI-Platzierung … Re-Learn-Button". Falls strengere Bestätigung gewünscht: identisches `pattern="LÖSCHEN"`-Input-Feld-Muster wie bei Agent-Löschen (`index.html:52-56`) 1:1 kopierbar.

---

### `agent/src/config.py` — `style_md`-Feld + `enable_style_adaption`-Flag

**Analog 1 (Feld-Lademuster context_md):** Zeilen 116-123, 171
```python
    # Pfade
    context_file: Path
    state_db: Path
    prompts_dir: Path

    # Loaded content
    context_md: str
    prompt_classify: str
    prompt_generate: str
    ...
    context_md = context_file.read_text(encoding="utf-8") if context_file.exists() else ""
```
**Übertragbar:** neues Feld `style_file: Path` (analog `context_file`) + `style_md: str` (analog `context_md`), gleiches `if .exists() else ""`-Guard (Fehler-Isolation: fehlendes style.md bricht den Draft-Pfad nie, D-Established-Pattern). Pfad in `load_agent_config` (Zeile 270): `agent_dir / "style.md"` analog `agent_dir / "context.md"`.

**Analog 2 (Feature-Flag-Muster `ENABLE_PII_REDACTION`):** Zeilen 111-113, 199
```python
    # Flags
    enable_pii_redaction: bool
    log_level: str
    ...
    enable_pii_redaction=(env.get("ENABLE_PII_REDACTION") or "true").lower() == "true",
```
**Übertragbar 1:1:** `enable_style_adaption: bool` im dataclass + `enable_style_adaption=(env.get("ENABLE_STYLE_ADAPTION") or "true").lower() == "true"` in `_build_config` (D-54: Default `true`). Bei `false` liest `generate.py` `style_md` gar nicht bzw. injiziert leeren Block (Claude's Discretion, „was der Schalter genau unterdrückt" — konsistent mit `enable_pii_redaction`, das in `main.py`/`draft.py` konditional geprüft wird).

---

### `agent/src/generate.py` — `{style_md}`-Injection

**Analog (History-Block-Bau + Prompt-Format, komplett, Zeilen 20-88):**
```python
_HISTORY_BODY_MAX_CHARS = 800


def _truncate_body(body: str, max_chars: int = _HISTORY_BODY_MAX_CHARS) -> str:
    if len(body) <= max_chars:
        return body
    return body[:max_chars] + "\n[... gekürzt ...]"


def _build_history_block(history: list) -> str:
    """Baut den {conversation_history}-Prompt-Block aus MailMessage-Liste."""
    if not history:
        return ""
    ...


def generate_draft_text(
    from_address: str,
    subject: str,
    body: str,
    config: Config,
    logger: Optional[logging.Logger] = None,
    conversation_history: list | None = None,
) -> str:
    ...
    company_name = _extract_company_name(config.context_md)
    history_block = _build_history_block(conversation_history or [])
    prompt = config.prompt_generate.format(
        **{
            "company_name": company_name,
            "context_md_full": config.context_md,
            "conversation_history": history_block,
            "from": from_address,
            "subject": subject,
            "body": body.strip(),
        }
    )
```
**Übertragbar:** analoges optionales Prompt-Argument `style_md_block = config.style_md if config.enable_style_adaption else ""`, zusätzlicher Format-Key `"style_md": style_md_block`. Leerer String bei fehlendem/deaktiviertem Profil → Prompt-Verhalten bleibt exakt wie heute (STY-02-Kontrakt, „leer = Verhalten wie heute"), analog zu `conversation_history=[]` → `history_block = ""` (kein "None"-String im Prompt, siehe Test `test_generate_empty_history_no_none_in_prompt`).

---

### `agent/prompts/generate.txt` — Hierarchie-Block context.md > style.md

**Analog (bestehendes Template, komplett, 22 Zeilen):**
```
Du bist der E-Mail-Assistent für {company_name}.
Entwerfe eine kurze, freundliche, professionelle Antwort auf die folgende Kundenanfrage.
Antworte auf Deutsch. Halte den Ton und die Vorgaben ein, die im Firmen-Kontext stehen.
Antworte NUR mit dem E-Mail-Text (kein Betreff, keine Headers). Am Ende die Signatur.

# Firmen-Kontext

{context_md_full}

# Bisheriger Gesprächsverlauf (wenn vorhanden)

{conversation_history}

# Eingehende E-Mail

Von: {from}
Betreff: {subject}

{body}

# Deine Antwort:
```
**Übertragbar:** neue Sektion nach `# Firmen-Kontext` einfügen, z.B.:
```
# Schreibstil (wenn vorhanden — NUR Ton/Form, NIE Inhalt)

{style_md}
```
mit einem expliziten Hierarchie-Satz in der Kopfzeile (D-56-Formulierung: „Firmen-Kontext bestimmt WAS gesagt wird, Schreibstil nur WIE"). Gleiches Prinzip wie `{conversation_history}` — Platzhalter bleibt im Format-Aufruf immer vorhanden, leer wenn nicht gesetzt.

---

### `\Sent`-SPECIAL-USE-Erkennung (neu, WebUI-seitig)

**Analog:** `agent/src/imap_client.py::detect_drafts_folder()` (Zeilen 61-78)
```python
def detect_drafts_folder(self) -> Optional[str]:
    """Auto-Discovery via IMAP SPECIAL-USE (RFC 6154).
    Sucht nach einem Ordner mit \\Drafts-Flag. Gibt None zurück wenn der
    Server das Feature nicht announciert oder kein Draft-Ordner markiert ist.
    """
    assert self._mailbox is not None, "Use inside 'with' block"
    try:
        for folder_info in self._mailbox.folder.list():
            flags = tuple(str(f) for f in (folder_info.flags or ()))
            if any("Drafts" in f for f in flags):
                self.logger.info(
                    "drafts_folder_detected_via_special_use",
                    extra={"folder": folder_info.name, "flags": flags},
                )
                return folder_info.name
    except Exception as e:
        self.logger.warning("special_use_detection_failed", extra={"error": str(e)})
    return None
```
**1:1 übertragbar** — `"Drafts" in f` → `"Sent" in f` (RFC 6154 kennt `\Sent` als Standard-Flag-Name), gleiches Try/Except-Fallback-auf-`None`-Muster. **Resolution-Chain** (welche Quelle Vorrang hat) analog zu `agent/src/main.py::_resolve_drafts_folder` (Zeilen 184-240): 1) explizit gesetzt (`IMAP_SENT_FOLDER`, bereits vorhanden in `config.imap_sent_folder`/`provider_config.py`) 2) SPECIAL-USE-Probe 3) Provider-Tabellen-Default. Da die Extraktion NUR beim Setup/Button läuft (kein Poll-Zyklus, D-53), wird der Caching-Mechanismus (`_drafts_cache`) NICHT benötigt — einfache Einmal-Probe pro Extraktions-Call reicht.

**Provider-Fallback bereits vorhanden:** `agent/src/provider_config.py` — `sent`-Spalte pro Provider ist bereits gepflegt (Zeilen 6-33, inkl. IONOS-Korrektur `"Gesendete Objekte"`). Direkt wiederverwendbar (`resolve_imap_config(email)["sent"]`), keine Neuimplementierung nötig — nur Import in die WebUI (bisher Agent-only-Modul, ggf. als Shared-Utility referenzieren statt duplizieren).

---

## Shared Patterns

### PII-Redaction vor jedem LLM-Call mit externem Text
**Source:** `agent/src/pii.py::redact()` (komplett, 44 Zeilen)
```python
def redact(text: str) -> str:
    """Redact IBANs and Luhn-valid credit-card numbers from text."""
    if not text:
        return text
    text = _IBAN_PATTERN.sub("[IBAN_REDACTED]", text)
    text = _CC_PATTERN.sub(_redact_cc, text)
    return text
```
**Apply to:** `webui/src/style_extract.py` — jede gesendete Mail-Body VOR dem Extraktions-Call durch `redact()` schicken (STY-03/STY-04). Modul bereits in `agent/src/pii.py` vorhanden — entweder als Shared-Dependency importieren (`agent/` und `webui/` sind aktuell getrennte Packages ohne gemeinsames Shared-Lib) oder 1:1 nach `webui/src/pii.py` duplizieren (wie `crypto.py` bereits in beiden Services existiert, siehe `webui/src/crypto.py` vs. `agent/src/crypto.py` — etabliertes Dopplungs-Muster in diesem Repo, siehe Phase-5-Fix "WR-06 Drift-Guard für duplizierte crypto.py"). **Achtung:** Falls Dopplung gewählt wird, den in Phase 5 eingeführten Hash-Sync-Test (Drift-Guard) als Vorlage für einen analogen `pii.py`-Sync-Test nutzen.

### LLM-Adapter (Provider-agnostisch)
**Source:** `agent/src/llm.py::llm_call(...)` (komplett, 94 Zeilen)
```python
def llm_call(
    provider: str,
    api_key: str,
    model: str,
    prompt: str,
    max_tokens: int,
    temperature: float,
) -> str:
    fn = _DISPATCH.get((provider or "").strip().lower(), _call_anthropic)
    text = fn(prompt, model, max_tokens, temperature, api_key)
    logger.info("llm_call_done", extra={"provider": provider, "model": model})
    return text
```
**Apply to:** `webui/src/style_extract.py` MUSS diesen Adapter nutzen statt (wie `llm_seed.py`) fest auf `Anthropic(...)` zu verdrahten — D-55 verlangt Provider-Agnostik (Draft-Modell-Klasse je Provider). `llm.py` müsste als Dependency in die WebUI importierbar sein (aktuell nur `agent/src/llm.py` — entweder duplizieren analog `crypto.py` oder als gemeinsames Package extrahieren; Duplizieren ist das im Repo etablierte Vorgehen, siehe oben).

### Section-Save via HTMX
**Source:** `webui/src/templates/index.html:136-140` (IMAP-Fieldset-Beispiel)
```html
<div class="section-save">
  <button type="button" class="btn-section-save" hx-post="/save" hx-include="closest fieldset, #active-agent-id" hx-target="#save-msg-imap" hx-swap="innerHTML">Diesen Abschnitt übernehmen</button>
  <span id="save-msg-imap" class="save-inline-msg"></span>
</div>
```
**Apply to:** neues style-Fieldset (style.md-Textarea + Freitext-Feld) — gleicher Button/Span/`hx-include`-Aufbau, eigene `save-msg-style`-ID; Backend-Handler in `_save_response(...)` (main.py:257-264) unverändert wiederverwendbar.

### Fehler-Isolation pro Agent (Established Pattern, Phase 5)
**Source:** Established Pattern aus `agent/src/main.py` (`_fail_agent`, Zeile 243ff) + `config.py` (leerer `context_md`-Fallback)
**Apply to:** fehlendes/leeres `style.md` darf `generate_draft_text` NIE zum Absturz bringen — konsequent leerer String statt Exception, exakt wie beim bestehenden `context_md`-Guard (`config.py:171`).

## No Analog Found

Keine Datei ohne Analog — alle 13 klassifizierten Dateien haben einen konkreten Match im bestehenden Code (exact oder role-match/Kombination zweier Analoge).

## Metadata

**Analog search scope:** `agent/src/`, `agent/prompts/`, `agent/tests/`, `webui/src/`, `webui/src/templates/`, `webui/prompts/`, `webui/tests/`, `agent/pyproject.toml`, `webui/pyproject.toml`
**Files scanned:** ~25 (gezielt über CONTEXT.md-Canonical-Refs + Grep/Read, kein Full-Repo-Scan nötig da Referenzen bereits in CONTEXT.md benannt)
**Pattern extraction date:** 2026-07-17
