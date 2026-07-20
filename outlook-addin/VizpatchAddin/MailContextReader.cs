using System.Runtime.InteropServices;
using VizpatchAddin.Core;
using Outlook = Microsoft.Office.Interop.Outlook;

namespace VizpatchAddin
{
    /// <summary>
    /// Defensive Mail-Kontext-Extraktion aus dem Outlook-Objektmodell (D-86,
    /// RESEARCH.md Pattern 3, Pitfall 3). Liest ausschliesslich die gerade
    /// geoeffnete bzw. markierte Mail und baut daraus einen
    /// <see cref="MailContext"/> (subject/sender/body) fuer die Chat-API.
    ///
    /// Object-Model-sicher: es wird NUR das von der VSTO-Runtime uebergebene
    /// <c>Application</c>-Objekt verwendet (es wird nie selbst eine
    /// Outlook-Instanz instanziiert) — dann greift der Outlook "Object Model
    /// Guard" beim Lesen von <c>Body</c>/<c>SenderEmailAddress</c> nicht (Pitfall 3).
    ///
    /// Kein-Auto-Send (D-87): rein lesend. Es werden keinerlei Outlook-Schreib-,
    /// Versand-, Verschiebe- oder Loesch-APIs und keine Item-Erzeugung aufgerufen.
    /// </summary>
    public static class MailContextReader
    {
        /// <summary>
        /// Baut den Mail-Kontext aus dem aktiven Item. Bevorzugt den
        /// <c>ActiveInspector</c> (geoeffnete Mail), faellt sonst auf das erste
        /// Element der <c>ActiveExplorer</c>-Selektion zurueck.
        ///
        /// Rueckgabe <c>null</c> (kein Absturz), wenn
        /// <list type="bullet">
        ///   <item>kein aktives Fenster / keine Auswahl existiert (COMException),</item>
        ///   <item>das aktive Item kein <see cref="Outlook.MailItem"/> ist
        ///         (Termin/Kontakt/Aufgabe, D-86).</item>
        /// </list>
        /// Die COM-Referenz auf das gelesene Item wird via
        /// <see cref="Marshal.ReleaseComObject"/> wieder freigegeben.
        /// </summary>
        public static MailContext TryBuildMailContext(Outlook.Application app)
        {
            if (app == null)
            {
                return null;
            }

            object currentItem = null;
            // Zwischen-COM-Objekte separat halten, um sie im finally sicher wieder
            // freizugeben. Selection ist bei jedem Aufruf ein frisch erzeugtes
            // COM-Objekt und wuerde sonst pro "Mail einbeziehen"-Send leaken.
            Outlook.Inspector inspector = null;
            Outlook.Explorer explorer = null;
            Outlook.Selection selection = null;
            try
            {
                inspector = app.ActiveInspector();
                if (inspector != null)
                {
                    currentItem = inspector.CurrentItem;
                }
                else
                {
                    explorer = app.ActiveExplorer();
                    if (explorer != null)
                    {
                        selection = explorer.Selection;
                        if (selection != null && selection.Count > 0)
                        {
                            // Outlook-Selektionen sind 1-basiert.
                            currentItem = selection[1];
                        }
                    }
                }
            }
            catch (COMException)
            {
                // z. B. kein aktives Fenster/keine Auswahl -> kein Kontext, kein Crash.
                // Das finally gibt trotzdem etwaige Zwischenobjekte frei.
                return null;
            }
            finally
            {
                // Rein lesend: nur die Zwischen-COM-Referenzen freigeben, nichts
                // schreiben/versenden. Reihenfolge Selection -> Explorer -> Inspector.
                if (selection != null) Marshal.ReleaseComObject(selection);
                if (explorer != null) Marshal.ReleaseComObject(explorer);
                if (inspector != null) Marshal.ReleaseComObject(inspector);
            }

            Outlook.MailItem mail = currentItem as Outlook.MailItem;
            if (mail == null)
            {
                // Nicht-Mail-Item (Termin/Kontakt/Aufgabe) oder gar kein Item ->
                // defensiv kein Kontext. Etwaige COM-Referenz sauber freigeben.
                if (currentItem != null && Marshal.IsComObject(currentItem))
                {
                    Marshal.ReleaseComObject(currentItem);
                }
                return null;
            }

            try
            {
                string sender = mail.SenderEmailAddress;
                if (string.IsNullOrEmpty(sender))
                {
                    sender = mail.SenderName;
                }

                return new MailContext
                {
                    Subject = mail.Subject ?? "",
                    Sender = sender ?? "",
                    Body = mail.Body ?? "",
                };
            }
            catch (COMException)
            {
                // Einzelne Property-Zugriffe koennen bei degradierten Items
                // fehlschlagen -> kein Kontext statt Absturz.
                return null;
            }
            finally
            {
                Marshal.ReleaseComObject(mail);
            }
        }
    }
}
