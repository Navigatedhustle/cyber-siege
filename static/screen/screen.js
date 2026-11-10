import {
  h,
  api,
  events,
  clock,
  badges,
  floor,
  showError
} from '/static/common.js';
let state, refreshing = false,
  last = '',
  lastPhase = 0;
const root = document.getElementById('screen');
const roles = [
  ['identity', 'ID'],
  ['email', 'EMAIL'],
  ['endpoint', 'DEVICE'],
  ['data_access', 'FILES'],
  ['lead', 'Lead']
];

function metric(value, label) {
  return `<div class="metric"><span class="number">${h(value)}</span><span class="unit">${h(label)}</span></div>`
}

function lanes(s) {
  return `<div class="model-lanes">${s.models.map(m=>{const x=s.metrics?.models[m.key];return `<div class="model-lane"><div>${h(m.name)}<small>${h(m.serving_stack)} · ${h(x?.source||'awaiting sample')}${x?.other_traffic_or_divergence?' · app usage selected after counter divergence':''}</small></div><strong>${x?floor(x.tps_5s):'—'} <small>output tokens / sec</small></strong></div>`}).join('')}</div>`
}

function compute(s) {
  if (s.session.replay) return `<div class="replay-banner">REPLAY · Recorded during rehearsal on ${h(s.recorded_at||'date unavailable; no recording loaded')}</div>`;
  const m = s.metrics;
  if (!m) return '<div class="notice">Waiting for measured session samples.</div>';
  return `<div class="metrics">${metric(floor(m.total.tps_5s),'Output tokens / sec · 5 second window')}${metric(m.total.active_streams,'Active concurrent streams')}${m.gpu?metric(m.gpu.utilization+'%','GPU utilization'):''}${m.gpu?metric(floor(m.gpu.power_watts)+' W','GPU power draw'):''}${metric(s.models.length,'Models live on this Fury')}</div>${lanes(s)}`
}

function overdriveMeter(s) {
  const m = s.metrics;
  return s.session.overdrive === 'running' && !s.session.replay ? `<aside class="overdrive running"><p class="eyebrow">Overdrive · Real model reviews</p><b>${m?floor(m.total.tps_5s):'—'} tokens / sec</b><small>${m?.total.active_streams??'—'} active streams${m?.gpu?' · '+floor(m.gpu.power_watts)+' W':''}</small>${s.models.map(x=>`<small>${h(x.name)} · ${floor(m?.models[x.key]?.tps_5s||0)} tokens / sec</small>`).join('')}<small>The room pushes the Fury to its limit.</small></aside>` : ''
}

function render(s) {
  clock(s);
  const p = s.session.phase;
  const rosterPage = Math.floor(Date.now() / 10000) % Math.max(1, Math.ceil(s.teams.length / 15));
  const visiblePeople = s.teams.slice(rosterPage * 15, rosterPage * 15 + 15);
  const cardPage = Math.floor(Date.now() / 10000) % Math.max(1, Math.ceil(s.commitments.length / 15));
  const visibleCards = s.commitments.slice(cardPage * 15, cardPage * 15 + 15);
  document.body.dataset.phase = String(p);
  document.body.classList.toggle('light', p >= 4);
  document.getElementById('badges').innerHTML = badges(s.session);
  document.getElementById('phase').textContent = `0${p} / 05 · ${s.session.phase_name}`;
  document.getElementById('footnote').textContent = p <= 3 ? 'HP ZGX Fury · Every displayed measurement comes from this session' : 'HP Limitless · From evidence to a customer conversation';
  let html = '';
  if (p === 1) {
    html = `<section class="lobby"><div><p class="eyebrow">HP LIMITLESS / COBALT RIDGE DISTRIBUTION</p><div class="time217">2:17 <span>AM</span></div><h1>Your next call matters.</h1><p>It is 2:17 AM. Your security team sees suspicious activity. You have limited time to decide what needs attention.</p><p class="small">One person. One device. Your own pace.</p><div class="lobby-state"><span></span>Everyone can start individually. No sign-in or room code.</div></div><aside class="join"><p class="join-kicker">START YOUR EXPERIENCE</p><img src="/api/qr.png?session=${h(s.session.id)}" alt="Scan to join this workshop"><p class="join-instruction">Scan. Press Start experience. Make your own call.</p><p class="join-code-label">NO SIGN-IN REQUIRED</p><p class="join-address">${h(new URL(s.join_url).host)}/play</p></aside></section><div class="room-counter"><strong>${s.joined}</strong> ${s.joined===1?'participant':'participants'} in the room <span>Press F for full screen</span></div><div class="team-wall">${visiblePeople.map(t=>`<div class="team-pill arrive">${h(t.name)}</div>`).join('')}</div>`;
  }
  if (p === 2) {
    html = `<section class="pick-layout"><div><p class="eyebrow">Three alerts. One first call.</p><h1>Where would you start?</h1><p class="intro">Each alert shows one part of the picture.<br>Choose a starting point on your phone.</p><p class="muted">${Object.values(s.picks).reduce((a,b)=>a+b,0)} of ${s.joined} participants have made their first call.</p></div><div>${s.alerts.map(a=>`<article class="pick-row"><strong>${h(a.title)}</strong><div class="pick-bar"><i style="width:${s.joined?100*(s.picks[a.id]||0)/s.joined:0}%"></i><b>${s.picks[a.id]||0} participants</b></div></article>`).join('')}</div></section>`
  }
  if (p === 3) {
    html = `${compute(s)}<div class="grid-title"><h1>One Fury. The room investigates.</h1><span class="muted">${s.investigations_completed} live investigations completed${s.teams.length>15?` · Showing ${rosterPage*15+1}–${Math.min((rosterPage+1)*15,s.teams.length)} of ${s.teams.length}`:''}</span></div><div class="investigation-grid" style="--teams:${Math.max(1,visiblePeople.length)}">${visiblePeople.map(t=>`<article class="team-column"><h3 title="${h(t.name)}">${h(t.name)}</h3>${roles.map(([key,name])=>{const status=t.agents[key]?.status||'idle';return `<div class="agent-cell ${h(status)} ${status==='started'?'running':''}">${name}<br><small>${h(status)}</small></div>`}).join('')}</article>`).join('')}</div><p class="muted small">${s.session.twist?'NEW EVENT: A service account accessed the same finance files from the same unusual network.':'Four specialist agents per participant, then one lead analyst. Tap evidence on your phone to see the fictional logs.'}</p>`
  }
  if (p === 4) {
    const b = s.session.reveal;
    html = '<section class="reveal">';
    if (b <= 1) {
      html += `<p class="eyebrow">The chain · Fictional exercise</p><h1>Separate alerts. One connected breach.</h1><div class="chain">${[
 ['01','The invoice','A lookalike supplier sends an attachment. A finance employee opens it.','EML9001 · EDR9001'],
 ['02','The stolen access','Browser token access and a callout expose the session.','EDR9002 · NET9001'],
 ['03','The replayed session','The same session signs in from a new network without another MFA prompt.','IDP9001'],
 ['04','The finance files','That session enumerates and downloads 428 sensitive files.','FIL9001 · FIL9002'],
 ['05','The second account','A service account uses the same external network outside its normal window.','FIL9003 · FIL9005']].map(([n,title,text,ids],i)=>`<article class="chain-item" style="animation-delay:${i*.15}s"><b>${n}</b><h2>${title}</h2><p>${text}</p><code>${ids}</code></article>`).join('')}</div>`
    }
    if (b === 2) {
      const ranked = Object.entries(s.picks).sort((a, b) => b[1] - a[1]);
      const start = ranked[0] || ['invoice', 0],
        label = s.alerts.find(a => a.id === start[0])?.title || 'the invoice';
      html += `<p class="eyebrow">The room stat · Your first calls</p><div class="big-stat">${start[1]} of ${s.joined}</div><h1>participants started with this alert.</h1><p class="intro">${h(label)}</p><div class="box"><h2>The root cause was the invoice.</h2><p>AI connected evidence we could not see from individual alerts.</p></div>`
    }
    if (b === 3) {
      const m = s.metrics;
      html += `<p class="eyebrow">The compute · Measured in this session</p><h1>One machine supported the room.</h1>${s.session.replay?compute(s):`<div class="compute-stats"><div><div class="big-stat">${s.served}</div><p>Participants served by the Fury</p></div><div><div class="big-stat">${s.investigations_completed}</div><p>Live AI investigations completed</p></div><div><div class="big-stat">${m?floor(m.total.tps_5s):'—'}</div><p>Aggregate output tokens / sec</p></div></div><p class="intro">Session peak: ${m?floor(m.peak_5s):'—'} output tokens / sec${m?.peak_at?' at '+h(new Date(m.peak_at*1000).toLocaleTimeString()):''} · Five second window</p>`}${lanes(s)}<p>${s.models.map(m=>h(m.name)+' · '+h(m.parameters)+' · '+h(m.serving_stack)).join('<br>')}</p><p>${s.metrics?.total.total_tokens??'—'} app counted output tokens · ${s.agent_runs??'See facilitator console for total'} agent runs</p><p>${s.overdrive_agreement.agreed} of ${s.overdrive_agreement.total} completed Overdrive model reviews agreed with the participants’ calls.</p>`
    }
    if (b === 4) {
      html += `<p class="eyebrow">The boundary · Verify the deployment facts</p><h1>Where the work ran.</h1><div class="facts"><div class="box"><h2>Configured inference endpoints</h2>${s.boundary.model_endpoints.map(m=>`<p><strong>${h(m.name)}</strong><br>${h(m.model_id)}<br>${h(m.serving_stack)}<br><code>${h(m.base_url)}</code></p>`).join('')}</div><div class="box"><h2>Storage and traffic</h2><p>${h(s.boundary.retained)}</p><p>${h(s.boundary.traffic)}</p><p>${h(s.boundary.runtime_downloads)}</p><p>${h(s.deployment.outbound_observation.value)}</p><p><strong>${s.boundary.confirmed?'Deployment facts confirmed.':'Deployment facts await Carlos’s confirmation.'}</strong></p></div></div>`
    }
    if (b === 5) {
      html += `<p class="eyebrow">Real customer evaluation</p><h1>From today’s fictional exercise to a real evaluation.</h1><p class="small">Today’s exercise was fictional. The following customer content is supplied separately and shown exactly as written.</p><div class="story">${h(s.customer_story)}</div>`
    }
    if (b === 6) {
      html += `<p class="eyebrow">The sales connection</p><h1>Which customer comes to mind?</h1><p class="intro">Think about customers with sensitive data, repeated AI workloads, and a need to control their infrastructure. Those are conversations worth opening.</p><div class="box"><h2>Bring one account into a ZGX Virtual Lab discussion.</h2><p class="intro">Choose a use case to explore. Name the person who will open the conversation. Pick a date.</p></div>`
    }
    if (b === 7) {
      if (s.session.leaderboard) {
        const ranked = s.teams.filter(t => t.score).sort((a, b) => b.score.total - a.score.total || (a.response_seconds || 0) - (b.response_seconds || 0)).slice(0, 3);
        html += `<p class="eyebrow">Evidence first · Response time breaks ties</p><h1>The room’s strongest calls.</h1><div class="leaderboard">${ranked.map((t,i)=>`<article><p class="eyebrow">0${i+1}</p><h2>${h(t.name)}</h2><div class="big-stat">${t.score.total}</div><p>points</p></article>`).join('')}</div>`
      } else html += `<p class="eyebrow">Your next move</p><h1>Take the conversation forward.</h1><p class="intro">Your Account Action Card opens in the next phase.</p>`
    }
    html += '</section>';
    html += '<div id="overdrive-meter"></div>';
  }
  if (p === 5) {
    html = `<section class="reveal"><p class="eyebrow">A conversation worth opening</p><div class="closing"><div><h1>Three things to take with you.</h1><div class="takeaways"><div class="takeaway"><b>01</b>AI connected evidence we could not see from individual alerts.</div><div class="takeaway"><b>02</b>One Fury supported the room’s AI investigations.</div><div class="takeaway"><b>03</b>I know which customer to talk to and what to ask.</div></div></div><div><div class="big-stat">${s.commitment_count}</div><h2>account commitments</h2><p>Name the next conversation on your phone.</p></div></div><div class="rule"></div><div class="commitments">${visibleCards.map(c=>`<div class="commitment arrive"><b>${h(c.account)}</b><span>${h(c.owner_first_name)} owns the next conversation</span></div>`).join('')}</div></section>`
  }
  const beat = s.session.reveal;
  const relevantTeams = p === 3 ? s.teams : (p === 1 || p === 4 && beat === 7 ? s.teams.map(t => [t.id, t.name, t.score, t.decision_at]) : null);
  const signature = JSON.stringify([p, beat, rosterPage, cardPage, s.session.twist, relevantTeams, (p === 2 || p === 4 && beat === 2) ? s.picks : null, s.joined, (p === 3 || p === 4 && beat === 3) ? s.metrics : null, s.session.overdrive, p === 5 ? s.commitments : null, s.session.leaderboard, s.session.replay, p === 4 && beat === 5 ? s.customer_story : null, (p === 3 || p === 4 && beat === 3) ? [s.served, s.investigations_completed] : null]);
  if (last !== signature) {
    root.innerHTML = html;
    last = signature
  }
  const meter = document.getElementById('overdrive-meter');
  if (meter) meter.innerHTML = overdriveMeter(s);
  lastPhase = p;
}
async function refresh() {
  if (refreshing) return;
  refreshing = true;
  try {
    state = await api('/api/public', undefined, 'screen');
    render(state)
  } catch (error) {
    showError(error)
  } finally {
    refreshing = false
  }
}
document.addEventListener('keydown', async event => {
  if (event.code === 'KeyF') {
    if (!document.fullscreenElement) await document.documentElement.requestFullscreen();
    else await document.exitFullscreen()
  }
  if (event.code === 'Space' && state?.session.phase === 4) {
    event.preventDefault();
    try {
      await api('/api/control', {
        action: 'reveal'
      }, 'admin');
      await refresh()
    } catch (error) {
      showError('The presentation could not advance. ' + error.message)
    }
  }
});
await refresh();
events('screen', (type, data) => {
  document.querySelector('[data-connection]').textContent = 'Connected';
  if (type === 'metrics' && state && !state.session.replay && data.sample) {
    state.metrics = data.sample;
    render(state)
  } else refresh()
});
setInterval(refresh, 5000);
