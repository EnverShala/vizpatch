using System;
using System.IO;
using System.Text;
using VizpatchAddin.Core;
using Xunit;

namespace VizpatchAddin.Tests
{
    public class ConnectProvisioningTests
    {
        private static string WriteTemp(string content)
        {
            string path = Path.Combine(
                Path.GetTempPath(), "vizpatch-prov-" + Guid.NewGuid().ToString("N"), ConnectProvisioning.FileName);
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            File.WriteAllText(path, content, Encoding.UTF8);
            return path;
        }

        [Fact]
        public void TryLoadFromFile_ValidFile_ImportsFieldsAndLeavesPasswordEmpty()
        {
            string path = WriteTemp(
                "{\"BackendUrl\":\"http://192.168.0.5:8080\",\"AgentId\":\"esso\","
                + "\"Username\":\"admin\",\"AddinOriginToken\":\"https://outlook.office.com\"}");
            try
            {
                var s = ConnectProvisioning.TryLoadFromFile(path);
                Assert.NotNull(s);
                Assert.Equal("http://192.168.0.5:8080", s.BackendUrl);
                Assert.Equal("esso", s.AgentId);
                Assert.Equal("admin", s.Username);
                Assert.Equal("https://outlook.office.com", s.AddinOriginToken);
                // Passwort wird NIE aus der Verknüpfungs-Datei übernommen (DPAPI).
                Assert.Equal("", s.Password);
            }
            finally
            {
                Directory.Delete(Path.GetDirectoryName(path), true);
            }
        }

        [Fact]
        public void TryLoadFromFile_MissingBackendUrl_ReturnsNull()
        {
            string path = WriteTemp("{\"AgentId\":\"esso\",\"Username\":\"admin\"}");
            try
            {
                Assert.Null(ConnectProvisioning.TryLoadFromFile(path));
            }
            finally
            {
                Directory.Delete(Path.GetDirectoryName(path), true);
            }
        }

        [Fact]
        public void TryLoadFromFile_NonexistentPath_ReturnsNull()
        {
            string path = Path.Combine(
                Path.GetTempPath(), "vizpatch-none-" + Guid.NewGuid().ToString("N"), ConnectProvisioning.FileName);
            Assert.Null(ConnectProvisioning.TryLoadFromFile(path));
        }

        [Fact]
        public void TryLoadFromFile_MalformedJson_ReturnsNull()
        {
            string path = WriteTemp("das ist kein json {");
            try
            {
                Assert.Null(ConnectProvisioning.TryLoadFromFile(path));
            }
            finally
            {
                Directory.Delete(Path.GetDirectoryName(path), true);
            }
        }
    }
}
