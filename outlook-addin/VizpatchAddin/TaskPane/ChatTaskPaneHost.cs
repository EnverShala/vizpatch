using System.Windows.Forms;

namespace VizpatchAddin.TaskPane
{
    /// <summary>
    /// WinForms-Host der Custom Task Pane (D-83: reines WinForms, kein WPF/ElementHost).
    /// <see cref="Microsoft.Office.Tools.CustomTaskPaneCollection.Add(UserControl, string)"/>
    /// erwartet einen <see cref="UserControl"/>; dieser Host fuellt die Pane und
    /// nimmt den eigentlichen Chat-Bereich (<c>ChatView</c>, Plan 08-02 Task 2) auf.
    /// </summary>
    public class ChatTaskPaneHost : UserControl
    {
        public ChatTaskPaneHost()
        {
            InitializeLayout();
        }

        private void InitializeLayout()
        {
            this.Dock = DockStyle.Fill;
            this.BackColor = System.Drawing.SystemColors.Window;
            // Der Chat-Bereich (ChatView) wird in Task 2 hier eingehaengt.
        }
    }
}
