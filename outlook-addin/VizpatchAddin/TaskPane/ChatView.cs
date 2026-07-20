using System;
using System.Collections.Generic;
using System.Drawing;
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

        public ChatView()
        {
            BuildUi();
            _settings = LoadSettingsSafe();
            _sessionId = SessionIdGenerator.NewSessionId();
            ShowConfigHintIfNeeded();
        }

        private void BuildUi()
        {
            this.Dock = DockStyle.Fill;

            _log = new RichTextBox
            {
                Dock = DockStyle.Fill,
                ReadOnly = true,
                BackColor = Color.White,
                BorderStyle = BorderStyle.None,
                Font = new Font("Segoe UI", 9.5f),
            };

            var inputPanel = new Panel { Dock = DockStyle.Bottom, Height = 124, Padding = new Padding(6) };

            _input = new TextBox
            {
                Dock = DockStyle.Fill,
                Multiline = true,
                ScrollBars = ScrollBars.Vertical,
                Font = new Font("Segoe UI", 9.5f),
            };
            _input.KeyDown += Input_KeyDown;

            var buttonBar = new FlowLayoutPanel
            {
                Dock = DockStyle.Bottom,
                FlowDirection = FlowDirection.RightToLeft,
                Height = 32,
                Padding = new Padding(0, 4, 0, 0),
            };

            _sendButton = new Button { Text = "Senden", AutoSize = true };
            _sendButton.Click += SendButton_Click;

            _resetButton = new Button { Text = "Zuruecksetzen", AutoSize = true };
            _resetButton.Click += ResetButton_Click;

            _settingsButton = new Button { Text = "Einstellungen", AutoSize = true };
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
            };
            _includeMailCheck = new CheckBox
            {
                Text = "Aktuelle Mail einbeziehen",
                AutoSize = true,
                Checked = false,
                Font = new Font("Segoe UI", 9f),
            };
            optionsBar.Controls.Add(_includeMailCheck);

            // Reihenfolge steuert das Docking: buttonBar zuunterst, optionsBar
            // darueber, Eingabefeld fuellt den Rest.
            inputPanel.Controls.Add(_input);
            inputPanel.Controls.Add(optionsBar);
            inputPanel.Controls.Add(buttonBar);

            this.Controls.Add(_log);
            this.Controls.Add(inputPanel);
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
                    + "Bitte in %AppData%\\Vizpatch\\OutlookAddin\\settings.json hinterlegen "
                    + "(Settings-Dialog folgt in einer spaeteren Version).");
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
            _sendButton.Enabled = false;

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

            AppendRoleLine("Sie", Color.FromArgb(0, 90, 158));
            AppendUserText(message);
            AppendRoleLine("Assistent", Color.FromArgb(34, 34, 34));

            var assistantText = new System.Text.StringBuilder();
            bool sawError = false;

            using (var cts = new CancellationTokenSource())
            {
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
                catch (Exception ex)
                {
                    AppendErrorLine(ex.Message);
                    sawError = true;
                }
            }

            // Verlauf erst nach vollstaendiger, fehlerfreier Antwort anhaengen
            // (analog chat.js) — haelt den Verlauf konsistent.
            if (!sawError)
            {
                _history.Add(new ChatTurn("user", message));
                _history.Add(new ChatTurn("assistant", assistantText.ToString()));
            }

            AppendNewLine();
            _sendButton.Enabled = true;
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

        private void AppendRoleLine(string role, Color color)
        {
            _log.SelectionStart = _log.TextLength;
            _log.SelectionColor = color;
            _log.SelectionFont = new Font(_log.Font, FontStyle.Bold);
            _log.AppendText((_log.TextLength > 0 ? "\n" : "") + role + ":\n");
            _log.SelectionFont = new Font(_log.Font, FontStyle.Regular);
            _log.SelectionColor = Color.Black;
            ScrollToEnd();
        }

        private void AppendUserText(string text)
        {
            _log.SelectionColor = Color.Black;
            _log.AppendText(text + "\n");
            ScrollToEnd();
        }

        private void AppendAssistantChunk(string chunk)
        {
            _log.SelectionStart = _log.TextLength;
            _log.SelectionColor = Color.Black;
            _log.AppendText(chunk);
            ScrollToEnd();
        }

        private void AppendToolLine(string label)
        {
            _log.SelectionStart = _log.TextLength;
            _log.SelectionColor = Color.FromArgb(120, 120, 120);
            _log.SelectionFont = new Font(_log.Font, FontStyle.Italic);
            _log.AppendText("\n[Werkzeug] " + label + "\n");
            _log.SelectionFont = new Font(_log.Font, FontStyle.Regular);
            _log.SelectionColor = Color.Black;
            ScrollToEnd();
        }

        private void AppendErrorLine(string text)
        {
            _log.SelectionStart = _log.TextLength;
            _log.SelectionColor = Color.FromArgb(178, 34, 34);
            _log.AppendText("\n[Fehler] " + text + "\n");
            _log.SelectionColor = Color.Black;
            ScrollToEnd();
        }

        private void AppendSystemLine(string text)
        {
            _log.SelectionStart = _log.TextLength;
            _log.SelectionColor = Color.FromArgb(120, 120, 120);
            _log.SelectionFont = new Font(_log.Font, FontStyle.Italic);
            _log.AppendText(text + "\n");
            _log.SelectionFont = new Font(_log.Font, FontStyle.Regular);
            _log.SelectionColor = Color.Black;
            ScrollToEnd();
        }

        private void AppendNewLine()
        {
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
