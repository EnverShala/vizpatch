#!/usr/bin/env bash
#
# check-addin-no-autosend.sh — Struktureller Kein-Auto-Send-Quellwächter
# für das VSTO-Outlook-classic-Add-in (Phase 8, Plan 08-04, OUT-09, D-87).
#
# Zweck
# -----
# Belegt maschinell (ohne Windows/VS/Outlook), dass der GESAMTE Add-in-
# Quellbaum unter outlook-addin/ KEINE Outlook-Schreib-/Sende-/Verschiebe-/
# Lösch-/Item-Erzeugungs-APIs aufruft. Kein-Auto-Send ist damit strukturell
# garantiert, nicht bloß per Konvention.
#
# Das ist das POSIX-Gegenstück zu den bereits im Repo etablierten Wächtern:
#   - webui/tests/test_addin_readonly.py  (JS-Taskpane: setAsync/saveAsync/…)
#   - webui/tests/test_chat_tools.py      (AST-Scan: kein SMTP-Send-Pfad)
# Es folgt demselben Muster: konkrete verbotene API-AUFRUF-Muster ("Wort(")
# statt blinder Substrings; Kommentare werden vor dem Gate entfernt, damit
# erklärende Prosa ("ruft KEINE .Send-APIs auf") den Wächter nicht selbst
# invalidiert.
#
# Verbotene Muster
# ----------------
# Eindeutig (immer verboten — keine False-Positive-Gefahr):
#   .Send(  .SaveAs(  .Reply(  .ReplyAll(  .Forward(  .CreateItem(
#   new Outlook.Application   CreateObject(
# Mehrdeutig (auf MailItem = verboten, auf lokalen Objekten = erlaubt):
#   .Save(  .Move(  .Delete(
#   Für diese drei Verben gilt eine ALLOWLIST bekannter, NICHT-Outlook-
#   Empfänger (lokale Settings-Persistenz + Datei-/Verzeichnis-APIs in den
#   Tests). Alles andere .Save(/.Move(/.Delete( ist ein Verstoß — ein
#   eingeschmuggeltes mail.Save(), item.Delete() oder mail.Move(trash) würde
#   also rot. (Gegenprobe: siehe unten "Counter-Proof".)
# Ausdrücklich ERLAUBT (rein lesend, matcht bewusst NICHT): .Subject,
#   .SenderEmailAddress, .Body, .CurrentItem, .Selection, .SendAsync( (HTTP,
#   kein Outlook — "Send" ohne unmittelbares "(").
#
# Exit-Code: 0 = sauber, 1 = mindestens ein Verstoß (Fundstellen ausgegeben).
#
# Nutzung:
#   bash scripts/check-addin-no-autosend.sh          # scannt outlook-addin/
#   bash scripts/check-addin-no-autosend.sh <dir>    # scannt <dir> (Counter-Proof)
#
# Counter-Proof (dokumentiertes Rot-Verhalten):
#   d=$(mktemp -d); printf 'class X { void f(){ mail.Send(); } }\n' > "$d/Probe.cs"
#   bash scripts/check-addin-no-autosend.sh "$d"     # -> Exit 1, meldet .Send(
#   rm -rf "$d"
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCAN_DIR="${1:-$ROOT/outlook-addin}"

if [ ! -d "$SCAN_DIR" ]; then
  echo "FEHLER: Scan-Verzeichnis nicht gefunden: $SCAN_DIR" >&2
  exit 2
fi

# --- 1. Quelldateien einsammeln (Build-Artefakte obj/ + bin/ ausgeschlossen) ---
mapfile -t CS_FILES < <(find "$SCAN_DIR" -type f -name '*.cs' \
  -not -path '*/obj/*' -not -path '*/bin/*' | sort)

if [ "${#CS_FILES[@]}" -eq 0 ]; then
  echo "FEHLER: keine *.cs-Quelldateien unter $SCAN_DIR gefunden." >&2
  exit 2
fi

# --- 2. Kommentar-Stripper: entfernt //-, ///-Zeilen- und /* */-Blockkommentare,
#        behält aber die Zeilennummer als Präfix, damit Fundstellen exakt sind. ---
strip_comments() {
  awk '
    BEGIN { inblock = 0 }
    {
      line = $0
      if (inblock) {
        idx = index(line, "*/")
        if (idx > 0) { line = substr(line, idx + 2); inblock = 0 }
        else { print NR ":"; next }
      }
      # Inline-Blockkommentare /* ... */ entfernen
      while ((s = index(line, "/*")) > 0) {
        rest = substr(line, s + 2)
        e = index(rest, "*/")
        if (e > 0) { line = substr(line, 1, s - 1) substr(rest, e + 2) }
        else { line = substr(line, 1, s - 1); inblock = 1; break }
      }
      # Zeilenkommentar // ... abschneiden (Code steht immer VOR dem //)
      c = index(line, "//")
      if (c > 0) line = substr(line, 1, c - 1)
      print NR ":" line
    }
  ' "$1"
}

# Kompletten Code-Stream als "datei:zeile:code" aufbauen (ohne Kommentare).
CODE_STREAM="$(
  for f in "${CS_FILES[@]}"; do
    rel="${f#"$ROOT"/}"
    strip_comments "$f" | while IFS= read -r numbered; do
      printf '%s:%s\n' "$rel" "$numbered"
    done
  done
)"

# --- 3. Muster ---
# Eindeutig verbotene Outlook-Schreib-/Sende-/Compose-Aufrufe.
UNAMBIGUOUS='\.Send\(|\.SaveAs\(|\.Reply\(|\.ReplyAll\(|\.Forward\(|\.CreateItem\(|new[[:space:]]+Outlook\.Application|CreateObject[[:space:]]*\('
# Mehrdeutige Verben (nur verboten, wenn NICHT auf einem erlaubten Empfänger).
AMBIGUOUS='\.Save\(|\.Move\(|\.Delete\('
# Allowlist: legitime Nicht-Outlook-Empfänger dieser Verben.
#   SecureSettingsStore.Save  -> lokale DPAPI-Settings-Persistenz (kein Outlook)
#   Directory.Delete/Move, File.Delete/Move -> Datei-System in den Tests
SAFE_RECEIVERS='SecureSettingsStore\.Save\(|Directory\.(Delete|Move)\(|File\.(Delete|Move)\('

FINDINGS=""

unamb="$(printf '%s\n' "$CODE_STREAM" | grep -E "$UNAMBIGUOUS" || true)"
if [ -n "$unamb" ]; then
  FINDINGS+="$unamb"$'\n'
fi

amb="$(printf '%s\n' "$CODE_STREAM" | grep -E "$AMBIGUOUS" | grep -Ev "$SAFE_RECEIVERS" || true)"
if [ -n "$amb" ]; then
  FINDINGS+="$amb"$'\n'
fi

# Leerzeilen entfernen
FINDINGS="$(printf '%s' "$FINDINGS" | grep -v '^[[:space:]]*$' || true)"

# --- 4. Ergebnis ---
FILE_COUNT="${#CS_FILES[@]}"
if [ -n "$FINDINGS" ]; then
  echo "KEIN-AUTO-SEND-WÄCHTER: VERSTOSS gefunden ($SCAN_DIR)" >&2
  echo "Verbotene Outlook-Schreib-/Sende-/Verschiebe-/Lösch-/Erzeugungs-APIs:" >&2
  printf '%s\n' "$FINDINGS" >&2
  echo "" >&2
  echo "-> Das Add-in darf ausschliesslich LESEN und die Chat-API sprechen." >&2
  exit 1
fi

echo "KEIN-AUTO-SEND-WÄCHTER: OK — $FILE_COUNT *.cs-Dateien unter ${SCAN_DIR#"$ROOT"/} geprüft, keine Outlook-Schreib-/Sende-APIs."
exit 0
