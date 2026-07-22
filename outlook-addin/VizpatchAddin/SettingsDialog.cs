using System;
using System.Drawing;
using System.Windows.Forms;
using VizpatchAddin.Core;
using VizpatchAddin.TaskPane;

namespace VizpatchAddin
{
    /// <summary>
    /// Konfigurations-Dialog des Add-ins (D-85, RESEARCH.md Pattern 4). Bearbeitet
    /// Backend-URL, Agent-ID, Basic-Auth-Zugangsdaten, den CSRF-Origin-Token und die
    /// Zertifikats-Optionen (Thumbprint-Pinning / Blanket-Trust) und persistiert
    /// alles ueber <see cref="SecureSettingsStore"/> — das Passwort landet
    /// ausschliesslich DPAPI-verschluesselt auf der Platte, nie im Klartext.
    ///
    /// UX-Regel "leer = unveraendert" fuer das Passwortfeld (analog dem
    /// WebUI-Konfig-Formular): Das Feld wird beim Oeffnen bewusst NICHT mit dem
    /// gespeicherten Passwort vorbelegt; bleibt es beim Speichern leer, wird der
    /// bereits gespeicherte Wert beibehalten statt geleert.
    /// </summary>
    public sealed class SettingsDialog : Form
    {
        private TextBox _backendUrl;
        private TextBox _agentId;
        private TextBox _username;
        private TextBox _password;
        private TextBox _originToken;
        private TextBox _certThumbprint;
        private CheckBox _trustAnyCertificate;

        // Beim Oeffnen geladener Ist-Zustand — Quelle fuer "leer = unveraendert".
        private readonly AddinSettings _loaded;

        public SettingsDialog()
        {
            _loaded = LoadSafe();
            BuildUi();
            PopulateFrom(_loaded);
        }

        private static AddinSettings LoadSafe()
        {
            try
            {
                return SecureSettingsStore.Load();
            }
            catch
            {
                // Defekte/leere Settings duerfen den Dialog nicht abstuerzen lassen.
                return new AddinSettings();
            }
        }

        // Moderne Palette (identisch zur ChatView-Anmutung).
        private static readonly Color DlgBg = Color.White;
        private static readonly Color PrimaryBg = Color.FromArgb(0x25, 0x63, 0xEB);
        private static readonly Color PrimaryHover = Color.FromArgb(0x1D, 0x4E, 0xD8);
        private static readonly Color SecondaryBg = Color.FromArgb(0xEE, 0xF1, 0xF5);
        private static readonly Color SecondaryHover = Color.FromArgb(0xDD, 0xE3, 0xEC);
        private static readonly Color SecondaryFg = Color.FromArgb(0x1E, 0x3A, 0x5F);

        private void BuildUi()
        {
            Text = "Vizpatch — Einstellungen";
            // Sizable statt FixedDialog: der Betreiber kann das Fenster bei Bedarf
            // vergroessern; der Inhalt scrollt ohnehin (AutoScroll unten), sodass
            // nichts mehr abgeschnitten wird.
            FormBorderStyle = FormBorderStyle.Sizable;
            StartPosition = FormStartPosition.CenterParent;
            MaximizeBox = false;
            MinimizeBox = false;
            ClientSize = new Size(560, 620);
            MinimumSize = new Size(480, 420);
            Font = new Font("Segoe UI", 9.5f);
            BackColor = DlgBg;

            // Der Formularinhalt (Table) liegt in einem AutoScroll-Panel: reicht die
            // Hoehe nicht, erscheint ein Scrollbalken statt abgeschnittener Zeilen.
            var scrollHost = new Panel
            {
                Dock = DockStyle.Fill,
                AutoScroll = true,
                BackColor = DlgBg,
            };

            var layout = new TableLayoutPanel
            {
                Dock = DockStyle.Top,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                Padding = new Padding(16),
                ColumnCount = 2,
                BackColor = DlgBg,
            };
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 150));
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));

            _backendUrl = AddRow(layout, "Backend-URL:", new TextBox { Dock = DockStyle.Fill });
            _agentId = AddRow(layout, "Agent-ID:", new TextBox { Dock = DockStyle.Fill });
            _username = AddRow(layout, "Benutzername:", new TextBox { Dock = DockStyle.Fill });
            _password = AddRow(layout, "Passwort:",
                new TextBox { Dock = DockStyle.Fill, UseSystemPasswordChar = true });

            AddHint(layout,
                "Passwort leer lassen = unveraendert. Wird DPAPI-verschluesselt "
                + "gespeichert (nie Klartext).");

            _originToken = AddRow(layout, "Origin-Token:", new TextBox { Dock = DockStyle.Fill });
            AddHint(layout,
                "Muss serverseitig in ADDIN_FRAME_ANCESTORS gelistet sein "
                + "(CSRF-Origin-Workaround). Default: https://outlook.office.com");

            _certThumbprint = AddRow(layout, "Zertifikat-Thumbprint:",
                new TextBox { Dock = DockStyle.Fill });
            AddHint(layout,
                "Optional: TLS-Pinning gegen ein selbstsigniertes Backend-Zertifikat. "
                + "Leer = normale System-Zertifikatskette.");

            _trustAnyCertificate = new ModernCheckBox
            {
                Text = "Jedes Zertifikat akzeptieren (TrustAnyCertificate)",
                AutoSize = true,
                ForeColor = SecondaryFg,
            };
            AddRow(layout, "", _trustAnyCertificate);

            var warning = new Label
            {
                Text = "Achtung: Deaktiviert die TLS-Zertifikatspruefung fuer diesen "
                    + "Client vollstaendig (MITM-Risiko). Nur im vertrauenswuerdigen, "
                    + "isolierten LAN aktivieren — sonst Thumbprint-Pinning nutzen.",
                ForeColor = Color.FromArgb(178, 34, 34),
                AutoSize = true,
                MaximumSize = new Size(360, 0),
                Margin = new Padding(0, 2, 0, 4),
            };
            AddRow(layout, "", warning);

            var buttonBar = new FlowLayoutPanel
            {
                Dock = DockStyle.Bottom,
                FlowDirection = FlowDirection.RightToLeft,
                Height = 52,
                Padding = new Padding(12),
                BackColor = DlgBg,
            };
            var saveButton = new RoundButton(PrimaryBg, PrimaryHover, Color.White)
            {
                Text = "Speichern",
                Height = 34,
                AutoSize = true,
                AutoSizeMode = AutoSizeMode.GrowAndShrink,
                Margin = new Padding(6, 0, 0, 0),
                Font = new Font("Segoe UI Semibold", 9.5f),
                DialogResult = DialogResult.None,
            };
            saveButton.Click += SaveButton_Click;
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

            buttonBar.Controls.Add(saveButton);
            buttonBar.Controls.Add(cancelButton);

            scrollHost.Controls.Add(layout);
            // Reihenfolge: Fill-Host zuerst, Bottom-Buttonleiste zuletzt — so dockt
            // die Leiste unten und der scrollbare Inhalt fuellt den Rest darueber.
            Controls.Add(scrollHost);
            Controls.Add(buttonBar);
            AcceptButton = saveButton;
            CancelButton = cancelButton;
        }

        private static TextBox AddRow(TableLayoutPanel layout, string label, Control field)
        {
            int row = layout.RowCount;
            layout.RowCount = row + 1;
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            layout.Controls.Add(new Label
            {
                Text = label,
                Dock = DockStyle.Fill,
                TextAlign = ContentAlignment.MiddleLeft,
                ForeColor = SecondaryFg,
                Margin = new Padding(0, 7, 8, 7),
            }, 0, row);
            // Flacher, moderner Feld-Look (WinForms-Default Fixed3D wirkt altmodisch).
            if (field is TextBox tb)
            {
                tb.BorderStyle = BorderStyle.FixedSingle;
                tb.BackColor = Color.White;
                tb.Font = new Font("Segoe UI", 10f);
            }
            field.Margin = new Padding(0, 4, 0, 4);
            layout.Controls.Add(field, 1, row);
            return field as TextBox;
        }

        private static void AddHint(TableLayoutPanel layout, string text)
        {
            int row = layout.RowCount;
            layout.RowCount = row + 1;
            layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
            var hint = new Label
            {
                Text = text,
                ForeColor = Color.FromArgb(110, 110, 110),
                AutoSize = true,
                Margin = new Padding(0, 0, 0, 8),
                MaximumSize = new Size(360, 0),
            };
            layout.Controls.Add(hint, 1, row);
        }

        private void PopulateFrom(AddinSettings s)
        {
            _backendUrl.Text = s.BackendUrl ?? "";
            _agentId.Text = s.AgentId ?? "";
            _username.Text = s.Username ?? "";
            // "leer = unveraendert": Passwortfeld bewusst NICHT vorbelegen.
            // (WinForms net48 kennt kein PlaceholderText; der Hinweis steht als
            // Label unter dem Feld.)
            _password.Text = "";
            _originToken.Text = string.IsNullOrEmpty(s.AddinOriginToken)
                ? new AddinSettings().AddinOriginToken
                : s.AddinOriginToken;
            _certThumbprint.Text = s.CertThumbprint ?? "";
            _trustAnyCertificate.Checked = s.TrustAnyCertificate;
        }

        private void SaveButton_Click(object sender, EventArgs e)
        {
            var settings = new AddinSettings
            {
                BackendUrl = _backendUrl.Text.Trim(),
                AgentId = _agentId.Text.Trim(),
                Username = _username.Text.Trim(),
                // "leer = unveraendert": leeres Feld behaelt den gespeicherten Wert.
                Password = string.IsNullOrEmpty(_password.Text)
                    ? (_loaded.Password ?? "")
                    : _password.Text,
                AddinOriginToken = string.IsNullOrWhiteSpace(_originToken.Text)
                    ? new AddinSettings().AddinOriginToken
                    : _originToken.Text.Trim(),
                CertThumbprint = _certThumbprint.Text.Trim(),
                TrustAnyCertificate = _trustAnyCertificate.Checked,
            };

            try
            {
                SecureSettingsStore.Save(settings);
            }
            catch (Exception ex)
            {
                MessageBox.Show(this,
                    "Speichern fehlgeschlagen: " + ex.Message,
                    "Vizpatch", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            DialogResult = DialogResult.OK;
            Close();
        }
    }
}
