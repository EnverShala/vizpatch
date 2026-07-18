# Auftragsverarbeitungsvertrag (AVV) — Muster

**gemäß Art. 28 DSGVO — zwischen Betreiber und Vizionists**

> ⚠ **MUSTER / ENTWURF.** Dieses Dokument ist eine projektspezifische Vorlage, **kein Rechtsrat**.
> Vor Unterzeichnung von einer/einem Datenschutzbeauftragten oder Anwalt/Anwältin prüfen lassen.
> Platzhalter in [eckigen Klammern] ausfüllen.
>
> Ergänzend: die Betreiber-Checkliste liegt in `.planning/phases/02-deployment-beim-kunden/AVV-CHECKLIST.md`
> (Abschnitt 6 fasst die drei nötigen AVVs zusammen). Dieses Dokument ist der Vertrag **#2**
> (Betreiber ↔ Vizionists). Für #1 (Betreiber ↔ Anthropic) genügt Anthropics DPA in den Commercial
> Terms; für #3 (Betreiber ↔ OpenAI/Google) das jeweilige DPA — beide nur, wenn der Provider genutzt wird.

---

## §1 Parteien

**Verantwortlicher** (Auftraggeber, im Folgenden „Betreiber"):
- [Firmenname], [Anschrift], vertreten durch [Name]

**Auftragsverarbeiter** (Auftragnehmer, im Folgenden „Vizionists"):
- Vizionists, [Anschrift], vertreten durch [Name]

Dieser AVV gilt, **sobald Vizionists im Rahmen von Einrichtung, Wartung, Update oder Support
Zugriff auf personenbezogene Daten** des Betreibers (Server, Konfiguration, Logs, Postfach)
erhält. Betreibt der Betreiber Vizpatch vollständig selbst ohne jeden Vizionists-Zugriff, ist
kein AVV mit Vizionists erforderlich (dann genügt der Software-/Support-Vertrag).

## §2 Gegenstand und Dauer

- **Gegenstand:** Bereitstellung, Einrichtung und Wartung der selbst gehosteten Software **Vizpatch**
  (KI-gestützter E-Mail-Assistent) auf dem Server des Betreibers sowie zugehöriger Support.
- **Dauer:** Laufzeit des Software-/Dienstleistungsvertrags; endet mit dessen Beendigung.

## §3 Art, Umfang und Zweck der Verarbeitung

Vizpatch verarbeitet E-Mails des vom Betreiber konfigurierten Postfachs, um Kundenanfragen zu
klassifizieren, Antwort-**Entwürfe** zu erstellen (Ablage im Entwürfe-Ordner, **kein automatisches
Versenden**), ein Schreibstil-Profil abzuleiten und einen Assistenz-Chat mit Postfach-Werkzeugen
bereitzustellen (Suchen/Lesen, Entwurf umformulieren, Verschieben in den Papierkorb — Letzteres nur
nach ausdrücklicher Bestätigung des Betreibers, reversibel, kein endgültiges Löschen).

Vizionists verarbeitet personenbezogene Daten **ausschließlich weisungsgebunden** und nur, soweit
für die o. g. Leistungen erforderlich (Einrichtung, Fehleranalyse, Update, Support).

## §4 Art der Daten und Kategorien betroffener Personen

- **Datenarten:** E-Mail-Adresse (IMAP-Benutzer), E-Mail-Inhalte/Betreff/Absender (transient
  verarbeitet, nicht dauerhaft von Vizpatch gespeichert), abgeleitetes Stil-Profil, Betriebs-/
  Firmeninformationen (`context.md`), Zugangsdaten (IMAP-Passwort, API-Schlüssel — verschlüsselt).
- **Kategorien Betroffener:** Kunden/Absender des Betreibers, Beschäftigte des Betreibers.
- Es werden **keine besonderen Kategorien** (Art. 9 DSGVO) gezielt verarbeitet; PII-Muster
  (IBAN/Kreditkarten) werden vor der KI-Übermittlung maskiert.

## §5 Pflichten von Vizionists (Art. 28 Abs. 3)

1. **Weisungsbindung:** Verarbeitung nur nach dokumentierter Weisung des Betreibers; keine
   Zweckänderung. Hält Vizionists eine Weisung für rechtswidrig, wird der Betreiber informiert.
2. **Vertraulichkeit:** Zur Verschwiegenheit verpflichtete Personen; Zugriff nur „need to know".
3. **Datensicherheit (Art. 32):** siehe §6 (TOMs).
4. **Unter-Auftragsverarbeiter:** nur mit Genehmigung des Betreibers; siehe §7.
5. **Unterstützung** des Betreibers bei Betroffenenrechten (Art. 12–23), bei Meldepflichten
   (Art. 33/34) und ggf. Datenschutz-Folgenabschätzung (Art. 35).
6. **Löschung/Rückgabe:** Nach Vertragsende werden dem Vizionists zugängliche personenbezogene
   Daten gelöscht oder zurückgegeben; die WebUI-„Zurücksetzen"-Funktion löscht Konfiguration,
   Kontext, Stil-Profil, lokalen Verarbeitungs-Status und den Verschlüsselungsschlüssel.
7. **Nachweis-/Auditrechte:** Vizionists stellt die zur Nachweisführung erforderlichen
   Informationen bereit und ermöglicht Überprüfungen durch den Betreiber.
8. **Meldung von Verletzungen** des Schutzes personenbezogener Daten unverzüglich an den Betreiber.

## §6 Technisch-organisatorische Maßnahmen (TOMs, Art. 32)

- **Self-Hosting:** Betrieb ausschließlich auf dem Server des Betreibers; keine zentrale
  Datenhaltung bei Vizionists.
- **Verschlüsselung at-rest:** IMAP-Passwort und API-Schlüssel Fernet/AES-verschlüsselt;
  Schlüsseldatei mit eingeschränkten Rechten (chmod 600).
- **Datenminimierung:** E-Mail-Inhalte werden nur transient verarbeitet, nicht dauerhaft gespeichert
  (nur Message-ID-Kennungen zur Doppelverarbeitungs-Vermeidung).
- **PII-Maskierung** (IBAN/Kreditkarten) vor jeder KI-Übermittlung.
- **Kein-Auto-Send:** strukturell kein Mail-Versand; destruktive Aktionen (Papierkorb) nur nach
  bestätigungs-gebundenem Token, reversibel (kein Expunge), protokolliert.
- **Zugriffsschutz:** WebUI optional login-/bcrypt-geschützt; non-root-Container; Docker-Isolierung.
- **Verantwortung Betreiber:** Serverabsicherung, Backups, ggf. HTTPS-Reverse-Proxy.

## §7 Unter-Auftragsverarbeiter (Sub-Prozessoren)

Der Betreiber genehmigt folgende Unter-Auftragsverarbeiter für die KI-Verarbeitung (je nach
hinterlegtem API-Schlüssel; nur der tatsächlich genutzte Anbieter ist relevant):

| Unter-AV | Zweck | Ort | Absicherung |
|---|---|---|---|
| Anthropic PBC / Anthropic Ireland Ltd. | LLM-Inferenz (Klassifikation, Draft, Stil, Chat) | EU/USA | DPA in Commercial Terms, EU-SCC Modul 2+3, optional ZDR |
| OpenAI (nur falls genutzt) | LLM-Inferenz | EU/USA | OpenAI DPA + SCC |
| Google (nur falls genutzt) | LLM-Inferenz | EU/USA | Google DPA + SCC |

Vizionists informiert den Betreiber über beabsichtigte Änderungen (Hinzufügen/Ersetzen) von
Unter-Auftragsverarbeitern; der Betreiber kann widersprechen.

## §8 Drittlandübermittlung

Soweit der KI-Anbieter Daten außerhalb der EU (z. B. USA) verarbeitet, erfolgt die Übermittlung
auf Grundlage der **EU-Standardvertragsklauseln (SCC)** bzw. eines Angemessenheitsbeschlusses.
Zur Datensparsamkeit wird — soweit vom Anbieter unterstützt — **Zero-Data-Retention** angefragt.

## §9 Schlussbestimmungen

- Änderungen bedürfen der Textform.
- Bei Widerspruch zwischen diesem AVV und dem Hauptvertrag gilt für den Datenschutz dieser AVV.
- Es gilt deutsches Recht.

---

**Unterschriften**

Betreiber: ______________________  Ort/Datum: ____________

Vizionists: _____________________  Ort/Datum: ____________

---
*Muster erstellt 2026-07-18 für Vizpatch v1.5. Vor Verwendung rechtlich prüfen lassen.*
