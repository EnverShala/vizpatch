using System;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using Office = Microsoft.Office.Core;

namespace VizpatchAddin.Ribbon
{
    /// <summary>
    /// Ribbon (XML-Ansatz, RESEARCH.md Pattern 1): ein einzelner Toggle-Button
    /// "Vizpatch-Chat", der die <see cref="ThisAddIn.ChatPane"/> ein-/ausblendet.
    /// Der XML-Ansatz kommt ohne den Ribbon-Designer/Design-Time-Codegen aus und
    /// ist damit per MSBuild-Kommandozeile baubar.
    ///
    /// Bidirektionale Synchronisation:
    ///  - Klick auf den Toggle -> <c>OnToggleChat</c> setzt <c>ChatPane.Visible</c>.
    ///  - Schliesst der Nutzer die Pane ueber ihr "X", ruft ThisAddIn
    ///    <see cref="InvalidateToggle"/> -> Outlook fragt <c>GetChatPressed</c> neu
    ///    ab und der Button-Zustand folgt der tatsaechlichen Sichtbarkeit.
    /// </summary>
    [ComVisible(true)]
    public class ChatRibbon : Office.IRibbonExtensibility
    {
        private const string ToggleControlId = "vizpatchChatToggle";

        private Office.IRibbonUI _ribbon;

        /// <summary>Liefert das Ribbon-XML (eingebettete Ressource) an Outlook.</summary>
        public string GetCustomUI(string ribbonID)
        {
            return GetResourceText("VizpatchAddin.Ribbon.ChatRibbon.xml");
        }

        /// <summary>onLoad-Callback: haelt die Ribbon-Referenz fuer Invalidation.</summary>
        public void OnRibbonLoad(Office.IRibbonUI ribbonUI)
        {
            _ribbon = ribbonUI;
        }

        /// <summary>toggleButton onAction: steuert die Pane-Sichtbarkeit.</summary>
        public void OnToggleChat(Office.IRibbonControl control, bool pressed)
        {
            var pane = Globals.ThisAddIn != null ? Globals.ThisAddIn.ChatPane : null;
            if (pane != null)
            {
                pane.Visible = pressed;
            }
        }

        /// <summary>toggleButton getPressed: spiegelt die tatsaechliche Sichtbarkeit.</summary>
        public bool GetChatPressed(Office.IRibbonControl control)
        {
            var pane = Globals.ThisAddIn != null ? Globals.ThisAddIn.ChatPane : null;
            return pane != null && pane.Visible;
        }

        /// <summary>
        /// Erzwingt eine Neuabfrage von <see cref="GetChatPressed"/> — von
        /// ThisAddIn beim <c>VisibleChanged</c>-Event der Pane aufgerufen, damit
        /// der Toggle-Zustand der Pane-Sichtbarkeit folgt.
        /// </summary>
        public void InvalidateToggle()
        {
            if (_ribbon != null)
            {
                _ribbon.InvalidateControl(ToggleControlId);
            }
        }

        private static string GetResourceText(string resourceName)
        {
            var asm = Assembly.GetExecutingAssembly();
            using (var stream = asm.GetManifestResourceStream(resourceName))
            {
                if (stream == null)
                {
                    throw new InvalidOperationException(
                        "Ribbon-Ressource nicht gefunden: " + resourceName);
                }
                using (var reader = new StreamReader(stream))
                {
                    return reader.ReadToEnd();
                }
            }
        }
    }
}
