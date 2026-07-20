using Newtonsoft.Json.Linq;
using VizpatchAddin.Core;
using Xunit;

namespace VizpatchAddin.Tests
{
    public class MailContextTests
    {
        [Fact]
        public void ToJson_UsesExactBackendFieldNames_subject_sender_body()
        {
            var ctx = new MailContext
            {
                Subject = "Tankbeleg fehlt",
                Sender = "kunde@example.de",
                Body = "Guten Tag,\nmir fehlt ein Beleg.",
            };

            JObject parsed = JObject.Parse(ctx.ToJson());

            // Exakt die Feldnamen, die webui/src/main.py::_parse_mail_context liest.
            Assert.Equal("Tankbeleg fehlt", (string)parsed["subject"]);
            Assert.Equal("kunde@example.de", (string)parsed["sender"]);
            Assert.Equal("Guten Tag,\nmir fehlt ein Beleg.", (string)parsed["body"]);
        }

        [Fact]
        public void ToJson_HasNoUnexpectedPascalCaseFields()
        {
            var ctx = new MailContext { Subject = "x", Sender = "y", Body = "z" };
            JObject parsed = JObject.Parse(ctx.ToJson());

            Assert.Null(parsed["Subject"]);
            Assert.Null(parsed["Sender"]);
            Assert.Null(parsed["Body"]);
        }
    }
}
