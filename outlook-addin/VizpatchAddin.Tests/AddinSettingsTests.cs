using System;
using System.IO;
using VizpatchAddin.Core;
using Xunit;

namespace VizpatchAddin.Tests
{
    public class AddinSettingsTests
    {
        [Fact]
        public void Defaults_AddinOriginToken_And_TrustAnyCertificate()
        {
            var s = new AddinSettings();
            // CSRF-Origin-Befund: Default-Token ist Teil von DEFAULT_ADDIN_FRAME_ANCESTORS.
            Assert.Equal("https://outlook.office.com", s.AddinOriginToken);
            Assert.False(s.TrustAnyCertificate);
        }

        [Fact]
        public void Save_DoesNotWritePlaintextPassword_DpapiRoundTrip()
        {
            string path = Path.Combine(Path.GetTempPath(), "vizpatch-test-" + Guid.NewGuid().ToString("N"), "settings.json");
            const string secret = "geheimesPasswort123!";
            try
            {
                var original = new AddinSettings
                {
                    BackendUrl = "https://vizpatch.lan:8000",
                    AgentId = "default",
                    Username = "betreiber",
                    Password = secret,
                    AddinOriginToken = "https://outlook.office.com",
                    CertThumbprint = "AA:BB",
                    TrustAnyCertificate = true,
                };

                SecureSettingsStore.Save(original, path);

                // Das rohe JSON darf das Klartext-Passwort NICHT enthalten (DPAPI).
                string raw = File.ReadAllText(path);
                Assert.DoesNotContain(secret, raw);
                Assert.Contains("PasswordProtected", raw);

                // Round-Trip: Load entschluesselt das Passwort wieder identisch.
                var loaded = SecureSettingsStore.Load(path);
                Assert.Equal(secret, loaded.Password);
                Assert.Equal("https://vizpatch.lan:8000", loaded.BackendUrl);
                Assert.Equal("default", loaded.AgentId);
                Assert.Equal("betreiber", loaded.Username);
                Assert.Equal("https://outlook.office.com", loaded.AddinOriginToken);
                Assert.Equal("AA:BB", loaded.CertThumbprint);
                Assert.True(loaded.TrustAnyCertificate);
            }
            finally
            {
                string dir = Path.GetDirectoryName(path);
                if (dir != null && Directory.Exists(dir)) Directory.Delete(dir, true);
            }
        }

        [Fact]
        public void Load_MissingFile_ReturnsDefaults()
        {
            string path = Path.Combine(Path.GetTempPath(), "vizpatch-missing-" + Guid.NewGuid().ToString("N"), "settings.json");
            var loaded = SecureSettingsStore.Load(path);
            Assert.Equal("", loaded.BackendUrl);
            Assert.Equal("https://outlook.office.com", loaded.AddinOriginToken);
            Assert.False(loaded.TrustAnyCertificate);
        }
    }
}
