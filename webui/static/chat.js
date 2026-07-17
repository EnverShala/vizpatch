/* Vanilla-JS-SSE-Client für den Agenten-Chat (D-62, Walking-Skeleton).
 * Keine externe Lib (D-61) — fetch() + ReadableStream, lokal eingebunden wie htmx.min.js.
 * Reset-Button ist bewusst noch ohne Verhalten (Reset-Logik kommt erst in Plan 07-03). */
(function () {
  const root = document.getElementById('chat-root');
  const agentId = root.dataset.agentId;
  const log = document.getElementById('chat-log');
  const form = document.getElementById('chat-form');
  const input = document.getElementById('chat-input');
  const sendBtn = document.getElementById('chat-send-btn');

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
          } else if (parsed.eventType === 'done') {
            /* Stream-Ende — nichts anzuhängen. */
          } else {
            assistantBubble.textContent += parsed.data;
          }
          log.scrollTop = log.scrollHeight;
        }
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
