# vertrauen-einrichten.ps1 — VOR setup.exe ausführen.
# Liest das Signatur-Zertifikat aus VizpatchAddin.vsto und installiert es als
# vertrauenswürdig (TrustedPublisher + Root). Danach installiert das Add-in
# ohne "Herausgeber nicht verifiziert"-Warnung/Blocker.
#
# Aufruf:  Rechtsklick -> "Mit PowerShell ausführen"
#          oder: powershell -ExecutionPolicy Bypass -File .\vertrauen-einrichten.ps1
# Ohne Adminrechte: Import in den Benutzer-Speicher (Windows fragt beim
# Root-Import einmal nach Bestätigung — mit "Ja" beantworten).

$ErrorActionPreference = 'Stop'

# Download-Sperre (Mark of the Web) von ALLEN Paket-Dateien entfernen —
# sonst blockiert SmartScreen setup.exe ("Der Computer wurde durch Windows geschuetzt").
Get-ChildItem $PSScriptRoot -Recurse -File | Unblock-File
Write-Host "Download-Sperre entfernt (alle Dateien in $PSScriptRoot)."

$vsto = Join-Path $PSScriptRoot 'VizpatchAddin.vsto'
if (-not (Test-Path $vsto)) { throw "VizpatchAddin.vsto nicht gefunden neben diesem Script." }

[xml]$manifest = Get-Content $vsto
$b64 = ($manifest.GetElementsByTagName('X509Certificate') | Select-Object -First 1).InnerText
if (-not $b64) { throw "Kein Zertifikat im Manifest gefunden." }

$cert = [System.Security.Cryptography.X509Certificates.X509Certificate2]::new([Convert]::FromBase64String($b64))
Write-Host "Zertifikat: $($cert.Subject)"
Write-Host "Thumbprint: $($cert.Thumbprint)"

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$scope = if ($isAdmin) { 'LocalMachine' } else { 'CurrentUser' }

foreach ($storeName in 'TrustedPublisher', 'Root') {
    $store = [System.Security.Cryptography.X509Certificates.X509Store]::new($storeName, $scope)
    $store.Open('ReadWrite')
    if ($store.Certificates.Thumbprint -contains $cert.Thumbprint) {
        Write-Host "Schon vorhanden: $scope\$storeName"
    } else {
        $store.Add($cert)
        Write-Host "Importiert: $scope\$storeName"
    }
    $store.Close()
}

Write-Host ""
Write-Host "Fertig. Jetzt setup.exe starten - keine Herausgeber-Warnung mehr."
