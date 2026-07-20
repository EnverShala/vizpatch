using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using VizpatchAddin.Core;
using Xunit;

namespace VizpatchAddin.Tests
{
    public class ChatClientRequestTests
    {
        private static AddinSettings SampleSettings() => new AddinSettings
        {
            BackendUrl = "https://vizpatch.lan:8000",
            AgentId = "default",
            Username = "betreiber",
            Password = "geheim!",
            AddinOriginToken = "https://outlook.office.com",
        };

        [Fact]
        public void BuildRequest_UsesExactChatSendUrl()
        {
            using (var client = new ChatClient(SampleSettings(), new NoopHandler()))
            {
                var req = client.BuildRequest("hallo", null, null, "sess-1");
                Assert.Equal("https://vizpatch.lan:8000/chat/default/send",
                    req.RequestUri.ToString());
                Assert.Equal(HttpMethod.Post, req.Method);
            }
        }

        [Fact]
        public void BuildRequest_SetsOriginHeaderToAddinOriginToken()
        {
            using (var client = new ChatClient(SampleSettings(), new NoopHandler()))
            {
                var req = client.BuildRequest("hallo", null, null, "sess-1");
                Assert.True(req.Headers.Contains("Origin"));
                Assert.Equal("https://outlook.office.com",
                    req.Headers.GetValues("Origin").Single());
            }
        }

        [Fact]
        public async Task BuildRequest_SetsAllFourFormFields()
        {
            using (var client = new ChatClient(SampleSettings(), new NoopHandler()))
            {
                var history = new[] { new ChatTurn("user", "frueher"), new ChatTurn("assistant", "antwort") };
                var mail = new MailContext { Subject = "Betreff", Sender = "a@b.de", Body = "Text" };

                var req = client.BuildRequest("meine frage", history, mail, "sess-42");
                string body = await req.Content.ReadAsStringAsync();
                var form = ParseForm(body);

                Assert.Equal("meine frage", form["message"]);
                Assert.Equal("sess-42", form["session_id"]);
                // history als JSON-Array [{role,content}]
                Assert.Contains("\"role\":\"user\"", form["history"]);
                Assert.Contains("\"content\":\"frueher\"", form["history"]);
                // mail_context als JSON {subject,sender,body}
                Assert.Contains("\"subject\":\"Betreff\"", form["mail_context"]);
                Assert.Contains("\"sender\":\"a@b.de\"", form["mail_context"]);
                Assert.Contains("\"body\":\"Text\"", form["mail_context"]);
            }
        }

        [Fact]
        public async Task BuildRequest_EmptyMailContext_SerializesToEmptyString()
        {
            using (var client = new ChatClient(SampleSettings(), new NoopHandler()))
            {
                var req = client.BuildRequest("frage", null, null, "s");
                string body = await req.Content.ReadAsStringAsync();
                var form = ParseForm(body);
                Assert.Equal("", form["mail_context"]);
                // history ohne Turns -> leeres JSON-Array
                Assert.Equal("[]", form["history"]);
            }
        }

        [Fact]
        public async Task StreamChatAsync_SendsBasicAuthHeader_WithCorrectBase64()
        {
            var capture = new CapturingHandler(SseBody("data: ok\n\nevent: done\ndata: \n\n"));
            using (var client = new ChatClient(SampleSettings(), capture))
            {
                var frames = new List<(string, string)>();
                await client.StreamChatAsync("hi", null, null, "s",
                    (evt, data) => frames.Add((evt, data)), CancellationToken.None);

                Assert.NotNull(capture.LastRequest);
                var auth = capture.LastRequest.Headers.Authorization;
                Assert.NotNull(auth);
                Assert.Equal("Basic", auth.Scheme);
                string expected = Convert.ToBase64String(Encoding.UTF8.GetBytes("betreiber:geheim!"));
                Assert.Equal(expected, auth.Parameter);
            }
        }

        [Fact]
        public async Task StreamChatAsync_DispatchesFramesInOrder_TextThenDone()
        {
            var capture = new CapturingHandler(SseBody(
                "event: tool\ndata: mails_suchen\n\ndata: Antworttext\n\nevent: done\ndata: \n\n"));
            using (var client = new ChatClient(SampleSettings(), capture))
            {
                var frames = new List<(string EventType, string Data)>();
                await client.StreamChatAsync("hi", null, null, "s",
                    (evt, data) => frames.Add((evt, data)), CancellationToken.None);

                Assert.Equal(3, frames.Count);
                Assert.Equal(("tool", "mails_suchen"), frames[0]);
                Assert.Equal(("message", "Antworttext"), frames[1]);
                Assert.Equal(("done", ""), frames[2]);
            }
        }

        [Fact]
        public async Task StreamChatAsync_Non200_Throws()
        {
            var capture = new CapturingHandler(SseBody("nope"), HttpStatusCode.Forbidden);
            using (var client = new ChatClient(SampleSettings(), capture))
            {
                await Assert.ThrowsAsync<HttpRequestException>(() =>
                    client.StreamChatAsync("hi", null, null, "s", (e, d) => { }, CancellationToken.None));
            }
        }

        /// <summary>Parst einen application/x-www-form-urlencoded-Body ohne System.Web.</summary>
        private static Dictionary<string, string> ParseForm(string body)
        {
            var result = new Dictionary<string, string>();
            foreach (var pair in body.Split('&'))
            {
                if (pair.Length == 0) continue;
                int eq = pair.IndexOf('=');
                string key = eq >= 0 ? pair.Substring(0, eq) : pair;
                string val = eq >= 0 ? pair.Substring(eq + 1) : "";
                result[Uri.UnescapeDataString(key.Replace("+", " "))] =
                    Uri.UnescapeDataString(val.Replace("+", " "));
            }
            return result;
        }

        // --- Test-Doubles ---

        private static HttpContent SseBody(string body)
        {
            var content = new StreamContent(new MemoryStream(Encoding.UTF8.GetBytes(body)));
            return content;
        }

        /// <summary>Handler, der nie wirklich sendet (fuer reine BuildRequest-Tests).</summary>
        private sealed class NoopHandler : HttpMessageHandler
        {
            protected override Task<HttpResponseMessage> SendAsync(
                HttpRequestMessage request, CancellationToken cancellationToken)
            {
                throw new InvalidOperationException("NoopHandler darf nicht senden");
            }
        }

        /// <summary>Faengt den Request ab und liefert einen kanonischen SSE-Body.</summary>
        private sealed class CapturingHandler : HttpMessageHandler
        {
            private readonly HttpContent _body;
            private readonly HttpStatusCode _status;
            public HttpRequestMessage LastRequest { get; private set; }

            public CapturingHandler(HttpContent body, HttpStatusCode status = HttpStatusCode.OK)
            {
                _body = body;
                _status = status;
            }

            protected override Task<HttpResponseMessage> SendAsync(
                HttpRequestMessage request, CancellationToken cancellationToken)
            {
                LastRequest = request;
                var resp = new HttpResponseMessage(_status) { Content = _body };
                return Task.FromResult(resp);
            }
        }
    }
}
