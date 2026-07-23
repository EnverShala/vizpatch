"""GET /addin-installer: lädt das Outlook-Add-in-Bundle als ZIP herunter.

Gezippt wird das mitgelieferte `addin-publish/`-Verzeichnis (ClickOnce braucht den
kompletten Ordner). Der Ablageort ist über `main.ADDIN_BUNDLE_DIR` konfigurierbar
(Default `/compose/addin-publish`) — die Tests zeigen ihn auf ein Temp-Bundle.
"""
from __future__ import annotations

import io
import zipfile


def test_addin_installer_streams_zip_with_bundle_structure(authed_client, tmp_path, monkeypatch):
    import src.main as main

    bundle = tmp_path / "addin-publish"
    (bundle / "Application Files").mkdir(parents=True)
    (bundle / "setup.exe").write_bytes(b"MZ fake installer")
    (bundle / "VizpatchAddin.vsto").write_bytes(b"<vsto/>")
    (bundle / "Application Files" / "VizpatchAddin.dll.deploy").write_bytes(b"dll")
    monkeypatch.setattr(main, "ADDIN_BUNDLE_DIR", str(bundle))

    r = authed_client.get("/addin-installer")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert "vizpatch-addin-installer.zip" in r.headers.get("content-disposition", "")

    zf = zipfile.ZipFile(io.BytesIO(r.content))
    names = zf.namelist()
    # ClickOnce-Ordnerstruktur bleibt erhalten (Wurzel = addin-publish/).
    assert "addin-publish/setup.exe" in names
    assert "addin-publish/VizpatchAddin.vsto" in names
    assert "addin-publish/Application Files/VizpatchAddin.dll.deploy" in names


def test_addin_installer_404_when_bundle_absent(authed_client, tmp_path, monkeypatch):
    import src.main as main

    monkeypatch.setattr(main, "ADDIN_BUNDLE_DIR", str(tmp_path / "does-not-exist"))
    r = authed_client.get("/addin-installer")
    assert r.status_code == 404
