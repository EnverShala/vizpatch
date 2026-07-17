"""Struktureller Kein-Auto-Send-Wächter für das Outlook-Add-in
(Phase 8, Plan 08-02, OUT-04/D-70).

Analog zum Phase-7-Guard-Muster (test_endpoints_chat.py::
test_chat_py_source_has_no_mail_write_or_send_path): prüft konkrete
verbotene API-Muster statt blinder Zufalls-Substrings, ignoriert
Kommentarzeilen, damit erklärende Kommentare den Wächter nicht selbst
invalidieren.

Deckt ab:
(a) taskpane.js enthält KEINES der Office-Schreib-/Compose-/Send-Muster
    (setAsync, saveAsync, displayReplyForm, displayReplyAllForm,
    displayNewMessageForm, makeEwsRequestAsync, sendAsync) — lesende
    getAsync/addHandlerAsync sind erlaubt
(b) addin_manifest.xml enthält Permission == ReadItem und WEDER
    ReadWriteItem NOCH ReadWriteMailbox
(c) Negativ-Fall (bewusst eingefügtes verbotenes Muster) wird vom
    JS-Wächter tatsächlich erkannt — belegt, dass der Test nicht durch
    Zufall immer grün ist
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

TASKPANE_JS = Path(__file__).resolve().parent.parent / "static" / "addin" / "taskpane.js"
ADDIN_MANIFEST_XML = Path(__file__).resolve().parent.parent / "src" / "templates" / "addin_manifest.xml"

FORBIDDEN_OFFICE_WRITE_PATTERNS = (
    "setAsync",
    "saveAsync",
    "displayReplyForm",
    "displayReplyAllForm",
    "displayNewMessageForm",
    "makeEwsRequestAsync",
    "sendAsync",
)


def _code_lines(text: str) -> list[str]:
    """Filtert Kommentarzeilen (// und Block-Kommentar-Zeilen innerhalb /* */)
    heraus, damit erklärende Kommentare wie "kein setAsync" den Wächter nicht
    selbst-invalidieren (analog zum Phase-7-Muster, das # und \"\"\"-Zeilen
    ignoriert)."""
    lines = []
    in_block_comment = False
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if in_block_comment:
            if "*/" in stripped:
                in_block_comment = False
            continue
        if stripped.startswith("/*"):
            if "*/" not in stripped:
                in_block_comment = True
            continue
        if stripped.startswith("//") or stripped.startswith("*"):
            continue
        lines.append(raw_line)
    return lines


def _find_forbidden_write_calls(js_text: str) -> list[str]:
    findings = []
    for line in _code_lines(js_text):
        for pattern in FORBIDDEN_OFFICE_WRITE_PATTERNS:
            if pattern in line:
                findings.append(f"{pattern} in: {line.strip()}")
    return findings


def test_taskpane_js_has_no_office_write_or_send_apis():
    js_text = TASKPANE_JS.read_text(encoding="utf-8")
    findings = _find_forbidden_write_calls(js_text)
    assert findings == [], f"taskpane.js enthaelt verbotene Office-Schreib-/Send-APIs: {findings}"


def test_taskpane_js_still_uses_permitted_read_apis():
    """Gegenprobe: die erlaubten lesenden APIs sind tatsaechlich vorhanden —
    sonst waere der obige Test trivial gruen, weil taskpane.js leer ist."""
    js_text = TASKPANE_JS.read_text(encoding="utf-8")
    assert "getAsync" in js_text
    assert "addHandlerAsync" in js_text


def test_guard_detects_injected_forbidden_write_pattern():
    """Negativ-Fall: belegt, dass _find_forbidden_write_calls tatsaechlich
    anschlaegt, wenn ein verbotenes Muster im Code (nicht im Kommentar)
    auftaucht — der Wächter ist kein Blindgänger."""
    poisoned = "function evil() {\n  item.body.setAsync('x', function () {});\n}\n"
    findings = _find_forbidden_write_calls(poisoned)
    assert findings != []


def test_guard_ignores_forbidden_pattern_mentioned_only_in_comments():
    """Ein erklärender Kommentar, der z. B. 'kein setAsync' erwähnt, darf den
    Wächter NICHT triggern (False-Positive-Schutz)."""
    commented_only = (
        "// Kein setAsync, kein saveAsync, kein sendAsync hier.\n"
        "/* displayNewMessageForm wird bewusst NICHT aufgerufen. */\n"
        "function ok() { return 1; }\n"
    )
    findings = _find_forbidden_write_calls(commented_only)
    assert findings == []


def test_manifest_permission_is_exactly_readitem():
    xml_text = ADDIN_MANIFEST_XML.read_text(encoding="utf-8")
    ns = {"m": "http://schemas.microsoft.com/office/appforoffice/1.1"}
    root = ET.fromstring(xml_text)
    permissions = root.find("m:Permissions", ns)
    assert permissions is not None
    assert permissions.text.strip() == "ReadItem"


def test_manifest_has_no_readwrite_permissions():
    xml_text = ADDIN_MANIFEST_XML.read_text(encoding="utf-8")
    assert "ReadWriteItem" not in xml_text
    assert "ReadWriteMailbox" not in xml_text
