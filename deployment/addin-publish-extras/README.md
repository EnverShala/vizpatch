# addin-publish-extras

Zwei Helfer-Skripte, die das Build-Skript (`scripts/build-deployment-package.sh`)
in **jedes** `addin-publish/`-Bundle des Deployment-Pakets kopiert — sie liegen
dann neben `setup.exe` und `VizpatchAddin.vsto` und lösen am Kunden-PC das
„Windows hat Ihren PC geschützt" / „Herausgeber nicht verifiziert"-Problem.

- **`INSTALLIEREN.cmd`** — empfohlener Weg für den Kunden: Doppelklick → entfernt
  die Download-Sperre (Mark of the Web), richtet das Vertrauen ein und startet
  `setup.exe`.
- **`vertrauen-einrichten.ps1`** — die eigentliche Logik: `Unblock-File` über alle
  Paket-Dateien + Import des **öffentlichen** Signatur-Zertifikats (gelesen aus
  `VizpatchAddin.vsto`) in TrustedPublisher/Root (Benutzer- oder Maschinen-Store
  je nach Rechten).

**Keine Secrets:** Das Zertifikat wird zur Laufzeit aus dem ohnehin verteilten
`.vsto`-Manifest gelesen (öffentlicher Teil, kein privater Schlüssel). Deshalb
versioniert (nicht gitignored) — nur so ist der Paket-Build aus einem frischen
Clone reproduzierbar.
