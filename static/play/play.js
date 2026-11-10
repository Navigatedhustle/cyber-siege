import {
  h,
  api,
  getToken,
  setToken,
  events,
  showError,
  clearError,
  clock,
  badges,
  logButtons,
  floor
} from '/static/common.js';
let state, signature = '',
  refreshPending = false,
  starting = false,
  clientId = '',
  decisionDraft = {
    decision: '',
    evidence: []
  };
const app = document.getElementById('app');
const missionSteps = ['Start', 'Choose', 'Investigate', 'Reveal', 'Commit'];
const names = {
  identity: 'Identity analyst',
  email: 'Email analyst',
  endpoint: 'Endpoint analyst',
  data_access: 'Data access analyst',
  lead: 'Lead analyst'
};

function deviceId() {
  if (clientId) return clientId;
  try {
    clientId = localStorage.getItem('cyber_siege_device') || crypto.randomUUID();
    localStorage.setItem('cyber_siege_device', clientId)
  } catch {
    clientId = crypto.randomUUID()
  }
  return clientId;
}
async function startExperience() {
  if (starting) return;
  starting = true;
  clearError();
  const button = document.getElementById('start-experience');
  if (button) button.disabled = true;
  try {
    const result = await api('/api/experience/start', {
      client_id: deviceId()
    });
    setToken(result.token);
    state = result.state;
    signature = '';
    render(state);
    history.replaceState({}, '', '/play');
  } catch (error) {
    showError(error)
  } finally {
    starting = false;
    if (button) button.disabled = false
  }
}
async function refresh() {
  if (refreshPending) return;
  refreshPending = true;
  try {
    const incoming = await api(getToken() ? '/api/me' : '/api/public');
    if (incoming.team && incoming.team.mode !== 'individual') {
      await startExperience();
      return
    }
    state = incoming;
    render(state);
  } catch (error) {
    if (error.status === 401) {
      setToken('');
      signature = '';
      state = await api('/api/public');
      render(state)
    } else showError(error);
  } finally {
    refreshPending = false
  }
}

function personalAction(action, label, extra = '') {
  return `<button type="button" class="personal-next" data-personal="${action}" ${extra}>${label}<span aria-hidden="true">→</span></button>`;
}

function reveal(s) {
  const person = s.team,
    beat = s.session.reveal,
    m = s.metrics;
  const headings = ['Separate alerts. One connected breach.', 'Your first call was one part of the story.', 'One Fury supported these investigations.', 'Know where the work ran.', 'A real evaluation, shown separately.', 'Which customer comes to mind?', 'Make your next move.'];
  let content = '';
  if (beat === 0) {
    content = `<p>The invoice led to stolen access, an unusual sign-in and finance-file activity. The second account made containment the stronger call.</p><div class="timeline">${person.investigation.data.events.map(item=>`<article><p>${h(item.explanation)}</p>${logButtons(item.log_ids)}</article>`).join('')}</div><div class="notice">Your decision and evidence score: <strong>${person.score.total} points</strong>. Scoring uses the exercise answer key, independently of either model’s opinion.</div>`;
  } else if (beat === 1) {
    const picked = s.alerts.find(a => a.id === person.pick);
    content = `<p>You started with: <strong>${h(picked?.title)}</strong></p><p>The root cause was the invoice. The separate sources became useful when the evidence was connected.</p><div class="box"><strong>${s.picks[person.pick]||0} of ${s.joined}</strong><p>participants in this room chose the same starting alert.</p></div>`;
  } else if (beat === 2) {
    content = s.session.replay ? '<div class="notice">REPLAY · Compute numbers are hidden. Recorded findings add no live inference usage.</div>' : `<p>These are measured totals across the current room, including everyone’s individual investigations.</p><div class="personal-stats"><div><strong>${s.served}</strong><span>Participants served by live AI</span></div><div><strong>${s.investigations_completed}</strong><span>Live investigations completed</span></div><div><strong>${m?floor(m.peak_5s):'—'}</strong><span>Peak output tokens / sec · 5 seconds</span></div></div>${m?.peak_at?`<p class="muted">Peak observed at ${h(new Date(m.peak_at*1000).toLocaleTimeString())}. API usage can arrive at completion, so short windows can be bursty.</p>`:''}<p class="muted">Tokens are small pieces of text a model produces.</p>`;
    content += `<div class="personal-models">${s.models.map(model=>`<p><strong>${h(model.name)}</strong><br>${h(model.serving_stack)}</p>`).join('')}</div>${!s.session.replay?`<div class="box"><p class="eyebrow">OPTIONAL EXTRA CHECK</p><p>Ask each live model to review your case again. This is real additional work on the Fury.</p>${s.session.overdrive==='idle'||s.session.overdrive==='interrupted'?personalAction('overdrive','Run an extra cross-check'):s.session.overdrive==='running'?'<p>Independent reviews are running…</p>':`<p>${s.overdrive_agreement.agreed} of ${s.overdrive_agreement.total} completed extra reviews support your call.</p>`}</div>`:''}`;
  } else if (beat === 3) {
    content = `<div class="box"><p class="eyebrow">INFERENCE</p>${s.boundary.model_endpoints.map(model=>`<p><strong>${h(model.name)}</strong><br>${h(model.serving_stack)}</p>`).join('')}</div><p>${h(s.boundary.retained)}</p><p>${h(s.boundary.traffic)}</p><p>${h(s.boundary.runtime_downloads)}</p><p class="muted">${s.boundary.confirmed?'Deployment facts confirmed.':'Deployment facts await Carlos’s confirmation.'}</p>`;
  } else if (beat === 4) {
    content = `<p class="eyebrow">REAL CUSTOMER EVALUATION</p><p>Today’s exercise was fictional. This customer content is supplied separately and shown exactly as written.</p><div class="personal-story">${h(s.customer_story)}</div>`;
  } else if (beat === 5) {
    content = '<p>Think about customers with sensitive data, repeated AI workloads, and a need to control their infrastructure. Those are conversations worth opening.</p><div class="box"><h2>Start with a question.</h2><p>Which account could benefit from exploring a repeated AI workload on infrastructure they control?</p></div>';
  } else {
    content = '<div class="takeaway-list"><p>AI connected evidence we could not see from individual alerts.</p><p>One Fury supported the room’s AI investigations.</p><p>I know which customer to talk to and what to ask.</p></div><p>Next, create your own Account Action Card. Name an account, an owner and a date for the next conversation.</p>';
  }
  return `<p class="eyebrow">YOUR REVEAL / ${beat+1} OF 7</p><h1>${headings[beat]}</h1>${content}<div class="personal-navigation">${beat?'<button type="button" class="secondary" data-personal="previous_reveal">← Back</button>':''}${beat===6?personalAction('next','Create my Account Action Card'):personalAction('reveal','Continue')}</div>`;
}

function render(s) {
  const person = s.team;
  clock(s);
  document.body.dataset.phase = String(s.session.phase);
  document.body.classList.toggle('is-unjoined', !person);
  document.body.classList.toggle('light', !!person && s.session.phase >= 4);
  document.getElementById('phone-progress').innerHTML = missionSteps.map((name, i) => `<span class="${s.session.phase===i+1?'current':s.session.phase>i+1?'complete':''}" ${s.session.phase===i+1?'aria-current="step"':''}><i></i><b>0${i+1}</b> ${name}</span>`).join('');
  document.getElementById('status').innerHTML = person ? `<div class="row">${badges(s.session)}</div><p class="phone-label">Your individual experience · ${h(person.name)}</p>` : '';
  const nextSignature = JSON.stringify([s.session, person, s.evidence, s.customer_story, s.overdrive_agreement, s.metrics && s.session.phase === 4 ? s.metrics.peak_5s : null]);
  if (signature === nextSignature) return;
  signature = nextSignature;
  const cardForm = app.querySelector('#card');
  const cardDraft = cardForm ? Object.fromEntries(new FormData(cardForm)) : null;
  if (!person) {
    app.innerHTML = '<div class="join-intro"><p class="eyebrow">YOUR DEVICE. YOUR DECISION. YOUR PACE.</p><h1>Make the call.<br>See it connect.</h1><p>Experience a fictional incident on your own. Choose an alert, investigate with local AI and leave with a customer conversation to open.</p><div class="join-benefits"><span>About 20 minutes</span><span>No sign-in</span><span>No team or room code</span></div><button id="start-experience" class="personal-next">Start experience <span aria-hidden="true">→</span></button><p class="muted start-explainer">Your progress is saved in this browser. You can continue without waiting for anyone else.</p></div>';
    return;
  }
  let content = '';
  const p = s.session.phase;
  if (p === 2) {
    content = `<p class="eyebrow">YOUR FIRST CALL</p><h1>Where do you start?</h1><p>Three separate alerts. Choose the one you want to investigate first.</p><div class="stack">${s.alerts.map((a,i)=>`<button type="button" class="alert ${person.pick===a.id?'chosen':''}" data-pick="${a.id}"><span>Alert 0${i+1}${person.pick===a.id?' · Your starting point':''}</span>${h(a.title)}</button>`).join('')}</div>${person.pick?personalAction('investigate','Start my AI investigation'):'<p class="wait muted">Choose an alert above to continue.</p>'}`;
  } else if (p === 3) {
    const inv = person.investigation || {};
    content = '<p class="eyebrow">YOUR INVESTIGATION</p><h1>Connect the evidence.</h1><p>Four specialists examine different sources. A lead analyst connects what they find.</p>';
    if (inv.cached) content += `<div class="notice"><strong>CACHED REHEARSAL</strong> · Recorded ${h(inv.recorded_at)}. Recorded findings add no live token usage.</div>`;
    if (s.session.replay) content += '<div class="notice">REPLAY · Recorded rehearsal findings are shown with their original timing.</div>';
    if (!['running', 'done'].includes(inv.status)) content += `<button id="launch">Launch AI investigation</button>${inv.error?`<p class="error">${h(inv.error)}</p>`:''}`;
    content += Object.entries(person.agents || {}).map(([role, a]) => `<div class="agent ${h(a.status)}"><strong>${h(names[role]||role)} · ${h(a.status)}</strong><span class="muted">${a.events_scanned?a.events_scanned+' records searched':''}${a.tokens_used!=null?' · '+a.tokens_used+' output tokens':''}</span>${a.finding?`<p>${h(a.finding.summary)}</p>${logButtons(a.finding.log_ids)}`:''}</div>`).join('');
    if (inv.status === 'done') content += `<h2>Evidence timeline</h2><p class="muted">A session token keeps someone signed in. MFA asks for a second proof of identity at sign in.</p><div class="timeline">${inv.data.events.map(item=>`<article><p>${h(item.explanation)}</p>${logButtons(item.log_ids)}</article>`).join('')}</div><p>${h(inv.data.summary)}</p>${logButtons(inv.data.summary_log_ids)}`;
    if (!s.twist && inv.status === 'done') content += personalAction('twist', 'Show me the new event');
    if (s.twist) {
      content += `<div class="box"><p class="eyebrow">NEW EVENT / 02:16 AM</p><h2>${h(s.twist.title)}</h2><p>${h(s.twist.summary)}</p>${logButtons(s.twist.log_ids)}</div>`;
      if (!person.decision && inv.status === 'done') content += `<form id="decision"><h2>What do you do?</h2><p>Containment means limiting access while the security team checks what happened.</p><label for="decision-choice">Your decision</label><select id="decision-choice" name="decision" required><option value="" disabled>Choose your call</option><option value="escalate">Escalate for containment</option><option value="investigate">Continue investigating</option><option value="close">Close the alert</option></select><h3>Select up to three supporting evidence cards</h3>${Object.entries(s.evidence).map(([key,item])=>`<label class="evidence-option"><input type="checkbox" name="evidence" value="${key}" ${decisionDraft.evidence.includes(key)?'checked':''}><span>${h(item.title)}</span></label>`).join('')}<button>Submit my decision</button></form>`;
      if (person.decision) {
        const valid = (person.reviews || []).filter(r => !r.error);
        content += `<div class="notice">Decision received: <strong>${h({escalate:'Escalate for containment',investigate:'Continue investigating',close:'Close the alert'}[person.decision])}</strong></div><h2>${valid.length>1?'Two independent model reviews':valid.length===1?'One model reviewed it':'Model review'}</h2><div class="reviews ${valid.length>1?'two':''}">${(person.reviews||[]).map(r=>r.error?`<p class="notice">${h(r.error)}</p>`:`<article class="review"><p class="eyebrow">${h(r.model_name)} · ${h(r.lab)}</p><h3>${h(r.data.verdict.replaceAll('_',' '))}</h3><p>${h(r.data.explanation)}</p><p class="muted">Uncertainty: ${h(r.data.uncertainty)}</p>${logButtons(r.data.log_ids)}</article>`).join('')}</div>`;
        if (valid.length > 1 && valid[0].data.verdict !== valid[1].data.verdict) content += '<div class="notice">The models disagree. Treat this as uncertainty and examine the evidence.</div>';
        if (person.reviews?.length || s.session.replay) content += personalAction('next', 'Reveal the full story');
        else content += '<p class="wait muted">Your independent reviews are running. Your decision is saved.</p>';
      }
    }
  } else if (p === 4) {
    content = reveal(s)
  } else if (p === 5) {
    if (person.card_id) content = `<h1>Your next conversation is committed.</h1><div class="notice">Opportunity hypothesis to validate in discovery. Not based on research of this account.</div><p>Keep your card and open the conversation.</p><div class="stack"><a class="button" href="/card/${h(person.card_id)}" target="_blank" rel="noopener">Open Account Action Card</a><a class="button" href="/card/${h(person.card_id)}.pdf">Download your PDF</a></div>`;
    else content = `<h1>Turn this into a conversation.</h1><div class="notice">Opportunity hypothesis to validate in discovery. Not based on research of this account.</div><form id="card"><label for="account">One account to talk to</label><input id="account" name="account" maxlength="80" required><label for="industry">Industry</label><select id="industry" name="industry">${Object.entries(s.industries).map(([key,name])=>`<option value="${key}">${h(name)}</option>`).join('')}</select><label for="owner">Who owns the next conversation?</label><input id="owner" name="owner" maxlength="80" autocomplete="name" required><label for="target">Target date</label><input type="date" id="target" name="target_date" value="${s.default_target_date}" required><button>Create my Account Action Card</button></form>`;
  }
  app.innerHTML = content;
  if (cardDraft) {
    const form = document.getElementById('card');
    if (form)
      for (const [name, value] of Object.entries(cardDraft)) {
        const field = form.elements.namedItem(name);
        if (field) field.value = value
      }
  }
  const decision = document.getElementById('decision-choice');
  if (decision) decision.value = decisionDraft.decision;
}
document.addEventListener('submit', async event => {
  event.preventDefault();
  clearError();
  const form = event.target,
    data = new FormData(form),
    button = form.querySelector('button');
  button.disabled = true;
  try {
    if (form.id === 'decision') await api('/api/decision', {
      decision: data.get('decision'),
      evidence: data.getAll('evidence')
    });
    if (form.id === 'card') await api('/api/card', Object.fromEntries(data));
    await refresh();
  } catch (error) {
    showError(error)
  } finally {
    button.disabled = false
  }
});
document.addEventListener('change', event => {
  if (event.target.closest('#decision')) {
    const data = new FormData(document.getElementById('decision'));
    decisionDraft = {
      decision: data.get('decision'),
      evidence: data.getAll('evidence')
    };
    if (decisionDraft.evidence.length > 3) {
      event.target.checked = false;
      decisionDraft.evidence = decisionDraft.evidence.filter(x => x !== event.target.value);
      showError('Choose up to three evidence cards.')
    }
  }
});
document.addEventListener('click', async event => {
  const button = event.target.closest('button');
  if (!button) return;
  clearError();
  if (button.id === 'start-experience') {
    await startExperience();
    return
  }
  if (button.id === 'close-log') {
    document.getElementById('raw').close();
    return
  }
  if (button.closest('form')) return;
  button.disabled = true;
  try {
    if (button.dataset.pick) await api('/api/pick', {
      alert: button.dataset.pick
    });
    if (button.id === 'launch') await api('/api/investigate', {});
    if (button.dataset.personal) {
      const action = button.dataset.personal;
      await api('/api/experience/control', {
        action: action === 'investigate' ? 'next' : action,
        expected_phase: state.session.phase,
        expected_reveal: state.session.reveal
      });
      if (action === 'investigate') await api('/api/investigate', {});
    }
    if (button.dataset.log) {
      const row = await api('/api/logs/' + button.dataset.log);
      document.getElementById('logtext').textContent = JSON.stringify(row, null, 2);
      document.getElementById('raw').showModal();
      return
    }
    await refresh();
  } catch (error) {
    showError(error)
  } finally {
    button.disabled = false
  }
});
await refresh();
if (new URL(location.href).searchParams.get('start') === '1') await startExperience();
events('phone', type => {
  document.querySelector('[data-connection]').textContent = 'Connected';
  if (type !== 'metrics') refresh()
});
setInterval(refresh, 7000);
