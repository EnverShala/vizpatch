# README.addin.md — Outlook-Add-in-Betrieb (Phase 8, v1.4)

Ergänzt `README.phase4.md` um den Betrieb des Outlook-Add-ins (Taskpane +
Agenten-Chat, `/addin/taskpane.html` + `/addin/manifest.xml`). Vier Kapitel:
HTTPS, `ADDIN_BASE_URL`, Verteilung (Sideloading/M365), Auth-Fluss & Read-only.

---

## 1. HTTPS vor der WebUI (Reverse-Proxy)

**Warum HTTPS Pflicht ist:** Outlook lädt Add-in-Ressourcen (Taskpane-HTML,
Manifest, Office.js-Postback) nur über HTTPS — der Outlook-Webview verbietet
Mixed-Content (HTTPS-Seite lädt HTTP-Ressource) kategorisch. Ohne HTTPS lässt
sich das Add-in nicht sideloaden, unabhängig davon, ob es lokal funktioniert.

**Setup mit Caddy** (siehe `Caddyfile.example`):

```bash
cd /opt/vizpatch
cp deployment/Caddyfile.example Caddyfile
nano Caddyfile   # Domain aus Variante A/B eintragen
```

Caddy terminiert TLS extern und leitet per `reverse_proxy` an die WebUI auf
`localhost:8080` (bzw. `vizpatch-webui:8080` im selben Docker-Netz) weiter.
Die WebUI selbst bleibt unverändert auf reinem HTTP innerhalb des
Docker-Netzes — kein Zertifikat im WebUI-Container nötig.

**Zertifikat:**
- **Öffentliche Domain (Standard):** Caddy holt automatisch ein
  Let's-Encrypt-Zertifikat (ACME-HTTP-Challenge, benötigt Port 80+443 extern
  erreichbar sowie einen DNS A/AAAA-Record auf den Server).
- **Reine LAN-Installation** (kein öffentlicher DNS-Eintrag): `tls internal`
  in der Caddyfile (Variante B in `Caddyfile.example`) — Caddy signiert
  selbst. Outlook-Clients im LAN müssen dem Caddy-Root-CA-Cert einmalig
  vertrauen (auf den Client-Rechnern importieren), sonst zeigt der
  Outlook-Webview eine Zertifikatswarnung.

**Ports/Firewall:** Caddy braucht 80 (nur für die Let's-Encrypt-Challenge)
und 443 (HTTPS) extern erreichbar. Der WebUI-Port **8080 selbst darf NICHT**
extern exponiert werden — siehe die Sicherheits-Warnung in `README.phase4.md`
(Docker-Socket-Zugriff über die WebUI ist root-äquivalent). Nur Caddy
terminiert nach außen, die WebUI bleibt innerhalb des Docker-Netzes/localhost.

**`frame-ancestors`-Hinweis:** Die Add-in-Routen (`/addin/*`,
`/chat/*/embed`) liefern bereits eine eigene, gelockerte
Content-Security-Policy inklusive `frame-ancestors` — und bewusst **kein**
`X-Frame-Options`, weil dieser Header nur `DENY`/`SAMEORIGIN` kennt und den
Cross-Origin-Outlook-Webview sonst blockieren würde. **Der Reverse-Proxy darf
diese Header nicht überschreiben, entfernen oder durch eigene
Security-Header-Direktiven ersetzen** — Caddy in der mitgelieferten
`Caddyfile.example` tut das nicht (keine `header`-Direktive für
Security-Header), das muss so bleiben, falls die Caddyfile erweitert wird.

## 2. `ADDIN_BASE_URL` setzen

`ADDIN_BASE_URL` ist die öffentliche HTTPS-URL aus Kapitel 1 — also exakt die
Domain, die in der Caddyfile terminiert wird (z. B.
`https://vizpatch.<kunde-domain>.de`).

```bash
cd /opt/vizpatch
nano config/.env
# ADDIN_BASE_URL=https://vizpatch.<kunde-domain>.de eintragen (https:// Pflicht)
docker compose restart webui
```

**Kontrolle:**
```bash
curl -I https://<ADDIN_BASE_URL>/addin/taskpane.html   # muss 200 liefern
curl https://<ADDIN_BASE_URL>/addin/manifest.xml       # muss XML liefern, kein Fehler
```

`/addin/taskpane.html` muss laden (die Taskpane-Shell). `/addin/manifest.xml`
muss wohlgeformtes XML liefern, in dem `ADDIN_BASE_URL` bereits korrekt
eingesetzt ist (`{ADDIN_BASE_URL}`-Platzhalter → echte URL). Ein
`400`-Fehler an dieser Stelle bedeutet meist: `ADDIN_BASE_URL` fehlt, beginnt
nicht mit `https://`, oder enthält unzulässige Zeichen (`<`, `>`, `"`, `&`).

## 3. Add-in verteilen

### (a) Sideloading — neues Outlook + Outlook im Web (OWA)

1. Manifest herunterladen: `https://<ADDIN_BASE_URL>/addin/manifest.xml`
   im Browser aufrufen und als Datei speichern (z. B. `vizpatch-addin.xml`).
2. In Outlook (neues Outlook für Windows/Mac ODER Outlook im Web):
   - **„Add-Ins verwalten"** öffnen (Zahnrad-Symbol bzw. Menüpunkt „Get
     Add-ins" / „Add-Ins abrufen").
   - **„Eigenes Add-In hinzufügen"** (My add-ins → Add a custom add-in) →
     **„Aus Datei"** (Add from file) wählen.
   - Die gespeicherte `vizpatch-addin.xml` auswählen und hochladen.
3. Das Add-in erscheint im Lesefenster einer geöffneten Mail (Taskpane-Icon
   im Ribbon/Menüband). Klick öffnet die Taskpane mit Agenten-Dropdown +
   eingebettetem Chat.

**Hinweis:** Sideloading ist pro Benutzer/Postfach individuell — jeder
Benutzer, der das Add-in nutzen soll, muss diesen Schritt selbst durchführen
(oder Kapitel (b) nutzen).

### (b) Zentrale M365-Admin-Verteilung (Alternative)

Für die Verteilung an alle oder ausgewählte Nutzer eines M365-Tenants ohne
individuelles Sideloading:

1. Microsoft 365 Admin Center öffnen (`admin.microsoft.com`) — benötigt
   **Global-Admin** oder **Exchange-Admin**-Rechte.
2. **„Integrierte Apps"** (Integrated apps) → **„Add-In hochladen"** (Upload
   custom apps).
3. Die Manifest-URL (`https://<ADDIN_BASE_URL>/addin/manifest.xml`) angeben
   oder die heruntergeladene Manifest-Datei hochladen.
4. Zielgruppe wählen: bestimmte Nutzer, Gruppen, oder der gesamte Tenant.
5. Ausrollen — betroffene Nutzer sehen das Add-in nach kurzer Zeit
   automatisch in Outlook, ohne selbst sideloaden zu müssen.

Diese Variante ist der empfohlene Weg bei mehreren Nutzern im selben
M365-Tenant (z. B. mehrere Mitarbeiter-Postfächer bei einem Kunden).

## 4. Auth-Fluss & Read-only

**Auth-Fluss:** Die Taskpane iframed same-origin `/chat/{agent_id}/embed`
(kein Cross-Origin-Problem, siehe D-66/08-01-SUMMARY). Sie nutzt dabei
**exakt das bestehende WebUI-Auth-Regime** — es gibt kein separates
Add-in-Login-System. Ist `WEBUI_USER`/`WEBUI_PASSWORD` gesetzt (optionales
Basic-Auth, siehe `README.phase4.md`), zeigt der Outlook-Webview beim ersten
Laden der Taskpane den Basic-Auth-Prompt **im iframe/Taskpane-Fenster** —
der Nutzer meldet sich dort einmal mit denselben Zugangsdaten an wie im
normalen Browser-Zugriff auf die WebUI.

**Empfehlung:** `WEBUI_USER`/`WEBUI_PASSWORD` setzen, sobald die WebUI über
`ADDIN_BASE_URL` öffentlich (auch nur LAN-weit) erreichbar ist — ohne Login
könnte jeder mit Netzwerkzugriff auf die URL den Agenten-Chat nutzen.

**Read-only / Kein-Auto-Send:** Das Add-in ist **strikt rein lesend**. Es
liest ausschließlich die aktuell geöffnete Mail (Betreff, Absender, Body via
Office.js `Office.context.mailbox.item`) und reicht diese als Kontext an den
Chat weiter (`/addin/manifest.xml` erlaubt ausschließlich die Berechtigung
`ReadItem`, keine `ReadWriteItem`/`ReadWriteMailbox`). Das Add-in **erzeugt,
ändert oder sendet niemals Mails** — es ruft keine Office-Schreib-/Compose-/
Send-APIs auf (strukturell abgesichert, siehe
`webui/tests/test_addin_readonly.py`). Dieses Prinzip gilt projektweit
(Kein-Auto-Send, siehe `CLAUDE.md`) und wurde für das Add-in nicht
abgeschwächt.

---

## Verwandte Artefakte

- `deployment/Caddyfile.example` — Reverse-Proxy-Vorlage (Kapitel 1)
- `deployment/kunde-env.example` — `ADDIN_BASE_URL`/`ADDIN_FRAME_ANCESTORS`
  im Setup-Kontext (Kapitel 2)
- `GET /addin/taskpane.html` — Taskpane-Shell (Agenten-Dropdown + Chat-iframe)
- `GET /addin/manifest.xml` — pro Installation über `ADDIN_BASE_URL`
  templatisiertes XML-Manifest
- `README.phase4.md` — Basis-Deployment (Zero-Config-Setup, Sicherheit,
  Update/Rollback)
