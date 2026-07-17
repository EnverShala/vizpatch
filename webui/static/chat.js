/* Vanilla-JS-SSE-Client für den Agenten-Chat (D-62).
 * Keine externe Lib (D-61) — fetch() + ReadableStream, lokal eingebunden wie htmx.min.js.
 *
 * Verlauf (D-58): lebt ausschließlich in diesem In-Memory-Array — keine
 * DB, kein localStorage. Verlauf endet mit dem Seitenleben (Reload/Tab-Schluss).
 * Reset-Button (D-58) leert history + #chat-log.
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

  let history = [];

  function resetHistory() {
    history = [];
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
    const mailContext = window.vizpatchGetMailContext();
    if (mailContext) {
      fd.append('mail_context', JSON.stringify(mailContext));
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

  form.addEventListener('submit', function (event) {
    event.preventDefault();
    const message = input.value.trim();
    if (!message) return;
    input.value = '';
    sendMessage(message);
  });
})();
