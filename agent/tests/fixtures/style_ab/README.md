# A/B-Fixtures: Schreibstil-Adaption (Phase 6, Plan 06-04, SC2)

Diese Fixtures sind die Grundlage für die **menschliche Abnahme** von SC2
("Draft mit vs. ohne Stil-Profil unterscheidet sich sichtbar im Ton, nicht im
Fach-Inhalt") und der Hierarchie-Härtung gegen T-06-01 ("style.md übersteuert
NIE den Firmen-Kontext, insbesondere nicht bei Beschwerden"). Die eigentliche
Ton-Bewertung ist subjektiv und erfolgt im nachfolgenden
`checkpoint:human-verify` (06-04, Task 2) — dieser Ordner liefert nur das
reproduzierbare Test-Material dafür.

## Dateien

| Datei | Zweck |
|-------|-------|
| `style-locker-ton.md` | Beispiel-`style.md` mit deutlich lockerem, Du-basiertem Ton — folgt dem D-56-Abschnitts-Schema (Anrede, Du/Sie, Grußformel, Satzlänge, Formalität, typische Wendungen) |
| `standard-oeffnungszeiten.eml` | Sachlich-neutrale Kundenanfrage (Standard-Fall) — Öffnungszeiten-Frage, keine Emotion, kein Konfliktpotential |
| `beschwerde-verspaetung.eml` | Beschwerde-Mail (verärgerter Kunde) — Wartezeit + unfreundliches Personal, klar negativ emotional |

## Abnahme-Ablauf (für Task 2 / den Checkpoint)

Ziel: pro Fall (Standard, Beschwerde) **zwei** Drafts erzeugen — einmal MIT
aktivem Stil-Profil, einmal OHNE — und die zwei Paare gegenüberstellen. Das
muss über einen **echten LLM-Call** laufen (kein Mock), weil die
Ton-Beurteilung inhaltlich/qualitativ ist und sich nicht per Unit-Test
automatisieren lässt.

### Empfohlener Weg: über die WebUI (End-to-End, deckt auch den Klick-Pfad ab)

1. WebUI starten (`docker compose up`), Agenten mit gültigen IMAP-Creds +
   LLM-Key anlegen (siehe `06-04-PLAN.md` Task 2, Schritte 1-4).
2. Den Inhalt von `style-locker-ton.md` in das `style.md`-Fieldset des Agenten
   einfügen und speichern (oder über den Freitext + Re-Learn-Button ein
   ähnlich lockeres Profil erzeugen lassen).
3. Die beiden `.eml`-Fixtures als Mail an das Test-Postfach des Agenten
   senden (bzw. deren Betreff/Body manuell als eingehende Anfrage
   nachstellen) und den Agenten pollen/draften lassen → **Draft A**
   (mit Stil-Profil).
4. `style.md` leeren (oder `ENABLE_STYLE_ADAPTION=false` setzen), denselben
   Fall erneut draften lassen → **Draft B** (ohne Stil-Profil).
5. Wiederholen für beide Fixtures (Standard-Fall + Beschwerde-Fall) → macht
   insgesamt 4 Drafts (2 Fälle × mit/ohne Profil).

### Alternativer Weg: direkter Python-Aufruf (schneller, aber ohne Klick-Pfad-Abdeckung)

Für einen schnellen Vergleich ohne volle WebUI-Interaktion kann
`generate_draft_text()` direkt zweimal mit demselben `mock_config`-Objekt
(siehe `agent/tests/conftest.py`) aufgerufen werden — einmal mit
`config.style_md` auf den Inhalt von `style-locker-ton.md` gesetzt, einmal mit
`config.style_md = ""`. Wichtig: `config.llm_api_key` muss ein **echter**
Anthropic-Key sein (kein Mock von `llm.llm_call`), sonst entsteht kein
verwertbarer Vergleichsdraft.

```python
from pathlib import Path
from src.generate import generate_draft_text

fixtures = Path(__file__).parent  # agent/tests/fixtures/style_ab
style_md = (fixtures / "style-locker-ton.md").read_text(encoding="utf-8")

# body/subject/from aus den .eml-Fixtures entnehmen (Header + Body manuell
# oder per email.message_from_file() extrahieren)

# Draft A: mit Stil-Profil
mock_config.style_md = style_md
draft_a = generate_draft_text(from_address, subject, body, mock_config)

# Draft B: ohne Stil-Profil (heutiges Verhalten)
mock_config.style_md = ""
draft_b = generate_draft_text(from_address, subject, body, mock_config)
```

Das jeweils gleiche Vorgehen für `beschwerde-verspaetung.eml` wiederholen.

## Erwartete Beobachtung (Ziel der menschlichen Bewertung)

| Fall | Draft MIT `style.md` (locker) | Draft OHNE `style.md` |
|------|-------------------------------|------------------------|
| **Standard** (`standard-oeffnungszeiten.eml`) | Sichtbar lockerer Ton: Du-Anrede, kurze Sätze, lockere Grußformel, ggf. Emoji/Umgangssprache aus dem Profil | Neutral-freundlicher, formeller Standard-Ton wie bisher (Sie, "Mit freundlichen Grüßen") |
| **Beschwerde** (`beschwerde-verspaetung.eml`) | Ton bleibt trotz lockerem `style.md` **sachlich und deeskalierend** — keine Emojis/Kumpel-Sprache bei einer verärgerten Beschwerde; die Hierarchie aus `agent/prompts/generate.txt` ("Firmen-Kontext bestimmt WAS, style.md nur WIE — darf fachliche Vorgaben NIE übersteuern") hält | Sachlich-deeskalierender Ton wie bisher |

**Bestehen des Checks (SC2):**
- Standard-Fall: Draft A und Draft B unterscheiden sich klar erkennbar im Ton (nicht im Fach-Inhalt — beide nennen dieselben Öffnungszeiten aus `context.md`).
- Beschwerde-Fall: Draft A bleibt trotz des lockeren Profils sachlich/deeskalierend — keine unpassende Lässigkeit gegenüber einem verärgerten Kunden. Der Fach-Inhalt (Entschuldigung, Angebot zur Klärung) bleibt in A und B gleich.

Falls der Beschwerde-Fall im MIT-Profil-Draft trotzdem unpassend locker wirkt,
ist das ein Blocker (T-06-01 nicht mitigiert) — nicht "approved" zurückmelden,
sondern die konkrete Abweichung im Checkpoint-Resume beschreiben (siehe
`06-04-PLAN.md`, Task 2, `resume-signal`).
