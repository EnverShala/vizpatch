/* Office.js-Mail-Reader für die Outlook-Taskpane (D-69/OUT-03).
 *
 * Liest die gerade geöffnete Mail AUSSCHLIESSLICH lesend über
 * Office.context.mailbox.item und reicht {subject, sender, body} per
 * postMessage an das same-origin Chat-Embed weiter (iframe #addin-chat-frame,
 * D-66) — IMMER mit expliziter targetOrigin = window.location.origin,
 * NIEMALS '*' (T-08-04, Spoofing-Schutz auf Sender-Seite).
 *
 * Kein-Auto-Send (D-70/OUT-04) — struktureller Wächter in
 * webui/tests/test_addin_readonly.py: dieses Modul ruft AUSSCHLIESSLICH
 * lesende Office-APIs auf (getAsync/addHandlerAsync). KEINE Aufrufe von
 * setAsync, saveAsync, displayReplyForm, displayReplyAllForm,
 * displayNewMessageForm, makeEwsRequestAsync oder sendAsync. */
(function () {
  function postMailContext() {
    var frame = document.getElementById('addin-chat-frame');
    if (!frame || !frame.contentWindow) {
      return;
    }
    var item = Office.context.mailbox.item;
    if (!item) {
      return;
    }
    var subject = item.subject || '';
    var sender = (item.from && item.from.emailAddress) || '';
    item.body.getAsync(Office.CoercionType.Text, function (result) {
      var body = '';
      if (result.status === Office.AsyncResultStatus.Succeeded) {
        body = result.value || '';
      }
      frame.contentWindow.postMessage(
        { type: 'vizpatch-mail-context', subject: subject, sender: sender, body: body },
        window.location.origin
      );
    });
  }

  Office.onReady(function () {
    postMailContext();

    // Bei Mailwechsel (z. B. gepinnte Taskpane) erneut lesen + posten.
    Office.context.mailbox.addHandlerAsync(Office.EventType.ItemChanged, postMailContext);

    // Frisch geladenes Embed-iframe hat noch keinen Kontext — beim load
    // erneut posten, damit es die aktuell offene Mail sofort erhält.
    var frame = document.getElementById('addin-chat-frame');
    if (frame) {
      frame.addEventListener('load', postMailContext);
    }
  });
})();
