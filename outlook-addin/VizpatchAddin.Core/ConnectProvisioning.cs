using System;
using System.IO;
using System.Text;
using Newtonsoft.Json.Linq;

namespace VizpatchAddin.Core
{
    /// <summary>
    /// Auto-Provisionierung ("Mit Outlook verknüpfen"): Die WebUI erzeugt per
    /// Button eine kleine JSON-Datei (Backend-URL + Agent-ID + Benutzer +
    /// Origin-Token, <b>KEIN Passwort</b>) zum Download. Beim Start importiert das
    /// Add-in sie automatisch, solange noch keine Backend-URL konfiguriert ist —
    /// so ist das Add-in auf einem weiteren PC ohne manuelles Abtippen verbunden.
    ///
    /// Das Passwort bleibt bewusst leer: es wird am Ziel-PC per DPAPI
    /// (CurrentUser) gespeichert und kann daher nicht vom Server vorerzeugt
    /// werden — es wird einmalig über "Einstellungen" eingegeben.
    /// </summary>
    public static class ConnectProvisioning
    {
        /// <summary>Dateiname der Verknüpfungs-Datei (muss zur WebUI passen —
        /// siehe Content-Disposition in <c>/connect-config</c>).</summary>
        public const string FileName = "vizpatch-verknuepfung.json";

        /// <summary>
        /// Kandidaten-Pfade in Prüfreihenfolge: erst der Add-in-Konfigordner
        /// (%AppData%\Vizpatch\OutlookAddin\), dann der Downloads-Ordner des
        /// Benutzers (Standard-Ziel des Browser-Downloads).
        /// </summary>
        public static string[] CandidatePaths()
        {
            string appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
            string profile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            return new[]
            {
                Path.Combine(appData, "Vizpatch", "OutlookAddin", FileName),
                Path.Combine(profile, "Downloads", FileName),
            };
        }

        /// <summary>
        /// Parst eine Verknüpfungs-Datei zu <see cref="AddinSettings"/> (Passwort
        /// bleibt IMMER leer). Fehlende Datei, unlesbares/ungültiges JSON oder
        /// eine leere Backend-URL liefern <c>null</c> — der Aufrufer bleibt dann
        /// bei den bisherigen Einstellungen (nie ein Absturz).
        /// </summary>
        public static AddinSettings TryLoadFromFile(string path)
        {
            try
            {
                if (string.IsNullOrEmpty(path) || !File.Exists(path))
                {
                    return null;
                }
                JObject json = JObject.Parse(File.ReadAllText(path, Encoding.UTF8));
                string backendUrl = (string)json["BackendUrl"] ?? "";
                if (string.IsNullOrWhiteSpace(backendUrl))
                {
                    return null; // ohne Backend-URL ist die Datei wertlos
                }
                var defaults = new AddinSettings();
                return new AddinSettings
                {
                    BackendUrl = backendUrl,
                    AgentId = (string)json["AgentId"] ?? "",
                    Username = (string)json["Username"] ?? "",
                    Password = "", // NIE aus der Datei — DPAPI, am Ziel-PC eingeben
                    AddinOriginToken = (string)json["AddinOriginToken"] ?? defaults.AddinOriginToken,
                    CertThumbprint = (string)json["CertThumbprint"] ?? "",
                    TrustAnyCertificate = (bool?)json["TrustAnyCertificate"] ?? false,
                };
            }
            catch
            {
                return null;
            }
        }

        /// <summary>
        /// Sucht die Verknüpfungs-Datei an den <see cref="CandidatePaths"/> und
        /// liefert die erste erfolgreich geparste — oder <c>null</c>, wenn keine
        /// gefunden/gültig ist.
        /// </summary>
        public static AddinSettings TryImport()
        {
            foreach (var path in CandidatePaths())
            {
                var settings = TryLoadFromFile(path);
                if (settings != null)
                {
                    return settings;
                }
            }
            return null;
        }
    }
}
