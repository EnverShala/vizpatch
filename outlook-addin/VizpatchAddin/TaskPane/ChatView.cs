using System;
using System.Collections.Generic;
using System.Drawing;
using System.Reflection;
using System.Threading;
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
        private RichTextBox _log;
        private TextBox _input;
        private Button _sendButton;
        private Button _resetButton;
        private Button _settingsButton;
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
            _sessionId = SessionIdGenerator.NewSessionId();
            ShowConfigHintIfNeeded();
        }

        // Explizite, theme-unabhaengige Farben: In der VSTO-CustomTaskPane erben
        // WinForms-Controls sonst die Outlook-Ambient-Farben — je nach Office-Theme
        // (u. a. Dark/High-Contrast) ergibt das weiss-auf-weiss und ein kaum
        // sichtbares Eingabefeld. Wir erzwingen deshalb ein festes helles Schema.
        private static readonly Color UiBg = Color.White;
        private static readonly Color UiFg = Color.FromArgb(0x20, 0x20, 0x20);
        private static readonly Color BtnBg = Color.FromArgb(0xEF, 0xEF, 0xEF);
        private static readonly Color BtnBorder = Color.FromArgb(0xAD, 0xAD, 0xAD);

        // Chat-Blasen-Farben identisch zum Web-UI (webui/static/chat.css):
        // Nutzer rechtsbuendig in Blau (#2563eb) auf Weiss, Assistent linksbuendig
        // in hellem Grau (#eef1f5) auf Dunkel. Eine RichTextBox kennt keine echten
        // abgerundeten Sprechblasen — nachgebildet ueber SelectionAlignment
        // (rechts/links) + SelectionBackColor (Blasenfarbe hinter dem Text).
        private static readonly Color UserBubbleBg = Color.FromArgb(0x25, 0x63, 0xEB);
        private static readonly Color UserBubbleFg = Color.White;
        private static readonly Color AssistantBubbleBg = Color.FromArgb(0xEE, 0xF1, 0xF5);
        private static readonly Color AssistantBubbleFg = Color.FromArgb(0x11, 0x11, 0x11);

        private static Button MakeButton(string text)
        {
            var b = new Button
            {
                Text = text,
                AutoSize = true,
                FlatStyle = FlatStyle.Flat,
                UseVisualStyleBackColor = false,
                BackColor = BtnBg,
                ForeColor = UiFg,
                Margin = new Padding(4, 0, 0, 0),
                Padding = new Padding(6, 2, 6, 2),
            };
            b.FlatAppearance.BorderColor = BtnBorder;
            b.FlatAppearance.BorderSize = 1;
            return b;
        }

        private void BuildUi()
        {
            this.Dock = DockStyle.Fill;
            this.BackColor = UiBg;

            _log = new RichTextBox
            {
                Dock = DockStyle.Fill,
                ReadOnly = true,
                BackColor = UiBg,
                ForeColor = UiFg,
                BorderStyle = BorderStyle.None,
                Font = new Font("Segoe UI", 9.5f),
            };

            var inputPanel = new Panel { Dock = DockStyle.Bottom, Height = 124, Padding = new Padding(6), BackColor = UiBg };

            _input = new TextBox
            {
                Dock = DockStyle.Fill,
                Multiline = true,
                ScrollBars = ScrollBars.Vertical,
                Font = new Font("Segoe UI", 9.5f),
                BackColor = UiBg,
                ForeColor = UiFg,
                BorderStyle = BorderStyle.FixedSingle,
            };
            _input.KeyDown += Input_KeyDown;

            var buttonBar = new FlowLayoutPanel
            {
                Dock = DockStyle.Bottom,
                FlowDirection = FlowDirection.RightToLeft,
                Height = 32,
                Padding = new Padding(0, 4, 0, 0),
                BackColor = UiBg,
            };

            _sendButton = MakeButton("Senden");
            _sendButton.Click += SendButton_Click;

            _resetButton = MakeButton("Zuruecksetzen");
            _resetButton.Click += ResetButton_Click;

            _settingsButton = MakeButton("Einstellungen");
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
                Height = 26,
                Padding = new Padding(0, 2, 0, 0),
                BackColor = UiBg,
            };
            _includeMailCheck = new CheckBox
            {
                Text = "Aktuelle Mail einbeziehen",
                AutoSize = true,
                Checked = false,
                Font = new Font("Segoe UI", 9f),
                ForeColor = UiFg,
                BackColor = UiBg,
            };
            optionsBar.Controls.Add(_includeMailCheck);

            // Reihenfolge steuert das Docking: buttonBar zuunterst, optionsBar
            // darueber, Eingabefeld fuellt den Rest.
            inputPanel.Controls.Add(_input);
            inputPanel.Controls.Add(optionsBar);
            inputPanel.Controls.Add(buttonBar);

            this.Controls.Add(_log);
            this.Controls.Add(inputPanel);

            // Emblem-Logo oben in der Pane (statt des frueheren Wortmarken-Titels
            // "Vizpatch-Chat"). Nur den Kreis/Flieger, ohne Schriftzug. Wird als
            // eingebettete Ressource geladen; schlaegt das fehl, bleibt die Pane
            // einfach ohne Logo (kein Absturz). Zuletzt hinzugefuegt, damit es
            // ueber _log (Fill) am oberen Rand andockt.
            var emblem = LoadEmblemSafe();
            if (emblem != null)
            {
                var logoBox = new PictureBox
                {
                    Dock = DockStyle.Top,
                    Height = 64,
                    SizeMode = PictureBoxSizeMode.Zoom,
                    BackColor = UiBg,
                    Padding = new Padding(0, 6, 0, 6),
                    Image = emblem,
                };
                this.Controls.Add(logoBox);
            }
        }

        /// <summary>Laedt das eingebettete Emblem-PNG robust — jeder Fehler
        /// (Ressource fehlt/defekt) fuehrt zu <c>null</c> (keine Anzeige), nie zu
        /// einem Absturz der Pane. Die Ressource wird ueber das Namenssuffix
        /// gesucht (unabhaengig vom exakten Namespace-Praefix).</summary>
        private static Image LoadEmblemSafe()
        {
            try
            {
                var asm = Assembly.GetExecutingAssembly();
                foreach (var name in asm.GetManifestResourceNames())
                {
                    if (name.EndsWith("vizpatch_emblem.png", StringComparison.OrdinalIgnoreCase))
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
            _log.Clear();
            ShowConfigHintIfNeeded();
        }

        private void SettingsButton_Click(object sender, EventArgs e)
        {
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

        /// <summary>Setzt Ausrichtung + Hintergrund einer neutralen (linksbuendigen,
        /// nicht eingefaerbten) Zeile — Basis fuer Tool-/Fehler-/System-Zeilen und
        /// die Absaetze zwischen den Sprechblasen.</summary>
        private void ResetLineFormat()
        {
            _log.SelectionAlignment = HorizontalAlignment.Left;
            _log.SelectionBackColor = UiBg;
            _log.SelectionColor = UiFg;
            _log.SelectionFont = new Font(_log.Font, FontStyle.Regular);
        }

        /// <summary>Nutzer-Nachricht als rechtsbuendige, blau hinterlegte Blase
        /// (wie webui .chat-bubble-user).</summary>
        private void AppendUserBubble(string text)
        {
            // Vorherigen Absatz sauber abschliessen (neutral), dann die Blase.
            if (_log.TextLength > 0)
            {
                _log.SelectionStart = _log.TextLength;
                ResetLineFormat();
                _log.AppendText("\n");
            }
            _log.SelectionStart = _log.TextLength;
            _log.SelectionAlignment = HorizontalAlignment.Right;
            _log.SelectionBackColor = UserBubbleBg;
            _log.SelectionColor = UserBubbleFg;
            _log.SelectionFont = new Font(_log.Font, FontStyle.Regular);
            // Randleerzeichen als leichtes "Polster" hinter der Einfaerbung.
            _log.AppendText(" " + text + " ");
            ScrollToEnd();
        }

        /// <summary>Beginnt die linksbuendige, grau hinterlegte Assistenten-Blase
        /// (wie webui .chat-bubble-assistant); die Text-Chunks folgen per
        /// <see cref="AppendAssistantChunk"/>.</summary>
        private void BeginAssistantBubble()
        {
            _log.SelectionStart = _log.TextLength;
            ResetLineFormat();
            _log.AppendText("\n");
            _log.SelectionStart = _log.TextLength;
            _log.SelectionAlignment = HorizontalAlignment.Left;
            _log.SelectionBackColor = AssistantBubbleBg;
            _log.SelectionColor = AssistantBubbleFg;
            _log.AppendText(" ");
            ScrollToEnd();
        }

        private void AppendAssistantChunk(string chunk)
        {
            // Formatierung je Chunk erneut setzen — dazwischen koennen Tool-Zeilen
            // die Auswahl-Attribute veraendert haben.
            _log.SelectionStart = _log.TextLength;
            _log.SelectionAlignment = HorizontalAlignment.Left;
            _log.SelectionBackColor = AssistantBubbleBg;
            _log.SelectionColor = AssistantBubbleFg;
            _log.AppendText(chunk);
            ScrollToEnd();
        }

        private void AppendToolLine(string label)
        {
            _log.SelectionStart = _log.TextLength;
            ResetLineFormat();
            _log.SelectionColor = Color.FromArgb(120, 120, 120);
            _log.SelectionFont = new Font(_log.Font, FontStyle.Italic);
            _log.AppendText("\n[Werkzeug] " + label + "\n");
            ResetLineFormat();
            ScrollToEnd();
        }

        private void AppendErrorLine(string text)
        {
            _log.SelectionStart = _log.TextLength;
            ResetLineFormat();
            _log.SelectionColor = Color.FromArgb(178, 34, 34);
            _log.AppendText("\n[Fehler] " + text + "\n");
            ResetLineFormat();
            ScrollToEnd();
        }

        private void AppendSystemLine(string text)
        {
            _log.SelectionStart = _log.TextLength;
            ResetLineFormat();
            _log.SelectionColor = Color.FromArgb(120, 120, 120);
            _log.SelectionFont = new Font(_log.Font, FontStyle.Italic);
            _log.AppendText(text + "\n");
            ResetLineFormat();
            ScrollToEnd();
        }

        private void AppendNewLine()
        {
            _log.SelectionStart = _log.TextLength;
            ResetLineFormat();
            _log.AppendText("\n");
            ScrollToEnd();
        }

        private void ScrollToEnd()
        {
            _log.SelectionStart = _log.TextLength;
            _log.ScrollToCaret();
        }
    }
}
