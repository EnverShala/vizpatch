namespace VizpatchAddin.Core
{
    /// <summary>
    /// Benutzerbezogene Add-in-Einstellungen (D-85). Backend-URL/Agent-ID/
    /// Zugangsdaten fuer den Thin-Client. Wird ueber
    /// <see cref="SecureSettingsStore"/> persistiert (Passwort DPAPI-verschluesselt).
    /// </summary>
    public sealed class AddinSettings
    {
        /// <summary>Basis-URL des Backends im LAN, z. B. <c>https://vizpatch.lan:8000</c> (D-85).</summary>
        public string BackendUrl { get; set; } = "";

        /// <summary>Ziel-Agent fuer <c>POST /chat/{AgentId}/send</c> (D-84).</summary>
        public string AgentId { get; set; } = "";

        /// <summary>Basic-Auth-Benutzername (bestehendes WebUI-Auth-Regime, D-85).</summary>
        public string Username { get; set; } = "";

        /// <summary>
        /// Basic-Auth-Passwort. Wird von <see cref="SecureSettingsStore"/> NIE im
        /// Klartext auf die Platte geschrieben, sondern ausschliesslich
        /// DPAPI-verschluesselt (siehe dort).
        /// </summary>
        public string Password { get; set; } = "";

        /// <summary>
        /// Origin-Token, das der <see cref="ChatClient"/> als <c>Origin</c>-Header
        /// mitschickt. Hintergrund (D-84/D-85, CSRF-Origin-Befund, RESEARCH.md
        /// Common Pitfall 1): die Backend-Middleware <c>enforce_same_origin</c>
        /// (webui/src/main.py) weist jeden nicht-sicheren Request OHNE passenden
        /// Origin-Header mit HTTP 403 ab — noch VOR der Auth-Pruefung. Die fuer den
        /// Office.js-Add-in gebaute Ausnahme <c>_origin_allowed_for_addin</c> greift
        /// nur, wenn ein Origin gesetzt UND in <c>ADDIN_FRAME_ANCESTORS</c> gelistet
        /// ist. Der Default <c>https://outlook.office.com</c> ist Bestandteil des
        /// serverseitigen <c>DEFAULT_ADDIN_FRAME_ANCESTORS</c> und funktioniert
        /// daher Zero-Config, ohne Backend-Codeaenderung.
        /// </summary>
        public string AddinOriginToken { get; set; } = "https://outlook.office.com";

        /// <summary>
        /// Optionaler Zertifikat-Thumbprint fuer TLS-Pinning gegen ein
        /// selbstsigniertes Backend-Zertifikat (RESEARCH.md Common Pitfall 5).
        /// Leer = normale System-Zertifikatskette.
        /// </summary>
        public string CertThumbprint { get; set; } = "";

        /// <summary>
        /// Blanket-TLS-Trust (JEDES Zertifikat akzeptieren). Default <c>false</c> —
        /// nur fuer bewusst isolierte LAN-Szenarien explizit aktivieren; im UI mit
        /// Warnhinweis. Gescoped auf den einen HttpClientHandler des ChatClient
        /// (NIE global via ServicePointManager, Common Pitfall 5).
        /// </summary>
        public bool TrustAnyCertificate { get; set; } = false;
    }
}
