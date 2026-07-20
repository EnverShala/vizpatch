using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace VizpatchAddin.Core
{
    /// <summary>
    /// Persistiert <see cref="AddinSettings"/> als JSON unter
    /// <c>%AppData%\Vizpatch\OutlookAddin\settings.json</c> (D-85, RESEARCH.md
    /// Pattern 4). Das Passwort wird AUSSCHLIESSLICH DPAPI-verschluesselt
    /// (<see cref="DataProtectionScope.CurrentUser"/>) als Base64 abgelegt — der
    /// Klartext erscheint nie in der Datei (spiegelt Vizpatch SEC-01..03 auf der
    /// Windows-Seite). Bewusst NICHT ueber <c>Properties.Settings.Default</c>
    /// (User-Scope-Settings persistieren in VSTO-Add-ins unzuverlaessig).
    /// </summary>
    public static class SecureSettingsStore
    {
        /// <summary>Standard-Ablageort: %AppData%\Vizpatch\OutlookAddin\settings.json.</summary>
        public static string DefaultSettingsPath => Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "Vizpatch", "OutlookAddin", "settings.json");

        /// <summary>Speichert an den Standardpfad.</summary>
        public static void Save(AddinSettings settings)
        {
            Save(settings, DefaultSettingsPath);
        }

        /// <summary>Laedt vom Standardpfad (oder Defaults, wenn keine Datei existiert).</summary>
        public static AddinSettings Load()
        {
            return Load(DefaultSettingsPath);
        }

        /// <summary>
        /// Speichert die Settings nach <paramref name="path"/>. Das Passwort wird
        /// per <see cref="ProtectedData.Protect"/> (CurrentUser-Scope) verschluesselt
        /// und Base64-kodiert als Feld <c>PasswordProtected</c> geschrieben —
        /// niemals als Klartext.
        /// </summary>
        public static void Save(AddinSettings settings, string path)
        {
            if (settings == null) throw new ArgumentNullException(nameof(settings));
            if (string.IsNullOrEmpty(path)) throw new ArgumentException("path leer", nameof(path));

            byte[] encrypted = ProtectedData.Protect(
                Encoding.UTF8.GetBytes(settings.Password ?? ""),
                optionalEntropy: null,
                scope: DataProtectionScope.CurrentUser);

            var toWrite = new JObject
            {
                ["BackendUrl"] = settings.BackendUrl ?? "",
                ["AgentId"] = settings.AgentId ?? "",
                ["Username"] = settings.Username ?? "",
                ["PasswordProtected"] = Convert.ToBase64String(encrypted),
                ["AddinOriginToken"] = settings.AddinOriginToken ?? "",
                ["CertThumbprint"] = settings.CertThumbprint ?? "",
                ["TrustAnyCertificate"] = settings.TrustAnyCertificate,
            };

            string dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir))
            {
                Directory.CreateDirectory(dir);
            }
            File.WriteAllText(path, toWrite.ToString(Formatting.Indented), Encoding.UTF8);
        }

        /// <summary>
        /// Laedt die Settings aus <paramref name="path"/> und entschluesselt das
        /// Passwort round-trip-treu. Existiert die Datei nicht, werden Defaults
        /// geliefert.
        /// </summary>
        public static AddinSettings Load(string path)
        {
            if (string.IsNullOrEmpty(path) || !File.Exists(path))
            {
                return new AddinSettings();
            }

            JObject json = JObject.Parse(File.ReadAllText(path, Encoding.UTF8));

            string password = "";
            string protectedB64 = (string)json["PasswordProtected"];
            if (!string.IsNullOrEmpty(protectedB64))
            {
                byte[] plain = ProtectedData.Unprotect(
                    Convert.FromBase64String(protectedB64),
                    optionalEntropy: null,
                    scope: DataProtectionScope.CurrentUser);
                password = Encoding.UTF8.GetString(plain);
            }

            var defaults = new AddinSettings();
            return new AddinSettings
            {
                BackendUrl = (string)json["BackendUrl"] ?? "",
                AgentId = (string)json["AgentId"] ?? "",
                Username = (string)json["Username"] ?? "",
                Password = password,
                AddinOriginToken = (string)json["AddinOriginToken"] ?? defaults.AddinOriginToken,
                CertThumbprint = (string)json["CertThumbprint"] ?? "",
                TrustAnyCertificate = (bool?)json["TrustAnyCertificate"] ?? false,
            };
        }
    }
}
