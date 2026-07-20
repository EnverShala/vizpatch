using System.Collections.Generic;

namespace VizpatchAddin.Core
{
    /// <summary>
    /// Zeilenbasierte SSE-Frame-Zustandsmaschine (RESEARCH.md Pattern 2 /
    /// „Don't Hand-Roll"). Zerlegt exakt das Server-Framing aus
    /// <c>webui/src/main.py</c> (<c>_sse_data_frame</c> + der <c>chat_send</c>-
    /// Generator):
    /// <list type="bullet">
    ///   <item>Text-Chunk: je Zeile <c>data: {line}</c>, Frame endet mit Leerzeile</item>
    ///   <item>Werkzeug: <c>event: tool</c> + <c>data: {label}</c></item>
    ///   <item>Abschluss: <c>event: done</c> + <c>data: </c></item>
    ///   <item>Fehler:   <c>event: error</c> + <c>data: {line}</c></item>
    /// </list>
    /// Rein string-basiert — KEIN HttpClient-/Netzwerk-Bezug, damit ohne Backend
    /// per xUnit testbar. .NET Framework 4.8 hat keinen eingebauten SSE-Parser
    /// (erst ab .NET 9), daher dieser kleine, an der SSE-Spec orientierte Parser.
    /// </summary>
    public sealed class SseLineParser
    {
        private const string DefaultEventType = "message";

        private string _eventType = DefaultEventType;
        private readonly List<string> _dataLines = new List<string>();

        /// <summary>
        /// Speist eine einzelne Zeile ein. Eine Leerzeile beendet den aktuellen
        /// Frame und liefert <c>(EventType, Data)</c> zurueck; alle anderen Zeilen
        /// liefern <c>null</c> (Frame noch nicht komplett). Mehrere <c>data:</c>-
        /// Zeilen desselben Frames werden mit <c>"\n"</c> verbunden. Fuehrende
        /// Leerzeichen nach <c>event:</c>/<c>data:</c> werden entfernt (TrimStart).
        /// <c>id:</c>/<c>retry:</c> und sonstige Felder werden ignoriert.
        /// </summary>
        public (string EventType, string Data)? Feed(string line)
        {
            if (string.IsNullOrEmpty(line))
            {
                return CompleteFrame();
            }

            if (line.StartsWith("event:"))
            {
                _eventType = line.Substring("event:".Length).TrimStart();
            }
            else if (line.StartsWith("data:"))
            {
                _dataLines.Add(line.Substring("data:".Length).TrimStart());
            }
            // andere SSE-Felder (id:, retry:, Kommentarzeilen ":…") werden ignoriert.
            return null;
        }

        /// <summary>
        /// Schliesst einen ggf. offenen Frame am Stream-Ende ohne abschliessende
        /// Leerzeile ab (defensiv). Liefert den Frame oder <c>null</c>.
        /// </summary>
        public (string EventType, string Data)? Flush()
        {
            return CompleteFrame();
        }

        private (string EventType, string Data)? CompleteFrame()
        {
            // Nur dispatchen, wenn der Frame Inhalt trug (data-Zeilen ODER ein
            // gesetztes event:) — reine Leerzeilen zwischen Frames erzeugen nichts.
            bool hasContent = _dataLines.Count > 0 || _eventType != DefaultEventType;
            if (!hasContent)
            {
                Reset();
                return null;
            }

            var frame = (_eventType, string.Join("\n", _dataLines));
            Reset();
            return frame;
        }

        private void Reset()
        {
            _eventType = DefaultEventType;
            _dataLines.Clear();
        }
    }
}
