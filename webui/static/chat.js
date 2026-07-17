/* Vanilla-JS-SSE-Client für den Agenten-Chat (D-62).
 * Keine externe Lib (D-61) — fetch() + ReadableStream, lokal eingebunden wie htmx.min.js.
 *
 * Verlauf (D-58): lebt ausschließlich in diesem In-Memory-Array — keine
 * DB, kein localStorage. Verlauf endet mit dem Seitenleben (Reload/Tab-Schluss).
 * Reset-Button (D-58) leert history + #chat-log.
 *
 * mail_context (D-65, Phase-8-Vorarbeit): window.vizpatchGetMailContext ist ein
 * überschreibbarer Hook. In Phase 7 liefert er null (kein Mail-Kontext). Phase 8
 * (Outlook-Add-in) überschreibt diese Funktion via Office.js mit der gerade
 * geöffneten Mail — keine Änderung an chat.js nötig. */
(function () {
  const root = document.getElementById('chat-root');
  const agentId = root.dataset.agentId;
  const log = document.getElementById('chat-log');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send-btn');
  const resetBtn = document.getElementById('chat-reset-btn');

  /** Phase-8-Erweiterungspunkt (D-65): Office.js überschreibt diesen Hook, um
   * die aktuell geöffnete Mail als {subject, sender, body} zurückzugeben.
   * Phase 7: liefert bewusst null — kein Mail-Kontext vorhanden. */
  if (typeof window.vizpatchGetMailContext !== 'function') {
    window.vizpatchGetMailContext = function () {
      return null;
    };
  }

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
