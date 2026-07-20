using Newtonsoft.Json;

namespace VizpatchAddin.Core
{
    /// <summary>
    /// Ein Verlaufs-Eintrag (D-58). Serialisiert als <c>{role, content}</c> —
    /// exakt die Struktur, die <c>webui/src/main.py::_parse_chat_history</c>
    /// erwartet (nur str-role/str-content-Turns werden serverseitig uebernommen).
    /// </summary>
    public sealed class ChatTurn
    {
        [JsonProperty("role")]
        public string Role { get; set; } = "";

        [JsonProperty("content")]
        public string Content { get; set; } = "";

        public ChatTurn() { }

        public ChatTurn(string role, string content)
        {
            Role = role;
            Content = content;
        }
    }
}
