export const h = value => String(value ?? '').replace(/[&<>"']/g, c => ({
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;'
} [c]));
export const floor = value => Math.floor((value ?? 0) * 10) / 10;
let memoryToken = '';
export function getToken() {
  try {
    return localStorage.getItem('cyber_siege_token') || memoryToken
  } catch {
    return memoryToken
  }
}
export function setToken(token) {
  const previous = getToken();
  memoryToken = token;
  try {
    localStorage.setItem('cyber_siege_token', token)
  } catch {}
  if (previous !== token) window.dispatchEvent(new Event('cyber-token-change'));
}
export async function api(path, body, surface = 'phone') {
  const headers = {};
  if (body) headers['Content-Type'] = 'application/json';
  if (surface === 'phone' && getToken()) headers.Authorization = 'Bearer ' + getToken();
  const response = await fetch(path, {
    method: body ? 'POST' : 'GET',
    headers,
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'same-origin'
  });
  if (!response.ok) {
    let value;
    try {
      value = await response.json()
    } catch {};
    throw Object.assign(new Error(typeof value?.detail === 'string' ? value.detail : 'Request failed (' + response.status + ')'), {
      status: response.status
    })
  }
  return response.json();
}
export function showError(error) {
  const node = document.getElementById('error');
  if (node) {
    node.textContent = error.message || error;
    node.classList.remove('hidden')
  } else console.error(error)
}
export function clearError() {
  document.getElementById('error')?.classList.add('hidden')
}
export function clock(state) {
  if (state.session.self_paced || state.session.mode === 'individual') {
    if (window.cyberClock) clearInterval(window.cyberClock);
    window.cyberClockKey = "";
    document.querySelectorAll("[data-timer]").forEach(n => n.textContent = state.team ? "YOUR PACE" : "START ANYTIME");
    return;
  }
  if (state.session.phase === 1 && state.session.started === false) {
    if (window.cyberClock) clearInterval(window.cyberClock);
    window.cyberClockKey = '';
    document.querySelectorAll('[data-timer]').forEach(n => n.textContent = 'LOBBY');
    return;
  }
  const key = JSON.stringify([state.session.id, state.session.deadline, state.session.paused, state.session.remaining_seconds]);
  if (window.cyberClockKey === key) return;
  window.cyberClockKey = key;
  const end = Date.now() + state.session.remaining_seconds * 1000;
  const tick = () => {
    const seconds = Math.max(0, Math.floor(state.session.paused ? state.session.remaining_seconds : (end - Date.now()) / 1000));
    document.querySelectorAll('[data-timer]').forEach(n => n.textContent = String(Math.floor(seconds / 60)).padStart(2, '0') + ':' + String(seconds % 60).padStart(2, '0') + (state.session.paused ? ' PAUSED' : ''))
  };
  if (window.cyberClock) clearInterval(window.cyberClock);
  tick();
  window.cyberClock = setInterval(tick, 1000);
}
export async function events(surface, onEvent) {
  while (true) {
    const controller = new AbortController();
    const changed = () => controller.abort();
    if (surface === 'phone') window.addEventListener('cyber-token-change', changed, {
      once: true
    });
    try {
      const token = surface === 'phone' ? getToken() : '';
      const headers = {
        'X-Surface': surface === 'phone' && !token ? 'screen' : surface
      };
      if (token) headers.Authorization = 'Bearer ' + token;
      const response = await fetch('/api/events', {
        headers,
        credentials: 'same-origin',
        signal: controller.signal
      });
      if (!response.ok) throw new Error('SSE unavailable');
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      onEvent('connected', {});
      while (true) {
        const {
          value,
          done
        } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, {
          stream: true
        });
        let end;
        while ((end = buffer.indexOf('\n\n')) >= 0) {
          const block = buffer.slice(0, end);
          buffer = buffer.slice(end + 2);
          let type = 'message',
            data = '';
          for (const line of block.split('\n')) {
            if (line.startsWith('event:')) type = line.slice(6).trim();
            if (line.startsWith('data:')) data += line.slice(5).trim()
          }
          if (data) onEvent(type, JSON.parse(data))
        }
      }
    } catch {} finally {
      window.removeEventListener('cyber-token-change', changed);
    }
    if (controller.signal.aborted) continue;
    document.querySelectorAll('[data-connection]').forEach(n => n.textContent = 'Reconnecting…');
    await new Promise(resolve => setTimeout(resolve, 2000));
  }
}
export const badges = s => `${s.label==='REHEARSAL'?'<span class="badge rehearsal">REHEARSAL</span>':''} ${s.replay?'<span class="badge replay">REPLAY</span>':''}`;
export const logButtons = ids => (ids || []).map(id => `<button type="button" class="secondary log-button" data-log="${h(id)}">${h(id)}</button>`).join('');
