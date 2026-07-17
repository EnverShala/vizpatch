# AVV / DSGVO-Checklist (PRE-04)

> ⚠ **BLOCKER-Status:** Dieser Punkt MUSS abgeschlossen sein BEVOR der Vor-Ort-Termin startet.
> Ohne wirksamen AVV/DPA-Rahmen darf der Bot keine echten Kunden-Mails verarbeiten.

## Zielsetzung

Der Betreiber (Auftraggeber der Verarbeitung) muss vor der ersten Live-Verarbeitung nachweisen können:

1. Ein wirksamer AVV/DPA mit Anthropic besteht.
2. Die Übermittlung in die USA ist DSGVO-konform abgesichert (EU-SCCs).
3. Es gibt eine Records-of-Processing-Notiz gemäß Art. 30 DSGVO.
4. Recht auf Löschung (Art. 17) ist technisch umgesetzt.
5. Datenminimierung (Art. 5) ist gegeben.

---

## 1. Anthropic-Vertragsrahmen

### Fakten (Recherche 2026-07-11)

- **AVV / DPA:** Der Anthropic Data Processing Agreement (DPA) ist automatisch in den **Anthropic Commercial Terms** eingebettet. Er gilt für alle bezahlten API-Accounts. **Kein separater PDF-Download nötig.**
- **EU-SCCs:** Modul 2 + 3 (Controller-to-Processor + Processor-to-Sub-Processor) sind automatisch im DPA enthalten.
- **Standard-Retention:** 7 Tage seit September 2025 (war vorher 30 Tage). Daten werden NICHT zum Model-Training genutzt.
- **ZDR (Zero Data Retention):** ⚠ **ZDR ist KEIN HTTP-Header oder API-Parameter.** ZDR wird per Vertragsanhang aktiviert — Antrag bei `sales@anthropic.com` oder über die Anthropic-Console.

### Checkliste

- [ ] Anthropic-Account existiert und ist als "Commercial Account" markiert. Verifikation: Anthropic-Console → Settings → Billing.
- [ ] Commercial Terms wurden bei Account-Setup akzeptiert (elektronische Zustimmung). Verifikation: Anthropic-Console zeigt keinen "Terms not accepted"-Banner mehr.
- [ ] Zustimmung ist im Namen des Betreibers erfolgt (nicht als Privatperson des Vizionists-Mitarbeiters).
- [ ] ZDR-Entscheidung getroffen:
    - Option A: 7-Tage-Retention akzeptabel → **KEINE Aktion nötig, Standard gilt.**
    - Option B: ZDR gewünscht → Antrag bei `sales@anthropic.com` mit Firmen-Details, DSGVO-Sensitivität begründen. Wartezeit typischerweise 1–4 Wochen. **BLOCKER falls Option B.**
- [ ] Entscheidung dokumentieren: [ ] Option A (Standard 7 Tage)  [ ] Option B (ZDR, Wartezeit ___)

---

## 2. Records of Processing (Art. 30 DSGVO)

Der Betreiber (nicht Vizionists) führt das Verzeichnis der Verarbeitungstätigkeiten. Für die KI-Email-Verarbeitung ist folgender Eintrag anzulegen:

```
Verarbeitungstätigkeit:      Automatisierte Erstellung von Antwort-Entwürfen auf Kunden-E-Mails via LLM
Verantwortlicher:            <Tankstelle GmbH, Adresse, USt-ID>
Auftragsverarbeiter:         Anthropic PBC / Anthropic Ireland Limited
Kategorien betroffener
Personen:                    Kunden der Tankstelle (Absender eingehender E-Mails)
Kategorien Daten:            E-Mail-Inhalt (Text), Absender-E-Mail-Adresse,
                             Betreff, ggf. E-Mail-Signatur/Kontaktdaten
Zweck:                       Vorbereitung von Antwortvorschlägen für den Betreiber;
                             kein automatisches Versenden
Rechtsgrundlage:             Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an
                             effizienter Kundenkommunikation) UND Art. 6 Abs. 1 lit. b
                             (Vertragsanbahnung/-erfüllung)
Datenübermittlung:           USA (Anthropic PBC), abgesichert durch EU-SCCs
                             Modul 2+3 (im DPA eingebettet)
Speicherdauer bei
Anthropic:                   max. 7 Tage (Standard) oder 0 Tage (ZDR falls aktiviert)
Speicherdauer im
Postfach des Betreibers:     Postfach-Retention gemäß IMAP-Provider,
                             keine zusätzliche Speicherung durch den Bot
Technisch-organisatorische
Maßnahmen:                   - PII-Redaction für IBAN/Kreditkarten vor LLM-Call
                             - .env chmod 600 (Secrets-Schutz)
                             - Non-root Container-User (uid 1000)
                             - Kein Auto-Send (Draft-only, Betreiber-Freigabe zwingend)
                             - Live-Fetch statt Bot-DB-Kopie (D-26)
```

- [ ] Records-of-Processing-Eintrag ist im Betreiber-Verzeichnis angelegt.

---

## 3. Recht auf Löschung (Art. 17 DSGVO)

**Umsetzung:** Der Bot legt KEINE eigene Kopie der Mails an (D-26 Live-Fetch aus IMAP). Wenn der Betreiber eine Mail aus dem Postfach löscht, ist sie automatisch aus dem Kontext des Bots verschwunden.

- [ ] Betreiber ist informiert, dass Löschen einer Mail im Postfach die Bot-Sicht sofort mit-löscht (kein separater Lösch-Prozess nötig).
- [ ] Lösch-Anfragen von Kunden werden vom Betreiber im Postfach umgesetzt (keine Vizionists-Aktion nötig).

---

## 4. Datenminimierung (Art. 5 DSGVO)

**Umsetzung:** Der Bot lädt bei jedem Draft-Zyklus nur die JETZT relevanten Mails aus IMAP (Thread-Suche + max 30-Tage-Absender-Fallback, max. 6 Nachrichten, Body-Truncation 800 Zeichen). Kein "Alle Mails lesen und speichern".

- [ ] Konfiguration `ENABLE_PII_REDACTION=true` ist gesetzt (Regex-Redaction für IBAN + Kreditkarten vor LLM-Call).

---

## 5. `.env`-Sicherheit

- [ ] `.env` auf Kundenserver hat `chmod 600` (nur owner lesbar).
- [ ] `.env` enthält keine Passwörter in der Terminal-History (mit `nano` bearbeiten, nicht `export`).
- [ ] `.env` ist NICHT in einem `git`-Repo (Kundenserver hat kein Git nach D-05).

---

## 6. Nachtrag v1.2–v1.4 (Stand 2026-07-17) — erweiterte Verarbeitung

> Die Abschnitte 1–5 entstanden für den reinen Anthropic-Draft-Betrieb (v1.0/v1.1).
> Seit v1.2–v1.4 sind neue Verarbeitungszwecke und Rollen hinzugekommen. Dieser
> Nachtrag ergänzt die Checkliste. **Muster — final rechtlich prüfen lassen.**

### 6.1 Wer schließt mit wem welchen AVV?

| # | Parteien | Rolle | Pflicht? | Inhalt-Besonderheit |
|---|---|---|---|---|
| 1 | Betreiber ↔ **Anthropic** | Controller ↔ Processor | Ja (bei Anthropic-Nutzung) | DPA in Commercial Terms eingebettet, EU-SCC Modul 2+3, ZDR optional |
| 2 | Betreiber ↔ **Vizionists** | Controller ↔ Processor | Ja, sobald Vizionists Zugriff auf Server/Config/Logs/Postfach hat (Einrichtung/Wartung/Support) | KI-Anbieter als **Unter-Auftragsverarbeiter** benennen |
| 3 | Betreiber ↔ **OpenAI** bzw. **Google** | Controller ↔ Processor | Nur falls dieser Provider per API-Key genutzt wird (Phase 5) | jeweiliges DPA + Drittland-Absicherung analog Anthropic |

### 6.2 Neue Verarbeitungszwecke (in Art.-30-Verzeichnis + AVV aufnehmen)

- [ ] **Schreibstil-Ableitung (Phase 6):** einmalige LLM-Verarbeitung der letzten Mails des *Gesendet*-Ordners; gespeichert wird nur ein abstrahiertes Stil-Profil (`style.md`), keine Mail-Inhalte.
- [ ] **Agenten-Chat (Phase 7):** Betreiber-Anfragen + injizierter Kontext/Status gehen an den KI-Anbieter; Kein-Auto-Send gilt auch hier.
- [ ] **Outlook-Add-in (Phase 8):** die geöffnete Mail (Betreff/Absender/Body) wird via Office.js in den Chat gereicht → an den KI-Anbieter; rein lesend (ReadItem).

### 6.3 Vizionists als Auftragsverarbeiter — AVV-Pflichtinhalt (Art. 28 Abs. 3)

- [ ] Gegenstand, Dauer, Art & Zweck der Verarbeitung, Datenarten, Kategorien Betroffener
- [ ] Weisungsbindung + Vertraulichkeit
- [ ] TOMs (Art. 32): Fernet-Verschlüsselung at-rest, chmod-600-Schlüsseldatei, Self-Hosting, PII-Maskierung, Kein-Auto-Send
- [ ] **Unter-Auftragsverarbeiter** (Anthropic; ggf. OpenAI/Google) benannt + genehmigt
- [ ] Unterstützung bei Betroffenenrechten & Meldepflichten (Art. 33/34)
- [ ] Löschung/Rückgabe nach Vertragsende (WebUI-Reset löscht Config + Kontext + Stil + State + Schlüssel)
- [ ] Audit-/Nachweisrechte des Betreibers
- [ ] Bei OpenAI/Google zusätzlich: Drittland-Transfer per SCC

### 6.4 Verhältnis zur WebUI-Einwilligung

- [ ] Die im WebUI implementierte **Pflicht-Checkbox „Datenschutzbestimmungen"** deckt die *Betreiber-Einwilligung* zur beschriebenen Verarbeitung ab (Art. 6 Abs. 1 lit. a). Sie **ersetzt nicht** die AVVs #1–#3 — das sind separate Verträge zwischen den Unternehmen. Beides ist nötig.
- [ ] Platzhalter in der Datenschutzerklärung (`webui/src/templates/_datenschutz.html`) mit echten Betreiber-Angaben ausgefüllt.

---

## Freigabe

- [ ] Alle Punkte in Abschnitt 1–6 sind ✅
- [ ] Optional: Datenschutzbeauftragter der Tankstelle (falls vorhanden) hat den Vorgang zur Kenntnis genommen

**AVV/DSGVO-Bereit für Live-Verarbeitung?** [ ] Ja  [ ] Nein — Blocker: ______________

**Bestätigt durch:** ______________ (Betreiber) und ______________ (Vizionists) am ______________
