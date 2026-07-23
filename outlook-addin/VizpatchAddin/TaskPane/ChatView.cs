using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using VizpatchAddin;
using VizpatchAddin.Core;

namespace VizpatchAddin.TaskPane
{
    /// <summary>
    /// Nativer Chat-Bereich der Custom Task Pane (MVP-Slice 1, D-82/D-84).
    /// Reicht eine getippte Nachricht an <see cref="ChatClient.StreamChatAsync"/>
    /// (Plan 08-01) und rendert den SSE-Stream inkrementell:
    /// Text-Chunks (default) werden an die laufende Antwort angehaengt,
    /// <c>event: tool</c> als dezente Werkzeug-Hinweiszeile, <c>event: done</c>
    /// schliesst den Turn ab, <c>event: error</c> zeigt eine Fehlermeldung.
    ///
    /// Sitzung: pro Task-Pane-Sitzung eine <c>session_id</c> (GUID) via
    /// <see cref="SessionIdGenerator"/>; bei jedem Send unveraendert mitgeschickt.
    /// "Zuruecksetzen" erzeugt eine NEUE session_id und leert den In-Memory-
    /// Verlauf (analog webui/static/chat.js).
    ///
    /// Mail-Kontext (D-86, Plan 08-03): ist die Checkbox "Aktuelle Mail
    /// einbeziehen" aktiv, wird vor jedem Send ueber
    /// <see cref="MailContextReader.TryBuildMailContext"/> der Kontext
    /// (subject/sender/body) aus dem aktiven <c>MailItem</c> gebaut und als
    /// <c>mail_context</c> an <see cref="ChatClient.StreamChatAsync"/> uebergeben.
    ///
    /// Kein-Auto-Send (D-87): diese View ruft KEINE Outlook-Schreib-/Versand-APIs
    /// auf und erzeugt keine MailItems — sie liest nur die offene Mail und spricht
    /// ausschliesslich die Chat-API.
    /// </summary>
    public class ChatView : UserControl
    {
        private FlowLayoutPanel _log;
        private Bubble _currentAssistant;
        private Panel _inputPanel;
        private TextBox _input;
        private RoundButton _sendButton;
        private RoundButton _resetButton;
        private RoundButton _settingsButton;
        private CheckBox _includeMailCheck;

        // In-Memory-Verlauf (D-58) — lebt nur mit der Sitzung.
        private readonly List<ChatTurn> _history = new List<ChatTurn>();
        private string _sessionId;
        private AddinSettings _settings;

        // Abbruch des laufenden SSE-Streams. Wird bei "Zuruecksetzen" und beim
        // Dispose der Pane gecancelt, damit kein Request haengt (WR-05).
        private CancellationTokenSource _activeCts;

        public ChatView()
        {
            BuildUi();
            _settings = LoadSettingsSafe();
            TryAutoProvisionIfUnconfigured();
            _sessionId = SessionIdGenerator.NewSessionId();
            ShowConfigHintIfNeeded();
        }

        /// <summary>
        /// „Mit Outlook verknüpfen" (Auto-Import): Ist noch KEINE Backend-URL
        /// konfiguriert, wird beim Start nach der von der WebUI erzeugten
        /// Verknüpfungs-Datei gesucht (Downloads-/Konfig-Ordner). Wird sie
        /// gefunden, übernimmt das Add-in Backend-URL/Agent-ID/Benutzer/
        /// Origin-Token und speichert sie. Das Passwort bleibt leer und wird —
        /// DPAPI-bedingt — einmalig über „Einstellungen" am Ziel-PC eingegeben.
        /// Jeder Fehler ist unkritisch: es bleibt bei den bisherigen
        /// Einstellungen (die Pane darf nie deshalb abstürzen).
        /// </summary>
        private void TryAutoProvisionIfUnconfigured()
        {
            try
            {
                if (!string.IsNullOrWhiteSpace(_settings.BackendUrl))
                {
                    return; // bereits konfiguriert — nie ueberschreiben
                }
                var provisioned = ConnectProvisioning.TryImport();
                if (provisioned == null)
                {
                    return;
                }
                SecureSettingsStore.Save(provisioned);
                _settings = LoadSettingsSafe();
                AppendSystemLine(
                    "Verknüpfung importiert (Backend-URL und Agent-ID übernommen). "
                    + "Bitte einmalig das WebUI-Passwort über \"Einstellungen\" eingeben.");
            }
            catch
            {
                // Provisionierung ist rein optional — niemals die Pane gefaehrden.
            }
        }

        // Explizite, theme-unabhaengige Farben: In der VSTO-CustomTaskPane erben
        // WinForms-Controls sonst die Outlook-Ambient-Farben — je nach Office-Theme
        // (u. a. Dark/High-Contrast) ergibt das weiss-auf-weiss und ein kaum
        // sichtbares Eingabefeld. Wir erzwingen deshalb ein festes helles Schema.
        private static readonly Color UiBg = Color.White;
        private static readonly Color UiFg = Color.FromArgb(0x20, 0x20, 0x20);

        // Moderne Button-/Eingabe-Palette (an das Web-UI angelehnt).
        private static readonly Color PrimaryBg = Color.FromArgb(0x25, 0x63, 0xEB);      // Senden (Blau #2563eb)
        private static readonly Color PrimaryHover = Color.FromArgb(0x1D, 0x4E, 0xD8);   // #1d4ed8
        private static readonly Color SecondaryBg = Color.FromArgb(0xEE, 0xF1, 0xF5);    // Zuruecksetzen/Einstellungen
        private static readonly Color SecondaryHover = Color.FromArgb(0xDD, 0xE3, 0xEC);
        private static readonly Color SecondaryFg = Color.FromArgb(0x1E, 0x3A, 0x5F);    // Vizpatch-Dunkelblau
        private static readonly Color InputBorder = Color.FromArgb(0xCC, 0xD3, 0xDE);
        private static readonly Color InputBorderFocus = PrimaryBg;

        // Chat-Blasen-Farben identisch zum Web-UI (webui/static/chat.css):
        // Nutzer rechtsbuendig in Blau (#2563eb) auf Weiss, Assistent linksbuendig
        // in hellem Grau (#eef1f5) auf Dunkel. Umgesetzt als echte abgerundete
        // Sprechblasen (eigenes `Bubble`-Control) in einem FlowLayoutPanel.
        private static readonly Color UserBubbleBg = Color.FromArgb(0x25, 0x63, 0xEB);
        private static readonly Color UserBubbleFg = Color.White;
        private static readonly Color AssistantBubbleBg = Color.FromArgb(0xEE, 0xF1, 0xF5);
        private static readonly Color AssistantBubbleFg = Color.FromArgb(0x11, 0x11, 0x11);

        // Blase nimmt hoechstens diesen Anteil der Log-Breite ein (Rest bleibt als
        // Luft auf der Gegenseite -> klarer Links/Rechts-Eindruck wie im Web-UI).
        private const double BubbleMaxWidthFraction = 0.78;

        /// <summary>Erzeugt einen modernen, flach gerundeten Button. `primary` =
        /// gefuellt in Vizpatch-Blau (Senden), sonst dezent hellgrau.</summary>
        private static RoundButton MakeButton(string text, bool primary)
        {
            return new RoundButton(primary
                ? PrimaryBg : SecondaryBg,
                primary ? PrimaryHover : SecondaryHover,
                primary ? Color.White : SecondaryFg)
            {
                Text = text,
                Height = 34,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                Margin = new Padding(6, 0, 0, 0),
                Font = new Font("Segoe UI Semibold", 9.5f),
            };
        }

        private void BuildUi()
        {
            this.Dock = DockStyle.Fill;
            this.BackColor = UiBg;

            _log = new FlowLayoutPanel
            {
                Dock = DockStyle.Fill,
                FlowDirection = FlowDirection.TopDown,
                WrapContents = false,
                AutoScroll = true,
                BackColor = UiBg,
                Padding = new Padding(6),
                Font = new Font("Segoe UI", 10f),
            };
            // Bei Groessenaenderung der Pane die Blasen neu ausrichten (Breite/Seite).
            _log.Resize += (s, e) => RelayoutBubbles();

            // Height ist nur der Startwert — AdjustInputPanelHeight() setzt die
            // Hoehe inhaltsabhaengig (klein starten, mit dem Text mitwachsen, max
            // 30% der Pane, siehe unten).
            _inputPanel = new Panel { Dock = DockStyle.Bottom, Height = 176, Padding = new Padding(10, 8, 10, 14), BackColor = UiBg };

            // Eingabefeld in einem gerundeten Rahmen-Container (RoundedPanel) —
            // die TextBox selbst ist randlos, der weiche Rahmen kommt vom Panel und
            // wechselt bei Fokus auf Vizpatch-Blau (moderner "Input-Chip"-Look).
            var inputFrame = new RoundedPanel(InputBorder)
            {
                Dock = DockStyle.Fill,
                BackColor = UiBg,
                Padding = new Padding(10, 8, 10, 8),
            };
            _input = new TextBox
            {
                Dock = DockStyle.Fill,
                Multiline = true,
                ScrollBars = ScrollBars.Vertical,
                Font = new Font("Segoe UI", 10.5f),
                BackColor = UiBg,
                ForeColor = UiFg,
                BorderStyle = BorderStyle.None,
            };
            _input.KeyDown += Input_KeyDown;
            // Mit der getippten Textmenge mitwachsen (Betreiber-Wunsch nach dem
            // Kundentermin): jede Aenderung rechnet die Panelhoehe neu, gedeckelt
            // auf hoechstens 30% der Pane-Hoehe.
            _input.TextChanged += (s, e) => AdjustInputPanelHeight();
            _input.Enter += (s, e) => { inputFrame.BorderColor = InputBorderFocus; inputFrame.Invalidate(); };
            _input.Leave += (s, e) => { inputFrame.BorderColor = InputBorder; inputFrame.Invalidate(); };
            inputFrame.Controls.Add(_input);

            var buttonBar = new FlowLayoutPanel
            {
                Dock = DockStyle.Bottom,
                FlowDirection = FlowDirection.RightToLeft,
                Height = 52,
                Padding = new Padding(0, 8, 0, 8),
                BackColor = UiBg,
            };

            _sendButton = MakeButton("Senden", primary: true);
            _sendButton.Click += SendButton_Click;

            _resetButton = MakeButton("Zurücksetzen", primary: false);
            _resetButton.Click += ResetButton_Click;

            _settingsButton = MakeButton("Einstellungen", primary: false);
            _settingsButton.Click += SettingsButton_Click;

            buttonBar.Controls.Add(_sendButton);
            buttonBar.Controls.Add(_resetButton);
            buttonBar.Controls.Add(_settingsButton);

            // Optionsleiste: Mail-Kontext opt-in (Default aus). Erst wenn aktiv,
            // liest das Add-in die offene/markierte Mail (Datensparsamkeit).
            var optionsBar = new FlowLayoutPanel
            {
                Dock = DockStyle.Bottom,
                FlowDirection = FlowDirection.LeftToRight,
                Height = 38,
                Padding = new Padding(2, 6, 0, 6),
                BackColor = UiBg,
            };
            _includeMailCheck = new ModernCheckBox
            {
                Text = "Aktuelle Mail einbeziehen",
                Checked = false,
                Font = new Font("Segoe UI", 9.5f),
                ForeColor = Color.FromArgb(0x55, 0x5B, 0x66),
                BackColor = UiBg,
                Margin = new Padding(0, 2, 0, 2),
            };
            optionsBar.Controls.Add(_includeMailCheck);

            // Reihenfolge steuert das Docking: buttonBar zuunterst, optionsBar
            // darueber, Eingabefeld fuellt den Rest.
            _inputPanel.Controls.Add(inputFrame);
            _inputPanel.Controls.Add(optionsBar);
            _inputPanel.Controls.Add(buttonBar);

            this.Controls.Add(_log);
            this.Controls.Add(_inputPanel);

            // Eingabefeld inhaltsabhaengig dimensionieren (klein starten, mitwachsen,
            // max 30% der Pane), sobald die Pane ihre echte Groesse kennt bzw. sich
            // aendert.
            this.Resize += (s, e) => AdjustInputPanelHeight();
            AdjustInputPanelHeight();

            // Volles Vizpatch-Logo oben in der Pane (statt des frueheren
            // Wortmarken-Titels "Vizpatch-Chat"). Wird als eingebettete Ressource
            // geladen; schlaegt das fehl, bleibt die Pane einfach ohne Logo (kein
            // Absturz). Zuletzt hinzugefuegt, damit es ueber _log (Fill) am oberen
            // Rand andockt.
            var logo = LoadLogoSafe();
            if (logo != null)
            {
                var logoBox = new PictureBox
                {
                    Dock = DockStyle.Top,
                    Height = 96,
                    SizeMode = PictureBoxSizeMode.Zoom,
                    BackColor = UiBg,
                    Padding = new Padding(0, 8, 0, 8),
                    Image = logo,
                };
                this.Controls.Add(logoBox);
            }
        }

        /// <summary>Laedt das eingebettete Logo-PNG robust — jeder Fehler
        /// (Ressource fehlt/defekt) fuehrt zu <c>null</c> (keine Anzeige), nie zu
        /// einem Absturz der Pane. Die Ressource wird ueber das Namenssuffix
        /// gesucht (unabhaengig vom exakten Namespace-Praefix).</summary>
        private static Image LoadLogoSafe()
        {
            try
            {
                var asm = Assembly.GetExecutingAssembly();
                foreach (var name in asm.GetManifestResourceNames())
                {
                    if (name.EndsWith("vizpatch_logo.png", StringComparison.OrdinalIgnoreCase))
                    {
                        using (var stream = asm.GetManifestResourceStream(name))
                        {
                            if (stream != null)
                            {
                                using (var img = Image.FromStream(stream))
                                {
                                    // Unabhaengige Kopie — loest die Bindung an den
                                    // (gleich geschlossenen) Ressourcen-Stream.
                                    return new Bitmap(img);
                                }
                            }
                        }
                    }
                }
            }
            catch
            {
                // bewusst geschluckt — kein Logo ist besser als ein Absturz.
            }
            return null;
        }

        private static AddinSettings LoadSettingsSafe()
        {
            try
            {
                return SecureSettingsStore.Load();
            }
            catch
            {
                // Defekte/leere Settings duerfen die UI nicht abstuerzen lassen.
                return new AddinSettings();
            }
        }

        private void ShowConfigHintIfNeeded()
        {
            if (string.IsNullOrEmpty(_settings.BackendUrl) || string.IsNullOrEmpty(_settings.AgentId))
            {
                AppendSystemLine(
                    "Hinweis: Backend-URL/Agent-ID noch nicht konfiguriert. "
                    + "Bitte oben ueber \"Einstellungen\" hinterlegen.");
            }
        }

        private void Input_KeyDown(object sender, KeyEventArgs e)
        {
            // Enter = senden, Shift+Enter = Zeilenumbruch (uebliches Chat-Verhalten).
            if (e.KeyCode == Keys.Enter && !e.Shift)
            {
                e.SuppressKeyPress = true;
                TriggerSend();
            }
        }

        private void SendButton_Click(object sender, EventArgs e)
        {
            TriggerSend();
        }

        private void ResetButton_Click(object sender, EventArgs e)
        {
            // Laufenden Stream abbrechen, damit kein Request weiterlaeuft und der
            // gecancelte Turn den frisch geleerten Verlauf nicht wieder befuellt.
            try { _activeCts?.Cancel(); }
            catch (ObjectDisposedException) { /* bereits abgeschlossen/disposed */ }

            _history.Clear();
            _sessionId = SessionIdGenerator.NewSessionId();
            _log.Controls.Clear();
            _currentAssistant = null;
            ShowConfigHintIfNeeded();
        }

        // Fixe Chrome-Hoehe im _inputPanel: buttonBar(52) + optionsBar(38) +
        // vertikales Panel-Padding(8+14) = 112 px. Dazu kommt der Innenabstand des
        // inputFrame (oben+unten = 16). Der Rest ist die eigentliche Textflaeche.
        private const int InputChromeHeight = 112;
        private const int InputFramePadding = 16;

        /// <summary>
        /// Haelt das Eingabefeld KLEIN und laesst es mit der getippten Textmenge
        /// MITWACHSEN (Betreiber-Wunsch nach dem Kundentermin): Start bei ~2 Zeilen,
        /// waechst Zeile fuer Zeile, gedeckelt auf HOECHSTENS 30% der Pane-Hoehe. Ab
        /// dem Deckel scrollt das Textfeld intern (ScrollBars.Vertical). Frueher war
        /// das Feld fest ~28% der Pane hoch -> es wirkte dauerhaft zu gross und stahl
        /// dem Chat-Verlauf Platz. Wird bei jedem TextChanged UND bei Pane-Resize
        /// aufgerufen.
        /// </summary>
        private void AdjustInputPanelHeight()
        {
            if (_inputPanel == null || _input == null)
            {
                return;
            }
            int total = this.ClientSize.Height;
            if (total <= 0)
            {
                return; // Pane hat noch keine echte Groesse — Resize triggert spaeter erneut.
            }

            // Verfuegbare Textbreite grob aus der Panelbreite (Panel-Padding 10+10 +
            // inputFrame-Padding 10+10 = ~40 px seitlicher Rahmen).
            int textWidth = _inputPanel.ClientSize.Width - 40;
            if (textWidth < 40) textWidth = 40;

            // Benoetigte Texthoehe fuer den aktuellen Inhalt (Wortumbruch).
            string probe = _input.Text.Length > 0 ? _input.Text : "Ag";
            int textHeight = TextRenderer.MeasureText(
                probe, _input.Font, new Size(textWidth, int.MaxValue),
                TextFormatFlags.WordBreak | TextFormatFlags.TextBoxControl).Height;

            int lineHeight = _input.Font.Height;
            int minTextHeight = lineHeight * 2;                 // Startgroesse ~2 Zeilen
            if (textHeight < minTextHeight) textHeight = minTextHeight;

            int panelHeight = textHeight + InputFramePadding + InputChromeHeight;

            // Deckel: hoechstens 30% der Pane. Die Untergrenze (2 Zeilen + Leisten)
            // gewinnt nur auf sehr kleinen Panes, wo 30% darunter laege — sonst
            // waere gar kein Bedienen mehr moeglich.
            int minPanel = minTextHeight + InputFramePadding + InputChromeHeight;
            int cap = (int)Math.Round(total * 0.30);
            int maxPanel = Math.Max(cap, minPanel);
            if (panelHeight < minPanel) panelHeight = minPanel;
            if (panelHeight > maxPanel) panelHeight = maxPanel;

            _inputPanel.Height = panelHeight;
        }

        private async void SettingsButton_Click(object sender, EventArgs e)
        {
            // Add-in-Einstellungs-Gate (Feature B): bereits konfigurierte
            // Einstellungen duerfen nur nach Eingabe des WebUI-Passworts geoeffnet
            // werden. Erststart (noch keine Backend-URL hinterlegt) laeuft ungegatet
            // — sonst kaeme man nie in den Dialog, um die URL ueberhaupt zu setzen.
            var current = LoadSettingsSafe();
            if (!string.IsNullOrWhiteSpace(current.BackendUrl))
            {
                if (!await AuthorizeSettingsAsync(current))
                {
                    return;
                }
            }

            // Settings-Dialog (D-85): persistiert via SecureSettingsStore (DPAPI).
            // Nach dem Speichern die Settings neu laden, damit der naechste Turn
            // die aktualisierte Konfiguration verwendet.
            using (var dialog = new SettingsDialog())
            {
                if (dialog.ShowDialog(this) == DialogResult.OK)
                {
                    _settings = LoadSettingsSafe();
                    AppendSystemLine("Einstellungen gespeichert.");
                    ShowConfigHintIfNeeded();
                }
            }
        }

        /// <summary>
        /// Add-in-Einstellungs-Gate: fragt das WebUI-Passwort ab und prueft es
        /// serverseitig (<see cref="ChatClient.VerifyPasswordAsync"/>) gegen die
        /// bereits hinterlegte Backend-URL.
        ///
        /// Zwei Faelle werden bewusst unterschieden:
        /// <list type="bullet">
        /// <item>Backend ERREICHBAR, Passwort falsch (HTTP 401): Dialog bleibt
        ///   gesperrt — genau der Schutz, den das Gate leisten soll.</item>
        /// <item>Backend NICHT erreichbar (falsche/veraltete URL, Server aus,
        ///   TLS-Fehler): eine Passwortpruefung ist gar nicht moeglich. Ohne
        ///   Ausweg waere die Konfiguration dann fuer immer gesperrt (man kaeme
        ///   nie an die falsche URL, um sie zu korrigieren — Lockout-Falle).
        ///   Deshalb wird hier eine ausdrueckliche Rueckfrage angeboten, den
        ///   Dialog zum KORRIGIEREN der Verbindung trotzdem zu oeffnen.</item>
        /// </list>
        /// </summary>
        private async Task<bool> AuthorizeSettingsAsync(AddinSettings current)
        {
            string entered;
            using (var prompt = new PasswordPrompt())
            {
                if (prompt.ShowDialog(this) != DialogResult.OK)
                {
                    return false; // vom Betreiber abgebrochen
                }
                entered = prompt.EnteredPassword;
            }

            try
            {
                using (var client = new ChatClient(current))
                using (var cts = new CancellationTokenSource(TimeSpan.FromSeconds(15)))
                {
                    // false = erreichbares Backend, aber falsches Passwort (401).
                    bool ok = await client.VerifyPasswordAsync(entered, cts.Token);
                    if (!ok)
                    {
                        MessageBox.Show(this,
                            "Falsches WebUI-Passwort — Einstellungen bleiben gesperrt.",
                            "Vizpatch", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    }
                    return ok;
                }
            }
            catch (Exception ex)
            {
                // Backend nicht erreichbar -> Passwort kann nicht geprueft werden.
                // Ausweg gegen die Lockout-Falle: Dialog zum Korrigieren der
                // Verbindung (v.a. der Backend-URL) trotzdem oeffnen lassen.
                var choice = MessageBox.Show(this,
                    "Das WebUI-Backend unter\r\n    " + (current.BackendUrl ?? "(keine URL)")
                    + "\r\nist nicht erreichbar, daher kann das Passwort nicht geprueft werden:\r\n"
                    + ex.Message + "\r\n\r\n"
                    + "Einstellungen trotzdem oeffnen, um die Verbindung (z. B. die "
                    + "Backend-URL) zu korrigieren?",
                    "Vizpatch — Verbindung pruefen",
                    MessageBoxButtons.YesNo, MessageBoxIcon.Warning,
                    MessageBoxDefaultButton.Button2);
                return choice == DialogResult.Yes;
            }
        }

        private void TriggerSend()
        {
            string message = _input.Text.Trim();
            if (message.Length == 0 || !_sendButton.Enabled)
            {
                return;
            }
            _input.Clear();
            // async void ist hier bewusst der uebliche WinForms-Event-Handler-Weg.
            SendAsync(message);
        }

        private async void SendAsync(string message)
        {
            // Etwaigen noch laufenden Turn abbrechen und die CTS als Feld halten,
            // damit Reset/Dispose ihn gezielt canceln koennen (WR-05).
            CancelActiveRequest();
            var cts = new CancellationTokenSource();
            _activeCts = cts;

            _sendButton.Enabled = false;

            var assistantText = new System.Text.StringBuilder();
            bool sawError = false;

            try
            {
                // Mail-Kontext (D-86) NUR bauen, wenn der Betreiber es ausdruecklich
                // will. Der COM-Zugriff geschieht bewusst hier — noch auf dem UI-Thread
                // vor dem await, wo das Outlook-Objektmodell erreichbar ist.
                MailContext mailContext = null;
                if (_includeMailCheck.Checked)
                {
                    mailContext = TryBuildMailContextSafe();
                    if (mailContext == null)
                    {
                        AppendSystemLine(
                            "Hinweis: Keine Mail als Kontext gefunden "
                            + "(keine Mail geoeffnet/markiert oder Nicht-Mail-Element).");
                    }
                }

                AppendUserBubble(message);
                BeginAssistantBubble();

                try
                {
                    // Neuer ChatClient je Turn — baut Basic-Auth + TLS-Scope + Origin
                    // (CSRF-Workaround) aus den Settings (Plan 08-01).
                    using (var client = new ChatClient(_settings))
                    {
                        // WICHTIG: KEIN Kontext-Detachment auf dem await — so laufen
                        // die onFrame-Rueckrufe auf dem UI-Thread (RESEARCH.md
                        // Anti-Pattern). Zusaetzlich defensiv ueber MarshalToUi().
                        await client.StreamChatAsync(
                            message,
                            _history,
                            mailContext,
                            _sessionId,
                            (evt, data) => MarshalToUi(() =>
                            {
                                switch (evt)
                                {
                                    case "tool":
                                        AppendToolLine(data);
                                        break;
                                    case "done":
                                        // Turn-Ende — nichts anzuhaengen.
                                        break;
                                    case "error":
                                        AppendErrorLine(data);
                                        sawError = true;
                                        break;
                                    default: // "message" = Text-Chunk
                                        assistantText.Append(data);
                                        AppendAssistantChunk(data);
                                        break;
                                }
                            }),
                            cts.Token);
                    }
                }
                catch (OperationCanceledException)
                {
                    // Abbruch durch Reset/Pane-Close (WR-05) — leise; der Turn
                    // wird nicht in den Verlauf uebernommen.
                    sawError = true;
                }
                catch (Exception ex)
                {
                    AppendErrorLine(ex.Message);
                    sawError = true;
                }

                // Verlauf erst nach vollstaendiger, fehlerfreier Antwort anhaengen
                // (analog chat.js) — haelt den Verlauf konsistent.
                if (!sawError)
                {
                    _history.Add(new ChatTurn("user", message));
                    _history.Add(new ChatTurn("assistant", assistantText.ToString()));
                }

                AppendNewLine();
            }
            finally
            {
                // Button IMMER wieder aktivieren (WR-06) — auch bei Fehler/Abbruch
                // oder einer Exception ausserhalb des inneren try. Aber nur, wenn
                // dieser Turn noch der aktive ist: ein zwischenzeitlich gestarteter
                // Nachfolge-Turn haelt den Button bewusst deaktiviert.
                if (_activeCts == cts)
                {
                    _sendButton.Enabled = true;
                    _activeCts = null;
                }
                cts.Dispose();
            }
        }

        /// <summary>Bricht einen ggf. laufenden SSE-Stream ab (idempotent, defensiv).</summary>
        private void CancelActiveRequest()
        {
            var cts = _activeCts;
            if (cts == null)
            {
                return;
            }
            try { cts.Cancel(); }
            catch (ObjectDisposedException) { /* bereits abgeschlossen */ }
        }

        /// <summary>
        /// Laufenden Request beim Verwerfen der Pane/des Controls abbrechen, damit
        /// keine spaeter eintreffende Fortsetzung auf disposte Controls zugreift
        /// (WR-05, ObjectDisposedException in async void).
        /// </summary>
        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                CancelActiveRequest();
                _activeCts = null;
            }
            base.Dispose(disposing);
        }

        /// <summary>
        /// Baut den Mail-Kontext aus dem aktiven Outlook-Item robust — jeder
        /// Fehler (kein Add-in-Host, COM-Problem) fuehrt zu <c>null</c> (kein
        /// Mail-Block), nie zu einem Absturz der Chat-UI.
        /// </summary>
        private MailContext TryBuildMailContextSafe()
        {
            try
            {
                var addin = Globals.ThisAddIn;
                var app = addin != null ? addin.Application : null;
                return app != null ? MailContextReader.TryBuildMailContext(app) : null;
            }
            catch
            {
                return null;
            }
        }

        // --- UI-Thread-Marshalling + Log-Ausgabe -------------------------------

        private void MarshalToUi(Action action)
        {
            if (this.IsHandleCreated && this.InvokeRequired)
            {
                this.BeginInvoke(action);
            }
            else
            {
                action();
            }
        }

        // --- Chat-Blasen (echte gerundete Sprechblasen im FlowLayoutPanel) ------

        /// <summary>Innenbreite des Log-Bereichs (ohne Padding). Mindestwert, damit
        /// die erste Blase auch vor dem ersten echten Layout brauchbar misst.</summary>
        private int AvailableWidth()
        {
            int w = _log.ClientSize.Width - _log.Padding.Horizontal;
            return w < 80 ? 80 : w;
        }

        /// <summary>Setzt Hoechstbreite (Umbruch bei ~78 %) und richtet die Blase per
        /// Rand aus: Nutzer nach rechts, Assistent nach links — ohne die verfuegbare
        /// Breite zu ueberschreiten (kein horizontaler Scrollbalken).</summary>
        private void LayoutBubble(Bubble b)
        {
            const int gap = 4;
            int avail = AvailableWidth();
            int maxW = (int)(avail * BubbleMaxWidthFraction);
            if (maxW < 60) maxW = 60;
            b.MaximumSize = new Size(maxW, 0);
            int bw = b.PreferredSize.Width;
            if (bw > avail) bw = avail;
            int rest = avail - bw - gap;
            if (rest < gap) rest = gap;
            b.Margin = b.IsUser
                ? new Padding(rest, gap, gap, gap)   // nach rechts schieben
                : new Padding(gap, gap, rest, gap);  // links belassen
        }

        private Bubble AddBubble(string text, bool isUser)
        {
            var b = new Bubble
            {
                IsUser = isUser,
                BackColor = UiBg,   // Ecken ausserhalb der Rundung = Panel-Hintergrund
                BubbleColor = isUser ? UserBubbleBg : AssistantBubbleBg,
                ForeColor = isUser ? UserBubbleFg : AssistantBubbleFg,
                Font = new Font("Segoe UI", 10f),
                Text = text ?? "",
            };
            _log.Controls.Add(b);
            LayoutBubble(b);
            ScrollToEnd();
            return b;
        }

        /// <summary>Dezente, linksbuendige Notiz-Zeile ohne Blase (Werkzeug/Fehler/
        /// System) — analog webui .chat-tool-activity.</summary>
        private void AddNote(string text, Color fore, FontStyle style)
        {
            var lbl = new Label
            {
                AutoSize = true,
                BackColor = UiBg,
                ForeColor = fore,
                Font = new Font("Segoe UI", 9f, style),
                Margin = new Padding(6, 2, 6, 2),
                MaximumSize = new Size((int)(AvailableWidth() * 0.95), 0),
                Text = text ?? "",
            };
            _log.Controls.Add(lbl);
            ScrollToEnd();
        }

        private void AppendUserBubble(string text)
        {
            _currentAssistant = null;
            AddBubble(text, true);
        }

        /// <summary>Startet einen Assistenten-Turn. Die Blase wird LAZY erst beim
        /// ersten Text-Chunk angelegt (keine leere graue Blase, wenn der Turn nur
        /// aus Werkzeug-/Fehlerzeilen besteht).</summary>
        private void BeginAssistantBubble()
        {
            _currentAssistant = null;
        }

        private void AppendAssistantChunk(string chunk)
        {
            if (_currentAssistant == null)
            {
                _currentAssistant = AddBubble(chunk, false);
            }
            else
            {
                _currentAssistant.Text += chunk;
                LayoutBubble(_currentAssistant);
                ScrollToEnd();
            }
        }

        private void AppendToolLine(string label)
        {
            // Werkzeug-Zeile beendet die laufende Assistenten-Blase optisch — ein
            // danach folgender Text-Chunk beginnt eine neue Blase. Das Label kommt
            // bereits als sprechender Taetigkeitstext vom Server (z. B. "Mails
            // suchen…") — kein "[Werkzeug]"-Praefix, kein Funktionsname.
            _currentAssistant = null;
            AddNote(label, Color.FromArgb(120, 120, 120), FontStyle.Italic);
        }

        private void AppendErrorLine(string text)
        {
            _currentAssistant = null;
            AddNote("[Fehler] " + text, Color.FromArgb(178, 34, 34), FontStyle.Regular);
        }

        private void AppendSystemLine(string text)
        {
            AddNote(text, Color.FromArgb(120, 120, 120), FontStyle.Italic);
        }

        /// <summary>Abstand zwischen Turns entsteht bereits aus den Blasen-Raendern —
        /// bewusst ein No-op (die bestehenden Aufrufer bleiben unveraendert).</summary>
        private void AppendNewLine()
        {
        }

        /// <summary>Richtet nach Groessenaenderung der Pane alle Blasen/Notizen neu
        /// aus (Breite + Seite).</summary>
        private void RelayoutBubbles()
        {
            _log.SuspendLayout();
            foreach (Control c in _log.Controls)
            {
                if (c is Bubble b)
                {
                    LayoutBubble(b);
                }
                else if (c is Label l)
                {
                    l.MaximumSize = new Size((int)(AvailableWidth() * 0.95), 0);
                }
            }
            _log.ResumeLayout();
        }

        private void ScrollToEnd()
        {
            if (_log.Controls.Count == 0)
            {
                return;
            }
            // Erst das Layout aktualisieren, damit die (waehrend des Streamings
            // gewachsene) Blasenhoehe schon steht — sonst zielt der Scroll auf
            // veraltete Positionen und die neueste Zeile bleibt unsichtbar (Teil
            // des Kundenbugs: „man kann nicht runterscrollen").
            _log.PerformLayout();
            // Y ueber die volle Inhaltshoehe setzen -> AutoScroll klemmt auf das
            // tatsaechliche Maximum = ganz unten. Zeigt zuverlaessig die letzte
            // Zeile, auch bei Blasen, die hoeher als der sichtbare Bereich sind.
            _log.AutoScrollPosition = new Point(0, _log.DisplayRectangle.Height);
        }

        /// <summary>
        /// Eine Chat-Sprechblase: ein AutoSize-Label, das seinen Hintergrund als
        /// gerundetes, antialiastes Rechteck selbst zeichnet (der Rest der
        /// Control-Flaeche bleibt in der Panel-Hintergrundfarbe -> runde Ecken).
        /// Der Text wird mit Wortumbruch innerhalb des Innenabstands gezeichnet.
        /// </summary>
        private sealed class Bubble : Label
        {
            public bool IsUser;
            public Color BubbleColor;
            private const int Radius = 14;

            // IDENTISCHE Flags fuer Messung (GetPreferredSize) UND Zeichnung
            // (OnPaint). Weichen sie voneinander ab, ist das selbst gezeichnete
            // Textlayout hoeher als die vom Label gemessene Groesse -> die
            // letzte(n) Zeile(n) werden abgeschnitten (genau der Kundenbug:
            // Antwort nicht vollstaendig lesbar). NoPrefix: '&' im Text nicht als
            // Tastenkuerzel verschlucken.
            private const TextFormatFlags BubbleTextFlags =
                TextFormatFlags.WordBreak | TextFormatFlags.Left | TextFormatFlags.Top
                | TextFormatFlags.NoPrefix;

            public Bubble()
            {
                AutoSize = true;
                Padding = new Padding(11, 8, 11, 8);
                Margin = new Padding(6, 4, 6, 4);
                DoubleBuffered = true;
            }

            /// <summary>
            /// Misst die Blasengroesse mit EXAKT denselben Flags/derselben Breite,
            /// mit der OnPaint zeichnet — zweistufig: erst die natuerliche Breite
            /// (gedeckelt auf <see cref="Control.MaximumSize"/>.Width) bestimmen,
            /// dann die Hoehe bei genau dieser Breite. Damit ist das Label immer
            /// hoch genug fuer den umgebrochenen Text; nichts wird mehr
            /// abgeschnitten. Die Basis-Label-AutoSize-Messung passte nicht zur
            /// selbst gezeichneten WordBreak-Ausgabe und war der Grund fuer die zu
            /// kurzen Blasen.
            /// </summary>
            public override Size GetPreferredSize(Size proposedSize)
            {
                int cap = MaximumSize.Width > 0
                    ? MaximumSize.Width
                    : (proposedSize.Width > 1 ? proposedSize.Width : 320);
                int capText = cap - Padding.Horizontal;
                if (capText < 1) capText = 1;

                string text = string.IsNullOrEmpty(Text) ? " " : Text;
                // 1) natuerliche Breite (<= capText).
                Size natural = TextRenderer.MeasureText(
                    text, Font, new Size(capText, int.MaxValue), BubbleTextFlags);
                int drawTextWidth = natural.Width < 1 ? 1 : natural.Width;
                // 2) Hoehe bei genau dieser Zeichenbreite (kann mehr Zeilen ergeben).
                Size measured = TextRenderer.MeasureText(
                    text, Font, new Size(drawTextWidth, int.MaxValue), BubbleTextFlags);

                return new Size(
                    drawTextWidth + Padding.Horizontal,
                    measured.Height + Padding.Vertical + 2); // +2 px Sicherheitspuffer
            }

            protected override void OnPaint(PaintEventArgs e)
            {
                e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
                var rect = new Rectangle(0, 0, Width - 1, Height - 1);
                using (var path = ModernShapes.RoundedRect(rect, Radius))
                using (var brush = new SolidBrush(BubbleColor))
                {
                    e.Graphics.FillPath(brush, path);
                }
                var textRect = new Rectangle(
                    Padding.Left, Padding.Top,
                    Width - Padding.Horizontal, Height - Padding.Vertical);
                TextRenderer.DrawText(
                    e.Graphics, Text, Font, textRect, ForeColor, BubbleTextFlags);
            }
        }
    }

    /// <summary>Gemeinsame Zeichen-Helfer fuer die modernen Add-in-Controls.</summary>
    internal static class ModernShapes
    {
        /// <summary>Gerundetes Rechteck als GraphicsPath.</summary>
        public static GraphicsPath RoundedRect(Rectangle r, int radius)
        {
            int d = radius * 2;
            if (d > r.Width) d = r.Width;
            if (d > r.Height) d = r.Height;
            if (d < 2) d = 2;
            var path = new GraphicsPath();
            path.AddArc(r.X, r.Y, d, d, 180, 90);
            path.AddArc(r.Right - d, r.Y, d, d, 270, 90);
            path.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            path.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
            path.CloseFigure();
            return path;
        }
    }

    /// <summary>
    /// Flacher, gerundeter Button mit eigener Zeichnung (WinForms-Standard-Buttons
    /// wirken altmodisch). Fuellfarbe + Hover-Farbe + Textfarbe werden im
    /// Konstruktor gesetzt; kein sichtbarer System-Rahmen. Wird sowohl von der
    /// ChatView als auch vom SettingsDialog genutzt.
    /// </summary>
    internal sealed class RoundButton : Button
    {
        private readonly Color _bg;
        private readonly Color _hover;
        private bool _hovering;
        private const int Radius = 8;

        public RoundButton(Color bg, Color hover, Color fore)
        {
            _bg = bg;
            _hover = hover;
            ForeColor = fore;
            FlatStyle = FlatStyle.Flat;
            FlatAppearance.BorderSize = 0;
            FlatAppearance.MouseOverBackColor = Color.Transparent;
            FlatAppearance.MouseDownBackColor = Color.Transparent;
            BackColor = Color.White;   // Ecken ausserhalb der Rundung
            Padding = new Padding(14, 4, 14, 4);
            Cursor = Cursors.Hand;
            DoubleBuffered = true;
        }

        protected override void OnMouseEnter(EventArgs e) { _hovering = true; Invalidate(); base.OnMouseEnter(e); }
        protected override void OnMouseLeave(EventArgs e) { _hovering = false; Invalidate(); base.OnMouseLeave(e); }

        protected override void OnPaint(PaintEventArgs e)
        {
            e.Graphics.Clear(Parent != null ? Parent.BackColor : BackColor);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            var rect = new Rectangle(0, 0, Width - 1, Height - 1);
            using (var path = ModernShapes.RoundedRect(rect, Radius))
            using (var brush = new SolidBrush(Enabled ? (_hovering ? _hover : _bg) : Color.FromArgb(0xC7, 0xCE, 0xD8)))
            {
                e.Graphics.FillPath(brush, path);
            }
            TextRenderer.DrawText(
                e.Graphics, Text, Font, ClientRectangle, ForeColor,
                TextFormatFlags.HorizontalCenter | TextFormatFlags.VerticalCenter | TextFormatFlags.EndEllipsis);
        }
    }

    /// <summary>
    /// Panel mit weichem, gerundetem 1px-Rahmen (fuer Eingabefeld-Container).
    /// <see cref="BorderColor"/> kann z. B. bei Fokus umgesetzt werden.
    /// </summary>
    internal sealed class RoundedPanel : Panel
    {
        public Color BorderColor;
        private const int Radius = 10;

        public RoundedPanel(Color border)
        {
            BorderColor = border;
            DoubleBuffered = true;
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            base.OnPaint(e);
            e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
            var rect = new Rectangle(0, 0, Width - 1, Height - 1);
            using (var path = ModernShapes.RoundedRect(rect, Radius))
            using (var pen = new Pen(BorderColor, 1.4f))
            {
                e.Graphics.DrawPath(pen, path);
            }
        }
    }

    /// <summary>
    /// Moderne, selbst gezeichnete Checkbox: gerundetes Kaestchen, im aktiven
    /// Zustand blau gefuellt mit weissem Haken (statt des altmodischen
    /// Windows-Standard-Kaestchens). Klick-/Toggle-Verhalten erbt sie von CheckBox.
    /// </summary>
    internal sealed class ModernCheckBox : CheckBox
    {
        private static readonly Color Accent = Color.FromArgb(0x25, 0x63, 0xEB);
        private static readonly Color BorderCol = Color.FromArgb(0xB4, 0xBD, 0xCB);
        private const int BoxSize = 18;
        private const int TextGap = 8;

        public ModernCheckBox()
        {
            AutoSize = true;
            Cursor = Cursors.Hand;
            BackColor = Color.White;
            SetStyle(ControlStyles.UserPaint | ControlStyles.OptimizedDoubleBuffer
                     | ControlStyles.ResizeRedraw | ControlStyles.SupportsTransparentBackColor, true);
        }

        protected override void OnCheckedChanged(EventArgs e)
        {
            base.OnCheckedChanged(e);
            Invalidate();
        }

        public override Size GetPreferredSize(Size proposedSize)
        {
            Size t = TextRenderer.MeasureText(Text, Font);
            return new Size(BoxSize + TextGap + t.Width + 4, Math.Max(BoxSize + 4, t.Height + 4));
        }

        protected override void OnPaint(PaintEventArgs e)
        {
            var g = e.Graphics;
            g.Clear(Parent != null ? Parent.BackColor : BackColor);
            g.SmoothingMode = SmoothingMode.AntiAlias;

            int top = (Height - BoxSize) / 2;
            var box = new Rectangle(0, top, BoxSize, BoxSize);
            using (var path = ModernShapes.RoundedRect(box, 4))
            {
                if (Checked)
                {
                    using (var b = new SolidBrush(Accent)) g.FillPath(b, path);
                    using (var pen = new Pen(Color.White, 2f)
                    { StartCap = LineCap.Round, EndCap = LineCap.Round })
                    {
                        g.DrawLines(pen, new[]
                        {
                            new Point(box.X + 4, box.Y + 9),
                            new Point(box.X + 8, box.Y + 13),
                            new Point(box.X + 14, box.Y + 5),
                        });
                    }
                }
                else
                {
                    using (var b = new SolidBrush(Color.White)) g.FillPath(b, path);
                    using (var pen = new Pen(BorderCol, 1.4f)) g.DrawPath(pen, path);
                }
            }

            var textRect = new Rectangle(BoxSize + TextGap, 0, Width - BoxSize - TextGap, Height);
            TextRenderer.DrawText(g, Text, Font, textRect, ForeColor,
                TextFormatFlags.Left | TextFormatFlags.VerticalCenter | TextFormatFlags.WordEllipsis);
        }
    }

    /// <summary>
    /// Kleiner modaler Passwort-Prompt fuer das Add-in-Einstellungs-Gate
    /// (Feature B). Fragt das WebUI-Passwort ab; die eigentliche Pruefung erfolgt
    /// beim Aufrufer serverseitig (<see cref="ChatClient.VerifyPasswordAsync"/>).
    /// Das Passwort wird nur im Speicher gehalten und nie persistiert.
    /// </summary>
    internal sealed class PasswordPrompt : Form
    {
        private static readonly Color PrimaryBg = Color.FromArgb(0x25, 0x63, 0xEB);
        private static readonly Color PrimaryHover = Color.FromArgb(0x1D, 0x4E, 0xD8);
        private static readonly Color SecondaryBg = Color.FromArgb(0xEE, 0xF1, 0xF5);
        private static readonly Color SecondaryHover = Color.FromArgb(0xDD, 0xE3, 0xEC);
        private static readonly Color SecondaryFg = Color.FromArgb(0x1E, 0x3A, 0x5F);

        private readonly TextBox _password;

        public string EnteredPassword => _password.Text;

        public PasswordPrompt()
        {
            Text = "Vizpatch — Einstellungen entsperren";
            FormBorderStyle = FormBorderStyle.FixedDialog;
            StartPosition = FormStartPosition.CenterParent;
            MinimizeBox = false;
            MaximizeBox = false;
            ClientSize = new Size(400, 170);
            Font = new Font("Segoe UI", 9.5f);
            BackColor = Color.White;

            var layout = new TableLayoutPanel
            {
                Dock = DockStyle.Fill,
                ColumnCount = 1,
                RowCount = 2,
                Padding = new Padding(16),
                BackColor = Color.White,
            };
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));

            var label = new Label
            {
                Text = "WebUI-Passwort eingeben, um die Einstellungen zu aendern:",
                AutoSize = true,
                MaximumSize = new Size(352, 0),
                ForeColor = SecondaryFg,
                Margin = new Padding(0, 0, 0, 12),
            };
            _password = new TextBox
            {
                UseSystemPasswordChar = true,
                BorderStyle = BorderStyle.FixedSingle,
                Font = new Font("Segoe UI", 10f),
                Dock = DockStyle.Fill,
            };
            layout.Controls.Add(label, 0, 0);
            layout.Controls.Add(_password, 0, 1);

            var buttonBar = new FlowLayoutPanel
            {
                Dock = DockStyle.Bottom,
                FlowDirection = FlowDirection.RightToLeft,
                Height = 52,
                Padding = new Padding(12),
                BackColor = Color.White,
            };
            var okButton = new RoundButton(PrimaryBg, PrimaryHover, Color.White)
            {
                Text = "Entsperren",
                Height = 34,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                Margin = new Padding(6, 0, 0, 0),
                Font = new Font("Segoe UI Semibold", 9.5f),
                DialogResult = DialogResult.OK,
            };
            var cancelButton = new RoundButton(SecondaryBg, SecondaryHover, SecondaryFg)
            {
                Text = "Abbrechen",
                Height = 34,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                Margin = new Padding(6, 0, 0, 0),
                Font = new Font("Segoe UI Semibold", 9.5f),
                DialogResult = DialogResult.Cancel,
            };
            buttonBar.Controls.Add(okButton);
            buttonBar.Controls.Add(cancelButton);

            // Fill-Inhalt zuerst, Bottom-Leiste zuletzt (Docking-Reihenfolge).
            Controls.Add(layout);
            Controls.Add(buttonBar);
            AcceptButton = okButton;
            CancelButton = cancelButton;
        }
    }
}
