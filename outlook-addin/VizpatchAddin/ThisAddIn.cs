using System;
using Microsoft.Office.Tools;
using VizpatchAddin.Ribbon;
using VizpatchAddin.TaskPane;
using Office = Microsoft.Office.Core;

namespace VizpatchAddin
{
    /// <summary>
    /// VSTO-Add-in-Einstiegspunkt (Phase 8, D-82/D-83). Registriert im Startup
    /// eine dockbare <see cref="CustomTaskPane"/> "Vizpatch-Chat" und synchronisiert
    /// deren Sichtbarkeit mit dem Ribbon-Toggle-Button (RESEARCH.md Pattern 1).
    ///
    /// Object-Model-sicher (Pitfall 3): das Add-in nutzt ausschliesslich das von
    /// Outlook via VSTO-Runtime uebergebene <c>Application</c>-Objekt (siehe
    /// ThisAddIn.Designer.cs) — es erzeugt NIE selbst eine Outlook.Application und
    /// ruft keine Send-/Write-/Move-/Delete-APIs auf (Kein-Auto-Send, D-87).
    /// </summary>
    public partial class ThisAddIn
    {
        private ChatTaskPaneHost _chatControl;
        private CustomTaskPane _chatPane;
        private ChatRibbon _ribbon;

        /// <summary>
        /// Die Chat-Task-Pane — vom Ribbon-Toggle ueber
        /// <c>Visible</c> ein-/ausgeblendet.
        /// </summary>
        public CustomTaskPane ChatPane
        {
            get { return _chatPane; }
        }

        private void ThisAddIn_Startup(object sender, EventArgs e)
        {
            _chatControl = new ChatTaskPaneHost();
            _chatPane = this.CustomTaskPanes.Add(_chatControl, "Vizpatch-Chat");
            _chatPane.Width = 420;
            // Standardmaessig ausgeblendet — der Betreiber blendet die Pane bei
            // Bedarf ueber den Ribbon-Toggle ein.
            _chatPane.Visible = false;
            // Sichtbarkeits-Aenderungen (auch das Schliessen ueber das "X" der
            // Pane) zuruecksynchronisieren, damit der Ribbon-Toggle den echten
            // Zustand widerspiegelt.
            _chatPane.VisibleChanged += ChatPane_VisibleChanged;
        }

        private void ChatPane_VisibleChanged(object sender, EventArgs e)
        {
            if (_ribbon != null)
            {
                _ribbon.InvalidateToggle();
            }
        }

        /// <summary>
        /// Liefert das Ribbon (XML-Ansatz, RESEARCH.md Pattern 1) — kein
        /// Ribbon-Designer/Designer-Codegen noetig.
        /// </summary>
        protected override Office.IRibbonExtensibility CreateRibbonExtensibilityObject()
        {
            _ribbon = new ChatRibbon();
            return _ribbon;
        }

        private void ThisAddIn_Shutdown(object sender, EventArgs e)
        {
            // Kein expliziter Teardown noetig: die VSTO-Runtime raeumt die
            // CustomTaskPane-Collection selbst ab.
        }

        #region Von VSTO generierter Code

        /// <summary>
        /// Erforderliche Methode fuer die VSTO-Verdrahtung — verbindet Startup/
        /// Shutdown mit den Handlern. Wird von ThisAddIn.Designer.cs aufgerufen.
        /// </summary>
        private void InternalStartup()
        {
            this.Startup += new EventHandler(ThisAddIn_Startup);
            this.Shutdown += new EventHandler(ThisAddIn_Shutdown);
        }

        #endregion
    }
}
