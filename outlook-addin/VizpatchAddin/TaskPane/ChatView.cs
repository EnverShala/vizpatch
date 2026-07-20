using System;
using System.Collections.Generic;
using System.Drawing;
using System.Threading;
using System.Windows.Forms;
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
    /// Kein-Auto-Send (D-87): diese View ruft KEINE Outlook-Schreib-/Versand-APIs
    /// auf und erzeugt keine MailItems — sie spricht ausschliesslich die Chat-API.
    /// <c>mail_context</c> bleibt in diesem Plan null (kommt in Plan 08-03).
    /// </summary>
    public class ChatView : UserControl
    {
        private RichTextBox _log;
        private TextBox _input;
        private Button _sendButton;
        private Button _resetButton;

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

            var inputPanel = new Panel { Dock = DockStyle.Bottom, Height = 96, Padding = new Padding(6) };

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

            buttonBar.Controls.Add(_sendButton);
            buttonBar.Controls.Add(_resetButton);

            inputPanel.Controls.Add(_input);
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
                            /* mailContext: */ null,
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
