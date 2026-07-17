# Phase 6: Schreibstil-Adaption pro Agent (v1.3) - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-17
**Phase:** 06-schreibstil-adaption
**Areas discussed:** Stil-Quellen (manuell + gelernt), Ausführungsort der Extraktion, Modellwahl, Profil-Format

---

## Bereichsauswahl (Eröffnungsfrage)

Angeboten: Re-Learn-Mechanik & Ausführungsort | Stil-Profil-Format | Modell & Extraktions-Call | Antwort-Mail-Filter & Mindestmenge

**User's choice:** Freitext statt Auswahl — neuer Wunsch: optionales Freitext-Feld im WebUI zum Beschreiben des Schreibstils bzw. Einfügen eines Beispiels (optional, leer erlaubt; vor allem für neue/leere Postfächer), zusätzlich zum Lernen aus gesendeten Mails. Bestätigung der Per-Agent-Isolation („keine Sammeldateien"). Meta-Hinweis: bei Fable-Limit mit Opus weitermachen.
**Notes:** Freitext-Feld als In-Scope-Erweiterung übernommen (D-52). Klargestellt: Fernet-Verschlüsselung betrifft nur Secrets in `.env`; style.md bleibt Klartext wie context.md (D-57).

---

## Stil-Quellen: manuelles Feld × gelerntes Profil

| Option | Description | Selected |
|--------|-------------|----------|
| Kombiniert im LLM-Call (Empfohlen) | Manuelle Beschreibung/Beispiel als zusätzlicher Input in den Extraktions-Call; EIN style.md; leeres Postfach → Profil nur aus manueller Angabe | ✓ |
| Manuell gewinnt, Lernen nur Fallback | Gefülltes Feld → nur daraus Profil; gesendete Mails werden ignoriert | |
| Zwei getrennte Blöcke in style.md | Gelernter + manueller Abschnitt, beide injiziert | |

**User's choice:** Kombiniert im LLM-Call
**Notes:** → D-52

---

## Ausführungsort der Extraktion

| Option | Description | Selected |
|--------|-------------|----------|
| In der WebUI, synchron (Empfohlen) | WebUI holt Sent-Mails selbst per IMAP (imap-tools als WebUI-Dependency), ruft LLM direkt, HTMX-Spinner ~30–60 s; Esso-Guard gratis (Extraktion nur bei Anlage + Button) | ✓ |
| Im Agent-Container, asynchron | Marker-Flag, Ergebnis erst nach nächstem Poll-Zyklus (bis 5 Min); Setup-Guard für Esso extra nötig | |

**User's choice:** Option 1 (WebUI, synchron) — mit Rückfrage, ob der Agent den Stil danach laufend aktualisiert oder ob es einmalig ist.
**Notes:** Antwort: einmalig beim Setup + manuell per Re-Learn-Button (STY-05, Nicht-Ziel „kein Learning-Loop"); der Agent liest style.md nur. → D-53, D-54. Periodische Auto-Aktualisierung als Deferred Idea notiert.

---

## Modellwahl für die Extraktion

| Option | Description | Selected |
|--------|-------------|----------|
| Draft-Modell (Empfohlen) | Pro Provider verdrahtetes Draft-Modell (Sonnet-Klasse bei Anthropic); Qualität zählt, einmalige Kosten | ✓ |
| Classify-Modell | Haiku-Klasse, billiger, flachere Profile | |

**User's choice:** Draft-Modell → D-55

---

## Profil-Format

| Option | Description | Selected |
|--------|-------------|----------|
| Festes Abschnitts-Schema (Empfohlen) | Vorgegebene Überschriften: Anrede, Du/Sie, Grußformel, Satzlänge, Formalität, typische Wendungen | ✓ |
| Freies Markdown | LLM strukturiert selbst; flexibler, aber unvorhersehbar | |

**User's choice:** Festes Abschnitts-Schema → D-56

---

## Abschlussfrage

**User's choice:** „Reicht — CONTEXT.md schreiben" — Detailfragen ausdrücklich an Claude delegiert.

## Claude's Discretion

- Mail-Filter (echte Antwort-Mails) + Mindestanzahl + Hinweis-Verhalten
- UI-Platzierung von Freitext-Feld und Re-Learn-Button
- `ENABLE_STYLE_ADAPTION`-Detailverhalten
- Ablageort/Format der manuellen Stil-Angabe (muss Re-Learn überleben)
- Prompt-Design (style-extract + Injection-Block mit Hierarchie context = WAS, style = WIE)
- Sent-Ordner-Erkennung (SPECIAL-USE `\Sent` + Provider-Fallback)
- Längen-Deckel style.md / Body-Truncation

## Deferred Ideas

- Periodische/automatische Stil-Aktualisierung (Learning-Loop) — bewusst nicht in Phase 6
- Verschlüsselung von style.md — nur bei ausdrücklichem Wunsch
