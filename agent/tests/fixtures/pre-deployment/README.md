# Pre-Deployment-Test-Fixtures

14 `.eml`-Fixtures für den Pre-Deployment-Test bei Vizionists (D-18).
Ziel: Vor dem Vor-Ort-Termin verifizieren dass Klassifikator und Generator
für die typischen Tankstellen-Anfrage-Muster solide arbeiten.

## Struktur

| Fixture | Kategorie | Erwartete Klassifikation | Test-Fokus |
|---------|-----------|-------------------------|------------|
| 01-oeffnungszeiten-frage.eml | Öffnungszeiten | REPLY_NEEDED | Draft nennt Öffnungszeiten aus context.md |
| 02-preis-anfrage.eml | Preis (Autowäsche) | REPLY_NEEDED | Draft verweist auf Preis-Aushang |
| 03-termin-anfrage.eml | Termin (Werkstatt) | REPLY_NEEDED | Draft mit Terminvorschlag oder Anruf-Aufforderung |
| 04-reklamation.eml | Reklamation | REPLY_NEEDED | Ton deeskalierend, Kontakt-Angebot |
| 05-newsletter.eml | Newsletter | IGNORE | Kein Draft |
| 06-amazon-bestellbestaetigung.eml | System-Mail | IGNORE | Kein Draft |
| 07-cold-sales.eml | Cold-Sales | IGNORE | Kein Draft |
| 08-delivery-failure.eml | MTA-Bounce | IGNORE | Kein Draft |
| 09-umlaut-frage.eml | UTF-8-Encoding | REPLY_NEEDED | Umlaute im Draft korrekt |
| 10-long-mail.eml | Long-Mail | REPLY_NEEDED | Truncation OK, Draft geht auf Kernfragen ein |
| 11-multi-turn-1-frage.eml | Multi-Turn (1/4) | REPLY_NEEDED | Erste Waschanlage-Frage ohne Vorgänger-Kontext |
| 12-multi-turn-2-rueckfrage.eml | Multi-Turn (2/4) | REPLY_NEEDED | Draft 12 kennt Kontext aus F11 |
| 13-multi-turn-3-detail.eml | Multi-Turn (3/4) | REPLY_NEEDED | Draft 13 kennt Kontext aus F11+F12 |
| 14-multi-turn-4-bestaetigung.eml | Multi-Turn (4/4) | REPLY_NEEDED | Draft 14 kennt Kontext aus F11+F12+F13 |

## Multi-Turn-Thread-Struktur (Fixtures 11-14)

Thread-Root: `<multi-turn-2026-07-11-t1@web.de>` (Fixture 11 — ohne In-Reply-To)

Jede Folge-Mail (Fixtures 12, 13, 14) enthält:
- `In-Reply-To: <vorherige-message-id>`
- `References: <alle vorherigen message-ids, chronologisch>`

Vollständige Header-Kette:

| Fixture | Message-ID | In-Reply-To | References |
|---------|-----------|-------------|------------|
| 11 | `<multi-turn-2026-07-11-t1@web.de>` | (keins) | (keins) |
| 12 | `<multi-turn-2026-07-11-t2@web.de>` | `<...t1@web.de>` | `<...t1@web.de>` |
| 13 | `<multi-turn-2026-07-11-t3@web.de>` | `<...t2@web.de>` | `<...t1@web.de> <...t2@web.de>` |
| 14 | `<multi-turn-2026-07-11-t4@web.de>` | `<...t3@web.de>` | `<...t1@web.de> <...t2@web.de> <...t3@web.de>` |

Damit die Thread-Erkennung in `imap_client.fetch_thread_history()` funktioniert,
müssen die 4 Mails NACHEINANDER ins Test-Postfach gesendet werden, mit einem
Poll-Zyklus dazwischen. Der Bot erzeugt zwischen jeder Runde einen Draft, der
(ab Fixture 12) den bisherigen Verlauf berücksichtigt.

Alle 4 Mails stammen vom selben Absender: `kunde-fischer@web.de`

## Nutzung im Test

Siehe `.planning/phases/02-deployment-beim-kunden/PRE-DEPLOYMENT-TEST.md`.

Die Mails werden am Test-Tag manuell an `shala@vizionists.com` gesendet (z. B. via
Zweit-Account oder mit `swaks` / `msmtp` per Skript). Der Bot pollt automatisch
und legt Drafts in `Vizpatch` an.

## RFC-5322-Konformität

Alle Fixtures:
- Haben einen Header-Block, getrennt durch Leerzeile vom Body
- Enthalten mindestens `From:`, `To:`, `Subject:`, `Date:`, `Message-ID:`, `Content-Type:`
- Nutzen `Content-Type: text/plain; charset=UTF-8` + `Content-Transfer-Encoding: 8bit`
- Sind parsebar via `email.message_from_file()` (Python stdlib)

Besonderheiten:
- Fixture 05: `List-Unsubscribe`-Header + `Precedence: bulk` (Newsletter-Erkennung)
- Fixture 08: `From: MAILER-DAEMON@...` + `Auto-Submitted: auto-replied` (Bounce-Erkennung)
- Fixture 09: Umlaute im Body (Ölwechsel, UTF-8-Encoding-Test)
- Fixture 10: Body > 2000 Zeichen (Truncation-Test im Klassifikations-Prompt)
