using System;

namespace VizpatchAddin.Core
{
    /// <summary>
    /// Erzeugt eine Sitzungs-Kennung je Chat-Sitzung — analog zu
    /// <c>generateSessionId()</c> in <c>webui/static/chat.js</c>. Kein
    /// Sicherheits-Token: die eigentliche Autorisierung des Papierkorb-Gates
    /// (Phase 9) bindet das Backend serverseitig per HMAC an diese Kennung.
    /// Reset einer Sitzung = neuer Aufruf = neue Kennung = wieder Erst-Bestaetigung.
    /// </summary>
    public static class SessionIdGenerator
    {
        /// <summary>Liefert eine neue GUID als String (analog crypto.randomUUID in chat.js).</summary>
        public static string NewSessionId()
        {
            return Guid.NewGuid().ToString();
        }
    }
}
