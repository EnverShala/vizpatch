using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Net.Security;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;

namespace VizpatchAddin.Core
{
    /// <summary>
    /// Thin-Client (D-82/D-84) gegen die bestehende Chat-API
    /// <c>POST {BackendUrl}/chat/{AgentId}/send</c>. Baut den Form-encoded
    /// Request (message/history/mail_context/session_id), setzt den
    /// CSRF-Origin-Header (RESEARCH.md Common Pitfall 1) und Basic-Auth, liest den
    /// <c>text/event-stream</c>-Body inkrementell (ResponseHeadersRead) und speist
    /// ihn zeilenweise in den <see cref="SseLineParser"/>. Jeder fertige Frame
    /// wird als <c>(EventType, Data)</c> an den Aufrufer-Callback gereicht.
    /// </summary>
    public sealed class ChatClient : IDisposable
    {
        private readonly AddinSettings _settings;
        private readonly HttpClient _http;

        /// <summary>Produktions-Konstruktor: baut den TLS-gescopten HttpClientHandler.</summary>
        public ChatClient(AddinSettings settings)
            : this(settings, BuildDefaultHandler(settings))
        {
        }

        /// <summary>
        /// Testbarer Konstruktor mit injizierbarem <see cref="HttpMessageHandler"/>
        /// (Request-Assertions ohne echtes Netzwerk).
        /// </summary>
        public ChatClient(AddinSettings settings, HttpMessageHandler handler)
        {
            _settings = settings ?? throw new ArgumentNullException(nameof(settings));
            _http = new HttpClient(handler)
            {
                // SSE-Stream ist langlebig -> kein Gesamt-Timeout (die einzelnen
                // Reads werden ueber den CancellationToken abgebrochen).
                Timeout = Timeout.InfiniteTimeSpan,
            };

            if (!string.IsNullOrEmpty(_settings.Username) || !string.IsNullOrEmpty(_settings.Password))
            {
                string raw = (_settings.Username ?? "") + ":" + (_settings.Password ?? "");
                string base64 = Convert.ToBase64String(Encoding.UTF8.GetBytes(raw));
                _http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Basic", base64);
            }
        }

        /// <summary>
        /// Baut den TLS-Trust GESCOPED auf DIESEN einen Handler — niemals
        /// prozessweit/global gesetzt (Anti-Pattern, RESEARCH.md Common Pitfall 5).
        /// Thumbprint-Pinning ist Default; Blanket-Trust nur bei explizitem
        /// <see cref="AddinSettings.TrustAnyCertificate"/>.
        /// </summary>
        private static HttpClientHandler BuildDefaultHandler(AddinSettings settings)
        {
            var handler = new HttpClientHandler();
            handler.ServerCertificateCustomValidationCallback = (request, cert, chain, errors) =>
            {
                // Blanket-Trust: JEDES Zertifikat akzeptieren — bewusst nur, wenn
                // der Betreiber es im Settings-Dialog explizit aktiviert hat.
                if (settings.TrustAnyCertificate)
                {
                    return true;
                }
                // Pinning: exakter Thumbprint-Vergleich (Doppelpunkte/Spaces egal).
                if (!string.IsNullOrEmpty(settings.CertThumbprint) && cert != null)
                {
                    string want = settings.CertThumbprint
                        .Replace(":", "").Replace(" ", "").Trim();
                    return string.Equals(cert.GetCertHashString(), want,
                        StringComparison.OrdinalIgnoreCase);
                }
                // Sonst normale System-Zertifikatskette.
                return errors == SslPolicyErrors.None;
            };
            return handler;
        }

        /// <summary>
        /// Sendet den Chat-POST und ruft <paramref name="onFrame"/> fuer jeden
        /// eintreffenden SSE-Frame auf. Bewusst OHNE das await-Kontext-Detachment
        /// (RESEARCH.md Anti-Pattern) — die await-Fortsetzungen (und damit
        /// <paramref name="onFrame"/>) bleiben auf dem aufrufenden (UI-)Kontext,
        /// damit der Chat-Log direkt aktualisiert werden darf.
        /// </summary>
        public async Task StreamChatAsync(
            string message,
            IEnumerable<ChatTurn> history,
            MailContext mailContext,
            string sessionId,
            Action<string, string> onFrame,
            CancellationToken ct)
        {
            if (onFrame == null) throw new ArgumentNullException(nameof(onFrame));

            var request = BuildRequest(message, history, mailContext, sessionId);

            using (var response = await _http.SendAsync(
                request, HttpCompletionOption.ResponseHeadersRead, ct))
            {
                response.EnsureSuccessStatusCode();

                using (var stream = await response.Content.ReadAsStreamAsync())
                using (var reader = new StreamReader(stream, Encoding.UTF8))
                {
                    var parser = new SseLineParser();
                    // Terminierung AUSSCHLIESSLICH ueber den Rueckgabewert von
                    // ReadLineAsync() (== null am Stream-Ende). KEIN reader.EndOfStream:
                    // dessen Getter liest bei Bedarf synchron das naechste Byte aus dem
                    // Netzwerk-Stream vor und wuerde auf dem (bewusst nicht abgekoppelten)
                    // UI-Thread blockieren, bis das Backend das naechste Byte sendet.
                    // So bleibt der gesamte Lesepfad durchgehend asynchron.
                    string line;
                    while ((line = await reader.ReadLineAsync()) != null)
                    {
                        ct.ThrowIfCancellationRequested();

                        var frame = parser.Feed(line);
                        if (frame != null)
                        {
                            onFrame(frame.Value.EventType, frame.Value.Data);
                        }
                    }
                    var tail = parser.Flush();
                    if (tail != null)
                    {
                        onFrame(tail.Value.EventType, tail.Value.Data);
                    }
                }
            }
        }

        /// <summary>
        /// Baut die <see cref="HttpRequestMessage"/> (URL, Form-Felder,
        /// Origin-Header). Oeffentlich fuer deterministische Request-Assertions.
        /// </summary>
        public HttpRequestMessage BuildRequest(
            string message,
            IEnumerable<ChatTurn> history,
            MailContext mailContext,
            string sessionId)
        {
            // AgentId ist frei konfigurierbar -> als Pfadsegment enkodieren, damit
            // Leerzeichen/Sonderzeichen (/, #, ?) keine falsche URL erzeugen.
            string url = _settings.BackendUrl.TrimEnd('/')
                + "/chat/" + Uri.EscapeDataString(_settings.AgentId ?? "") + "/send";

            var fields = new List<KeyValuePair<string, string>>
            {
                new KeyValuePair<string, string>("message", message ?? ""),
                new KeyValuePair<string, string>(
                    "history",
                    JsonConvert.SerializeObject(history ?? Enumerable.Empty<ChatTurn>())),
                new KeyValuePair<string, string>(
                    "mail_context",
                    mailContext != null ? mailContext.ToJson() : ""),
                new KeyValuePair<string, string>("session_id", sessionId ?? ""),
            };

            var request = new HttpRequestMessage(HttpMethod.Post, url)
            {
                Content = new FormUrlEncodedContent(fields),
            };

            // CSRF-Origin-Workaround (Common Pitfall 1): ein natives HttpClient
            // sendet standardmaessig KEINEN Origin-Header -> enforce_same_origin
            // wuerde den POST mit 403 abweisen, VOR der Auth-Pruefung. Der
            // AddinOriginToken ist in ADDIN_FRAME_ANCESTORS gelistet, sodass die
            // bestehende _origin_allowed_for_addin-Ausnahme greift.
            request.Headers.Add("Origin", _settings.AddinOriginToken);

            return request;
        }

        public void Dispose()
        {
            _http.Dispose();
        }
    }
}
