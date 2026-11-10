import {
  h,
  api,
  events,
  clock,
  badges,
  floor,
  showError,
  clearError
} from '/static/common.js';
let active = false,
  refreshing = false,
  soundEnabled = false,
  state, toastTimer, eventsStarted = false;
const htmlCache = new Map();
const phases = [
  ['Welcome screen', 'View'],
  ['First choices', 'View'],
  ['Investigation activity', 'View'],
  ['Room reveal', 'View'],
  ['Commitments wall', 'View']
];
const revealNames = ['The attack chain', 'The attack chain', 'The room’s first calls', 'The measured compute', 'Where the work ran', 'The real customer evaluation', 'The sales connection', 'The room’s next move'];

function html(id, value) {
  if (htmlCache.get(id) !== value) {
    document.getElementById(id).innerHTML = value;
    htmlCache.set(id, value)
  }
}

function text(id, value) {
  document.getElementById(id).textContent = value
}

function toast(message) {
  const node = document.getElementById('toast');
  node.textContent = message;
  node.classList.remove('hidden');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.add('hidden'), 3500)
}
async function refresh() {
  if (refreshing) return;
  refreshing = true;
  try {
    state = await api('/api/facilitator', undefined, 'admin');
    active = true;
    document.body.classList.add('is-connected');

    document.getElementById('console').classList.remove('hidden');
    render(state);
    connectEvents();
  } catch (error) {
    showError(error)
  } finally {
    refreshing = false
  }
}

function primary() {
  return {
    label: 'Start experience',
    href: '/play?start=1'
  };
}

function guide() {
  return {
    title: 'Everyone starts individually.',
    description: 'Share the experience link or display the QR code. Each person starts, investigates and continues on their own device. No sign-in, team or room code is needed.',
    hint: 'These optional presentation controls do not advance anyone’s personal experience.',
    line: 'Open the link on your own phone. Press Start experience, choose an alert and follow the evidence at your own pace.'
  };
}

function renderSide(s) {
  return `<span class="side-label">SCAN TO START INDIVIDUALLY</span><img class="invite-qr" src="/api/qr.png?session=${h(s.session.id)}" alt="Start your individual experience"><p class="side-caption">No sign-in. No team or room code.</p><button class="secondary copy-code" data-copy="link">Copy experience link ↗</button>`;
}

function render(s) {
  const p = s.session.phase,
    g = guide(s),
    action = primary(s),
    models = s.models;
  const heroReady = models.some(m => m.key === 'hero') && !s.session.replay;
  document.getElementById('health-status').className = 'health-status ' + (heroReady ? 'ready' : s.session.replay ? 'replay' : '');
  text('health-status', s.session.replay ? 'Replay mode' : heroReady ? 'Live AI ready' : 'Live AI unavailable');
  html('phase-rail', '<ol>' + phases.map(([name, duration], i) => `<li class="${p===i+1?'current':p>i+1?'completed':''}"${p===i+1?' aria-current="step"':''}><span>${p>i+1?'✓':'0'+(i+1)}</span><div>${name}<small class="phase-duration">${duration}</small></div></li>`).join('') + '</ol>');
  html('badges', badges(s.session));
  text('session-label', s.session.label === 'REHEARSAL' ? 'PRACTICE SESSION' : 'YOUR WORKSHOP');
  text('task-eyebrow', `0${p} / ${phases[p-1][0]}`);
  text('task-title', g.title);
  text('task-description', g.description);
  text('task-hint', g.hint);
  text('presenter-line', g.line);
  html('task-actions', action.href ? `<a id="primary-action" class="button" href="${action.href}">${h(action.label)} <span aria-hidden="true">${action.href.startsWith('/export')?'↓':'→'}</span></a>` : `<button id="primary-action" data-primary="${action.action}">${h(action.label)} <span aria-hidden="true">→</span></button>${p===1?'<a class="button secondary" href="/screen" target="_blank" rel="noopener">Open room screen <span aria-hidden="true">↗</span></a>':''}`);
  html('task-side', renderSide(s));
  const decided = s.teams.filter(t => t.decision).length;
  html('room-summary', `<div class="room-stat"><strong>${s.joined}</strong><span>participants in the room<br>${s.connected_phones} connected phones</span></div><div class="room-stat"><strong>${decided}</strong><span>individual decisions<br>${s.investigations_completed} live investigations</span></div><div class="room-stat"><strong>${s.commitment_count}</strong><span>account commitments<br>with an owner and a date</span></div>`);
  text('team-count', `${s.joined} participants`);
  html('teams', s.teams.length ? s.teams.map(t => `<div class="team-row"><div><strong>${h(t.name)}</strong><span class="team-state">${h(t.card_id?'Account committed':t.decision?'Decision received':t.investigation?.status==='done'?'Investigation complete':t.investigation?.status==='running'?'Investigating now':t.pick?'First call chosen':'Joined and ready')}${t.investigation?.cached?' · Cached rehearsal':''}${t.score?' · '+t.score.total+' points':''}</span></div><div class="team-actions"><button data-rename="${h(t.id)}" class="secondary">Rename</button><button data-remove="${h(t.id)}" class="secondary">Remove</button></div></div>`).join('') : '<div class="empty-teams"><span class="empty-symbol" aria-hidden="true">＋</span><strong>Your room starts with the first participant.</strong><p>Open the room screen and invite participants to scan the QR code. Their names will appear here.</p></div>');
  text('readiness-title', s.session.replay ? 'Recorded rehearsal mode.' : heroReady ? `${models.length} ${models.length===1?'model':'models'} ready for your room.` : 'Check the live model connection.');
  html('readiness-models', models.map(m => `<div class="readiness-model">${h(m.name)}</div>`).join(''));
  text('readiness-detail', s.session.replay ? 'Recorded findings are labeled. Replay adds no live token usage.' : heroReady ? 'Model requests run on the configured local Fury endpoints.' : 'Check Model health below. Replay needs a valid rehearsal recording.');
  const pause = document.getElementById('pause-control');
  pause.textContent = s.session.paused ? 'Resume timer' : 'Pause timer';
  pause.disabled = !s.session.started;
  document.querySelector('[data-action="extend"]').disabled = !s.session.started;
  document.querySelector('[data-action="previous"]').disabled = p === 1;
  document.querySelector('[data-action="twist"]').disabled = p !== 3 || s.session.twist;
  document.querySelector('[data-action="lock"]').disabled = p !== 3 || s.session.locked;
  document.querySelector('[data-action="leaderboard"]').disabled = p < 4;
  text('content-summary', s.warnings.length ? `${s.warnings.length} items to review before the event` : 'No pending content checks reported');
  renderDiagnostics(s);
  if (s.session.sound && !soundEnabled) {
    try {
      const audio = new AudioContext(),
        osc = audio.createOscillator(),
        gain = audio.createGain();
      osc.connect(gain);
      gain.connect(audio.destination);
      osc.frequency.value = 440;
      gain.gain.value = .05;
      osc.start();
      gain.gain.exponentialRampToValueAtTime(.001, audio.currentTime + .3);
      osc.stop(audio.currentTime + .3)
    } catch {}
  }
  soundEnabled = s.session.sound;
  clock(s);
}

function renderDiagnostics(s) {
  const gpu = s.metrics?.gpu;
  html('room', `<p>${s.joined} participants · ${s.connected_phones} connected phones · ${s.sse_clients} SSE clients</p><p>${s.served} participants served · ${s.investigations_completed} live investigations · ${s.agent_runs} usage events</p><p>Public URL: ${s.public_health.reachable===null?'not checked':s.public_health.reachable?'reachable':'unreachable'} · ${h(s.join_url)}</p>`);
  html('gpu', gpu ? `<p><strong>${h(gpu.name)}</strong> · ${gpu.utilization}% utilization · ${floor(gpu.power_watts)} W</p><p>${floor(gpu.memory_used_bytes/2**30)} / ${floor(gpu.memory_total_bytes/2**30)} GiB used</p><p>${gpu.processes.map(p=>`${h(p.model||'unattributed')} PID ${p.pid}: ${p.memory_bytes===null?'memory unavailable':floor(p.memory_bytes/2**30)+' GiB'}`).join('<br>')}</p>` : '<p>GPU telemetry is hidden during replay or unavailable.</p>');
  html('models', Object.entries(s.model_health).map(([key, m]) => `<article class="box"><p class="eyebrow">${h(m.lab)} / ${h(m.serving_stack)}</p><h2>${h(m.name)}</h2><p class="model-status">${m.healthy?'UP':'DOWN'} · ${m.qualified?'GATE PASSED':'NOT QUALIFIED'}</p><dl><dt>Exact model ID</dt><dd>${h(m.model_id)}</dd><dt>Last latency</dt><dd>${m.last_latency===null?'—':floor(m.last_latency)+' seconds'}</dd><dt>Queue / active</dt><dd>${m.queue_depth} / ${m.active}</dd><dt>Concurrency cap</dt><dd>${m.concurrency_cap}</dd><dt>GPU process memory</dt><dd>${gpu?.processes.some(p=>p.model===key&&p.memory_bytes!==null)?floor(gpu.processes.filter(p=>p.model===key).reduce((sum,p)=>sum+(p.memory_bytes||0),0)/2**30)+' GiB':'unavailable'}</dd><dt>Metrics source</dt><dd>${h(m.metrics?.source||'not measured')}</dd><dt>App token total</dt><dd>${m.metrics?.app.total_tokens??'—'}</dd><dt>Server token total</dt><dd>${m.metrics?.server?.total_tokens??'not available'}</dd><dt>Cross check</dt><dd>${m.metrics?.other_traffic_or_divergence?'Divergence over 10%. App source selected.':'No divergence detected yet'}</dd><dt>Fallbacks to hero</dt><dd>${m.fallbacks}</dd></dl>${m.error?`<p class="${m.healthy?'notice':'error'}">${h(m.error)}</p>`:''}</article>`).join(''));
  html('warnings', s.warnings.map(w => `<li>${h(w)}</li>`).join(''));
  text('session-detail', `Session ${s.session.id} · Reveal ${s.session.reveal}/7 · New event ${s.session.twist?'introduced':'waiting'} · Decisions ${s.session.locked?'locked':'open'} · Overdrive ${s.session.overdrive}`);
}
async function command(body) {
  await api('/api/control', body, 'admin');
  await refresh()
}
document.getElementById('cancel-new').addEventListener('click', () => document.getElementById('new-workshop').close());
document.getElementById('new-workshop-form').addEventListener('submit', async event => {
  event.preventDefault();
  const button = event.target.querySelector('button[type=submit]');
  button.disabled = true;
  try {
    await command({
      action: 'create',
      label: new FormData(event.target).get('mode')
    });
    document.getElementById('new-workshop').close();
    toast('New experience room ready. Everyone can press Start experience.')
  } catch (error) {
    showError(error)
  } finally {
    button.disabled = false
  }
});
document.addEventListener('click', async event => {
  const button = event.target.closest('button');
  if (!button || button.closest('#new-workshop-form')) return;
  clearError();
  if (button.id === 'new-session') {
    document.getElementById('new-workshop').showModal();
    return
  }
  if (button.dataset.copy) {
    try {
      await navigator.clipboard.writeText(state.join_url);
      toast('Experience link copied.')
    } catch {
      window.prompt('Copy this experience link', state.join_url)
    }
    return
  }
  let body;
  if (button.dataset.primary) {
    if (button.dataset.primary === 'reveal-start') {
      const missing = state.teams.filter(t => !t.decision).length;
      if (missing && !confirm(`${missing} participants have not submitted a decision. Lock decisions and reveal the story?`)) return;
      body = {
        action: 'next'
      };
    } else body = {
      action: button.dataset.primary
    };
  }
  if (button.dataset.action) body = {
    action: button.dataset.action
  };
  if (button.id === 'new-live' || button.id === 'new-rehearsal') {
    document.getElementById('workshop-mode').value = button.id === 'new-live' ? 'LIVE' : 'REHEARSAL';
    document.getElementById('new-workshop').showModal();
    return;
  }
  if (button.id === 'reset') {
    if (!confirm('Reset this room? Participants will start a new workshop. Previous results remain saved.')) return;
    body = {
      action: 'reset',
      confirm: true,
      label: state.session.label
    };
  }
  if (button.dataset.rename) {
    const name = prompt('New participant name (24 characters maximum)');
    if (!name) return;
    body = {
      action: 'rename',
      team_id: button.dataset.rename,
      name
    }
  }
  if (button.dataset.remove) {
    if (!confirm('Remove this participant from the room?')) return;
    body = {
      action: 'remove',
      team_id: button.dataset.remove
    }
  }
  if (!body) return;
  button.disabled = true;
  try {
    if (button.dataset.primary === 'reveal-start') await api('/api/control', {
      action: 'lock'
    }, 'admin');
    await command(body)
  } catch (error) {
    showError(error)
  } finally {
    button.disabled = false
  }
});

function connectEvents() {
  if (eventsStarted) return;
  eventsStarted = true;
  events('admin', () => {
    document.querySelector('[data-connection]').textContent = 'Connected';
    if (active) refresh()
  })
}
await refresh();
setInterval(refresh, 5000);
