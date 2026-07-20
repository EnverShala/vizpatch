using Newtonsoft.Json;

namespace VizpatchAddin.Core
{
    /// <summary>
    /// Mail-Kontext-DTO (D-65/D-86). Serialisiert EXAKT die Felder
    /// <c>subject</c>/<c>sender</c>/<c>body</c>, die das Backend in
    /// <c>webui/src/main.py::_parse_mail_context</c> erwartet — jede andere
    /// Benennung wuerde dort still auf leere Strings fallen.
    /// Diese Klasse ist COM-frei; der reale Wert wird spaeter (Plan 08-02) aus
    /// dem Outlook-Objektmodell befuellt.
    /// </summary>
    public sealed class MailContext
    {
        [JsonProperty("subject")]
        public string Subject { get; set; } = "";

        [JsonProperty("sender")]
        public string Sender { get; set; } = "";

        [JsonProperty("body")]
        public string Body { get; set; } = "";

        /// <summary>
        /// Serialisiert den Kontext als JSON mit den Feldnamen subject/sender/body
        /// (Newtonsoft.Json, robust gegen Umlaute/Anfuehrungszeichen in Bodies).
        /// </summary>
        public string ToJson()
        {
            return JsonConvert.SerializeObject(this);
        }
    }
}
