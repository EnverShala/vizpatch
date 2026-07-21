/* Vanilla-JS-SSE-Client für den Agenten-Chat (D-62).
 * Keine externe Lib (D-61) — fetch() + ReadableStream, lokal eingebunden wie htmx.min.js.
 *
 * Verlauf (D-58): lebt ausschließlich in diesem In-Memory-Array — keine
 * DB, kein localStorage. Verlauf endet mit dem Seitenleben (Reload/Tab-Schluss).
 * Reset-Button (D-58) leert history + #chat-log.
 *
 * sessionId (Session-Autorisierung Papierkorb-Werkzeuge, Betreiber-Entscheidung):
 * einmal pro Chat-Sitzung erzeugt, bei jedem Send mitgeschickt. Das Backend
 * verlangt die explizite Zwei-Schritt-Bestätigung nur für die ERSTE Verschiebung
 * in den Papierkorb je sessionId — danach laufen weitere Verschiebungen
 * DERSELBEN Sitzung ohne erneute Rückfrage. `resetHistory()` erzeugt eine NEUE
 * sessionId (Reset = neue Sitzung = wieder eine Erst-Bestätigung nötig).
 *
 * mail_context (D-65/D-69, Phase 8 — Outlook-Add-in): window.vizpatchGetMailContext
 * ist der Hook, den sendMessage() abfragt. Dieses Skript läuft IM Embed-iframe
 * (same-origin, D-66) und empfängt die gerade geöffnete Mail per postMessage von
 * der Taskpane (webui/static/addin/taskpane.js). Der message-Listener prüft
 * event.origin (T-08-04, Spoofing-Schutz) — Nachrichten von fremden Origins
 * werden verworfen. Ohne Add-in (reiner Browser-Chat, Phase 7) läuft nie eine
 * passende Nachricht ein, der Hook liefert dann weiterhin null. */
(function () {
  const root = document.getElementById('chat-root');
  const agentId = root.dataset.agentId;
  const log = document.getElementById('chat-log');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send-btn');
  const resetBtn = document.getElementById('chat-reset-btn');
  const fileInput = document.getElementById('chat-file-input');

  /* Anhang-Widget (ATT-03, Plan 12-03): Datei wird SOFORT bei Auswahl an
   * /chat/{agentId}/upload gestreamt (server-seitiger Pending-Upload-Store,
   * 12-01/12-02) — der Dateiinhalt selbst verlaesst den Browser sofort und
   * wird NIE in `history`/localStorage gehalten (T-12-11). Nur die vom Server
   * zurueckgegebenen Metadaten (Dateiname/Groesse/Typ) werden hier gemerkt und
   * dem naechsten sendMessage()-Aufruf als `attachment_meta` mitgegeben. */
  let pendingAttachment = null;

  function addUploadStatus(text) {
    const statusLine = document.createElement('div');
    statusLine.className = 'chat-upload-status';
    statusLine.textContent = text;
    log.appendChild(statusLine);
    log.scrollTop = log.scrollHeight;
  }

  if (fileInput) {
    fileInput.addEventListener('change', async function () {
      const file = fileInput.files && fileInput.files[0];
      if (!file) return;

      const fd = new FormData();
      fd.append('file', file);
      fd.append('session_id', sessionId);

      try {
        const res = await fetch('/chat/' + agentId + '/upload', { method: 'POST', body: fd });
        if (!res.ok) {
          const errText = await res.text();
          addUploadStatus('Anhang abgelehnt (' + res.status + '): ' + errText);
          return;
        }
        const data = await res.json();
        pendingAttachment = { dateiname: data.dateiname, groesse: data.groesse, mimetyp: data.mimetyp };
        addUploadStatus('Anhang bereit: ' + data.dateiname);
      } catch (e) {
        addUploadStatus('Netzwerkfehler beim Hochladen: ' + e);
      } finally {
        /* Denselben Dateinamen erneut hochladbar machen (change-Event feuert
         * sonst beim zweiten Auswaehlen derselben Datei nicht erneut). */
        fileInput.value = '';
      }
    });
  }

  /** Zuletzt per postMessage empfangene Mail (D-69) — Default null (kein
   * Mail-Kontext), z. B. solange kein Add-in eingebettet ist oder noch keine
   * Nachricht empfangen wurde. */
  let lastMailContext = null;

  window.addEventListener('message', function (event) {
    // T-08-04: nur same-origin-Nachrichten akzeptieren — die Taskpane postet
    // ausschließlich mit targetOrigin = window.location.origin, ein fremdes
    // Fenster könnte sonst gefälschten Mail-Kontext einschleusen.
    if (event.origin !== window.location.origin) {
      return;
    }
    const data = event.data;
    if (!data || data.type !== 'vizpatch-mail-context') {
      return;
    }
    lastMailContext = {
      subject: data.subject || '',
      sender: data.sender || '',
      body: data.body || '',
    };
  });

  window.vizpatchGetMailContext = function () {
    return lastMailContext;
  };

  function generateSessionId() {
    if (window.crypto && typeof window.crypto.randomUUID === 'function') {
      return window.crypto.randomUUID();
    }
    // Fallback fuer Browser ohne crypto.randomUUID — kein Sicherheits-Token,
    // nur eine Sitzungs-Kennung; das Backend bindet die eigentliche
    // Autorisierung an einen serverseitigen HMAC ueber diese Kennung.
    return 'sess-' + Date.now() + '-' + Math.random().toString(36).slice(2);
  }

  let history = [];
  let sessionId = generateSessionId();

  function resetHistory() {
    history = [];
    sessionId = generateSessionId();
    pendingAttachment = null;
    log.innerHTML = '';
  }

  if (resetBtn) {
    resetBtn.addEventListener('click', resetHistory);
  }

  function addBubble(role) {
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble chat-bubble-' + role;
    log.appendChild(bubble);
    log.scrollTop = log.scrollHeight;
    return bubble;
  }

  function parseSseBlock(block) {
    /* Ein SSE-Event kann mehrere data:-Zeilen (eingebettete Newlines im
     * Chunk) und optional eine event:-Zeile enthalten. */
    const lines = block.split('\n');
    let eventType = 'message';
    const dataLines = [];
    for (const line of lines) {
      if (line.startsWith('event:')) {
        eventType = line.slice('event:'.length).trim();
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice('data:'.length).replace(/^ /, ''));
      }
    }
    return { eventType: eventType, data: dataLines.join('\n') };
  }

  async function sendMessage(message) {
    sendBtn.disabled = true;
    addBubble('user').textContent = message;
    const assistantBubble = addBubble('assistant');

    const fd = new FormData();
    fd.append('message', message);
    fd.append('history', JSON.stringify(history));
    fd.append('session_id', sessionId);
    const mailContext = window.vizpatchGetMailContext();
    if (mailContext) {
      fd.append('mail_context', JSON.stringify(mailContext));
    }
    /* Anhang-Metadaten (ATT-03, Plan 12-03): nur mitschicken, wenn ein Upload
     * seit dem letzten Send noch nicht konsumiert wurde. Der serverseitige
     * Pending-Upload ist einmal konsumierbar (12-01) — pendingAttachment wird
     * daher NACH diesem Send unabhaengig vom Ausgang zurueckgesetzt (T-12-12:
     * ein zweiter Send darf nie veraltete Metadaten eines bereits verbrauchten
     * oder abgelaufenen Uploads mitschicken). */
    const attachmentForThisSend = pendingAttachment;
    if (attachmentForThisSend) {
      fd.append('attachment_meta', JSON.stringify(attachmentForThisSend));
    }

    let assistantText = '';
    let sawError = false;

    try {
      const res = await fetch('/chat/' + agentId + '/send', { method: 'POST', body: fd });
      if (!res.ok) {
        const errText = await res.text();
        assistantBubble.textContent = 'Fehler ' + res.status + ': ' + errText;
        return;
      }
      if (attachmentForThisSend) {
        /* Der serverseitige Pending-Upload wird von diesem Turn konsumiert
         * (oder war schon fuer diesen Turn bestimmt) — ein Folge-Send darf
         * ihn nicht nochmal mitschicken. */
        pendingAttachment = null;
        addUploadStatus('Anhang gesendet: ' + attachmentForThisSend.dateiname);
      }
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      while (true) {
        const chunk = await reader.read();
        if (chunk.done) break;
        buffer += decoder.decode(chunk.value, { stream: true });
        let sepIndex;
        while ((sepIndex = buffer.indexOf('\n\n')) !== -1) {
          const block = buffer.slice(0, sepIndex);
          buffer = buffer.slice(sepIndex + 2);
          if (!block.trim()) continue;
          const parsed = parseSseBlock(block);
          if (parsed.eventType === 'error') {
            assistantBubble.textContent += '\n[Fehler: ' + parsed.data + ']';
            sawError = true;
          } else if (parsed.eventType === 'done') {
            /* Stream-Ende — nichts anzuhängen. */
          } else if (parsed.eventType === 'tool') {
            /* Tool-Aktivität (D-80): eigene, dezente Statuszeile im Log — wird
             * NICHT an den Antworttext angehängt, damit die finale Antwort
             * sauber bleibt (z. B. für den history-Turn nach Streamende). */
            const toolLine = document.createElement('div');
            toolLine.className = 'chat-tool-activity';
            toolLine.textContent = parsed.data;
            log.appendChild(toolLine);
          } else {
            assistantText += parsed.data;
            assistantBubble.textContent += parsed.data;
          }
          log.scrollTop = log.scrollHeight;
        }
      }
      /* Verlauf (D-58) erst nach vollständiger Antwort anhängen — bei Fehler
       * während des Streams bleibt der Verlauf konsistent mit dem, was der
       * Assistent tatsächlich vollständig geantwortet hat. */
      if (!sawError) {
        history.push({ role: 'user', content: message });
        history.push({ role: 'assistant', content: assistantText });
      }
    } catch (e) {
      assistantBubble.textContent = 'Netzwerkfehler: ' + e;
    } finally {
      sendBtn.disabled = false;
    }
  }

  /* Auto-Grow (Design-Feinschliff 2026-07-19): das Textfeld waechst beim Tippen
   * bis zur CSS-max-height mit (danach scrollt es intern). resize ist im CSS
   * deaktiviert — diese Logik ersetzt den manuellen Anfasser. */
  function autoGrow() {
    input.style.height = 'auto';
    input.style.height = input.scrollHeight + 'px';
  }

  input.addEventListener('input', autoGrow);

  /* Enter = senden, Shift+Enter = Zeilenumbruch (uebliches Chat-Verhalten;
   * der Platzhaltertext im Feld kuendigt es an). */
  input.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      submitCurrentInput();
    }
  });

  function submitCurrentInput() {
    const message = input.value.trim();
    if (!message || sendBtn.disabled) return;
    input.value = '';
    input.style.height = ''; /* Auto-Grow-Hoehe zuruecksetzen */
    sendMessage(message);
  }

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    submitCurrentInput();
  });
})();
