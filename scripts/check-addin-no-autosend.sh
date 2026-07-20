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

# --- 2. Lexer-basierter Kommentar-/String-Stripper (WR-02): entfernt //-, ///-
#        Zeilen- und /* */-Blockkommentare UND den Inhalt von String-/Char-
#        Literalen, bevor gescannt wird. Damit koennen weder ein String-internes
#        "https://…" den Rest der Zeile vor dem Scan verstecken, noch ein in einem
#        String-Literal stehendes "mail.Send()" den Waechter selbst invalidieren.
#        Die Zeilennummer bleibt als Präfix erhalten, damit Fundstellen exakt sind. ---
strip_comments() {
  awk '
    BEGIN { inblock = 0 }
    {
      line = $0
      out = ""
      n = length(line)
      i = 1
      instr = 0    # innerhalb "..."
      inchar = 0   # innerhalb '\''...'\''
      while (i <= n) {
        c = substr(line, i, 1)
        two = substr(line, i, 2)
        if (inblock) {
          if (two == "*/") { inblock = 0; i += 2; continue }
          i++; continue
        }
        if (instr) {
          if (c == "\\") { i += 2; continue }   # Escape im String ueberspringen
          if (c == "\"") { instr = 0 }
          i++; continue                          # String-Inhalt verwerfen
        }
        if (inchar) {
          if (c == "\\") { i += 2; continue }
          if (c == "'\''") { inchar = 0 }
          i++; continue                          # Char-Inhalt verwerfen
        }
        # Normaler Code
        if (two == "/*") { inblock = 1; i += 2; continue }
        if (two == "//") { break }               # Rest der Zeile ist Kommentar
        if (c == "\"") { instr = 1; i++; continue }
        if (c == "'\''") { inchar = 1; i++; continue }
        out = out c
        i++
      }
      print NR ":" out
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
# Optionaler Whitespace vor '(' (WR-04): C# erlaubt 'mail.Send ()' oder einen
# Zeilenumbruch vor der Klammer. [[:space:]]* faengt das (zeilenintern) mit.
# Eindeutig verbotene Outlook-Schreib-/Sende-/Compose-Aufrufe.
#   Application-Erzeugung alias-unabhaengig (WR-04): matcht 'new Outlook.Application('
#   ebenso wie 'new OL.Application(' (beliebiger using-Alias) oder unqualifiziert
#   'new Application('. 'new ApplicationException(' bleibt unberuehrt (nach
#   'Application' folgt kein '(').
# Die '...[[:space:]]*$'-Alternativen fangen zusaetzlich den Fall, dass das '('
# erst in der naechsten Zeile steht (Zeilenumbruch vor der Klammer, WR-04): ein
# Compose-Verb am Zeilenende ist hier immer verdaechtig — kein rein lesender
# Zugriff endet exakt auf '.Send'/'.SaveAs'/'.Reply'/'.Forward'/'.CreateItem'
# ('.SendAsync'/'.Sender' enden anders und matchen daher nicht).
UNAMBIGUOUS='\.Send[[:space:]]*(\(|$)|\.SaveAs[[:space:]]*(\(|$)|\.Reply[[:space:]]*(\(|$)|\.ReplyAll[[:space:]]*(\(|$)|\.Forward[[:space:]]*(\(|$)|\.CreateItem[[:space:]]*(\(|$)|new[[:space:]]+([A-Za-z_][A-Za-z0-9_]*\.)*Application[[:space:]]*\(|CreateObject[[:space:]]*\('
# Mehrdeutige Verben (nur verboten, wenn NICHT auf einem erlaubten Empfänger).
AMBIGUOUS='\.Save[[:space:]]*\(|\.Move[[:space:]]*\(|\.Delete[[:space:]]*\('
# Allowlist: legitime Nicht-Outlook-Empfänger dieser Verben.
#   SecureSettingsStore.Save  -> lokale DPAPI-Settings-Persistenz (kein Outlook)
#   Directory.Delete/Move, File.Delete/Move -> Datei-System in den Tests
SAFE_RECEIVERS='SecureSettingsStore\.Save[[:space:]]*\(|Directory\.(Delete|Move)[[:space:]]*\(|File\.(Delete|Move)[[:space:]]*\('

FINDINGS=""

unamb="$(printf '%s\n' "$CODE_STREAM" | grep -E "$UNAMBIGUOUS" || true)"
if [ -n "$unamb" ]; then
  FINDINGS+="$unamb"$'\n'
fi

# Mehrdeutige Verben (WR-03): NICHT die ganze Zeile per Allowlist verwerfen —
# sonst versteckt 'SecureSettingsStore.Save(s); mail.Delete();' das mail.Delete().
# Stattdessen die erlaubten Empfänger-Aufrufe aus dem Code entfernen (nur fuer den
# Test) und pruefen, ob DANACH noch ein mehrdeutiges Verb uebrig bleibt. Gemeldet
# wird die urspruengliche Zeile.
# Nur Zeilen, die ueberhaupt ein mehrdeutiges Verb enthalten, durchlaufen den
# (teureren) Strip-Recheck — haelt den Wächter schnell (kein sed pro Quellzeile).
amb_candidates="$(printf '%s\n' "$CODE_STREAM" | grep -E "$AMBIGUOUS" || true)"
amb=""
if [ -n "$amb_candidates" ]; then
  amb="$(printf '%s\n' "$amb_candidates" | while IFS= read -r ln; do
    stripped="$(printf '%s' "$ln" | sed -E "s/($SAFE_RECEIVERS)//g")"
    if printf '%s' "$stripped" | grep -Eq "$AMBIGUOUS"; then
      printf '%s\n' "$ln"
    fi
  done)"
fi
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
