'use strict';
const $ = s => document.querySelector(s);
const app = $('#app');
const q = new URLSearchParams(location.search);
const path = location.pathname;
const isStation = path === '/station';
let content, state, socket, reconnectTimer, selectedRobot = 'SCOUT', admin = false, roomCode = q.get('room') || '', toastTimer;
let saved;
try { saved = JSON.parse(localStorage.getItem(`siege:${roomCode}:${isStation ? q.get('team') : 'player'}`) || 'null'); } catch { saved = null; }
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
const e = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const industryLabel = v => String(v).replaceAll('_',' ');
const money = n => '$' + Math.round(n || 0).toLocaleString('en-US');
const clock = n => `${String(Math.floor(Math.max(0,n)/60)).padStart(2,'0')}:${String(Math.floor(Math.max(0,n)%60)).padStart(2,'0')}`;
const brand = '<div class="brand">CYBER <span>SIEGE</span><small>HP ZGX FURY · LOCAL AI IN ACTION</small></div>';
function html(id, value) { const el = document.getElementById(id); if (el && el.innerHTML !== value) el.innerHTML = value; }
function toast(text) { $('#toast').textContent = text; $('#toast').classList.add('visible'); clearTimeout(toastTimer); toastTimer = setTimeout(() => $('#toast').classList.remove('visible'), 4000); }
async function api(url, body) {
  const response = await fetch(url, {method: body === undefined ? 'GET' : 'POST', headers: {'Content-Type':'application/json', ...(saved?.token ? {Authorization:'Bearer '+saved.token} : {})}, ...(body === undefined ? {} : {body:JSON.stringify(body)})});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Check your entry and try again.');
  return data;
}
function robot(name, status = 'idle') {
  const color = content.robots[name][2], icon = content.robots[name][3], index = Object.keys(content.robots).indexOf(name);
  return `<svg class="robot-art" viewBox="0 0 100 110" role="img" aria-label="${e(name)} ${e(status)}"><g stroke="#071321" stroke-width="3" stroke-linejoin="round"><path d="M50 22V9" stroke="${color}"/><circle class="antenna" cx="50" cy="7" r="5" fill="${color}"/><rect x="18" y="23" width="64" height="43" rx="${12+index}" fill="${color}"/><rect x="25" y="34" width="50" height="21" rx="8" fill="#0b2133"/><g class="eyes" fill="#e8fbff" stroke="none"><rect x="34" y="40" width="9" height="8" rx="3"/><rect x="57" y="40" width="9" height="8" rx="3"/></g><rect x="24" y="67" width="52" height="28" rx="10" fill="#243f54" stroke="${color}"/><path d="M32 96V104H23M65 96V104H76" stroke="${color}" stroke-width="7"/><path d="M23 73L12 81L9 75" stroke="${color}" stroke-width="9"/><path class="hand" d="M77 73L88 80L92 69" stroke="${color}" stroke-width="9"/><path class="beam" d="M30 55L5 98H95L70 55" fill="${color}" opacity=".15" stroke="none"/></g><text x="50" y="88" fill="${color}" font-size="24" text-anchor="middle" font-family="Arial">${e(icon)}</text></svg>`;
}
function villain(key) {
  const names = {invoice:'PHANTOM INVOICE', phisher:'PHISHER', lockjaw:'LOCKJAW', leaky:'LEAKY'};
  const bodies = {invoice:'M18 18H67L80 32V91L68 85L56 91L44 85L32 91L18 85Z',phisher:'M12 32L30 15L65 15L85 35L77 83L25 88L12 70Z',lockjaw:'M12 32Q12 18 28 18H72Q88 18 88 32V85H12Z',leaky:'M20 28Q18 12 50 12Q83 12 80 28L90 82Q50 101 10 82Z'};
  return `<svg class="villain-art" viewBox="0 0 100 110" role="img" aria-label="${names[key]}"><path d="${bodies[key]}" fill="#3b273b" stroke="#ffba72" stroke-width="3"/><path d="M25 38L42 43M75 38L58 43" stroke="#ffd279" stroke-width="5" stroke-linecap="round"/><rect x="27" y="46" width="15" height="10" rx="5" fill="#fff1bd"/><rect x="58" y="46" width="15" height="10" rx="5" fill="#fff1bd"/><path d="M34 70Q50 81 68 66" stroke="#ffba72" fill="none" stroke-width="4" stroke-linecap="round"/>${key==='lockjaw'?'<path d="M35 84V92M50 84V95M65 84V92" stroke="#c4ecff" stroke-width="7"/>':key==='phisher'?'<path d="M80 50Q99 50 92 70L83 66" fill="none" stroke="#ffba72" stroke-width="3"/>':key==='leaky'?'<rect x="64" y="77" width="22" height="21" rx="3" fill="#ffd279"/>':'<path d="M25 25H58M25 30H48" stroke="#ffd279" stroke-width="2"/>'}</svg>`;
}
function teamState() { return state?.teams.find(t => t.id === state.me?.team) || state?.teams[0]; }
function aggregate() {
  const teams = state.teams, total = key => teams.reduce((n,t)=>n+t[key],0)/teams.length;
  return {risk:total('risk'), trust:total('trust'), records:total('records')};
}
function city() {
  const positions = [[205,155],[455,155],[705,155],[205,405],[455,405],[705,405]];
  let buildings = positions.map(([x,y],i) => {
    const statuses = state.teams.map(t=>t.buildings[i]);
    const s = state.phase === 'wave' ? (statuses.includes('frozen')?'frozen':statuses.includes('alert')?'alert':statuses.includes('working')?'working':'restored') : state.phase==='lobby'||state.phase==='briefing'?'safe':'restored';
    const h = [86,118,76,85,104,68][i];
    const label = {safe:'◎ Online',alert:'⚠ Needs help',frozen:'❄ Frozen',working:'⚙ Team responding',restored:'✓ Restored'}[s];
    let windows = '';
    for (let r=0;r<3;r++) for(let c=0;c<3;c++) windows+=`<rect x="${-29+c*21}" y="${-h+23+r*15}" width="10" height="7" rx="1"/>`;
    return `<g class="building ${s}" transform="translate(${x},${y})" tabindex="0" role="button" data-building="${i}" aria-label="${e(state.buildings[i])}: ${e(label)}"><path class="base" d="M-92 19L0 -24L92 19L0 64Z" fill="#112e40" stroke="#2b6373" stroke-width="2"/><path d="M-55 3V${-h}L30 ${-h-30}L71 ${-h-8}V18L-13 49Z" fill="#1b3c55" stroke="#3c657d"/><path d="M-55 ${-h}L-13 ${-h+22}L71 ${-h-8}M-13 ${-h+22}V49" fill="none" stroke="#5f8fa2"/><path d="M-55 ${-h}L30 ${-h-30}L71 ${-h-8}L-13 ${-h+22}Z" fill="#2a536b"/><g class="windows" fill="#4dcbd5">${windows}</g><text x="23" y="${-h-6}" fill="#dffaff" text-anchor="middle" font-size="23" font-weight="bold">${e(content.industry_icons?.[state.industry]?.[i]||'◎')}</text><path d="M8 ${-h+30}L58 ${-h+12}M8 ${-h+48}L58 ${-h+30}M8 ${-h+66}L58 ${-h+48}" stroke="#3e7189" stroke-width="5"/><circle class="signal" cx="30" cy="${-h-35}" r="5"/>${s==='frozen'?`<path d="M-55 ${-h}L-42 ${-h+38}L-30 ${-h+14}L-14 ${-h+54}L0 ${-h+17}L30 ${-h-8}L45 ${-h+18}L60 ${-h-1}" fill="#b5e8ff" opacity=".8"/>`:''}<text class="city-label" x="0" y="83" text-anchor="middle">${e(state.buildings[i])}</text><text class="city-state" x="0" y="103" text-anchor="middle">${e(label)}</text></g>`;
  }).join('');
  return `<svg class="city-art" viewBox="0 0 920 535" aria-label="Northwind HQ, six fictional business buildings"><defs><pattern id="grid" width="40" height="24" patternUnits="userSpaceOnUse"><path d="M40 0H0V24" fill="none" stroke="#1a3c4a" stroke-width=".6"/></pattern></defs><path class="city-ground" d="M30 192L460 10L890 192V390L460 525L30 390Z"/><path d="M30 192L460 10L890 192V390L460 525L30 390Z" fill="url(#grid)"/><path d="M90 280H825M330 80V465M580 80V465" stroke="#19364a" stroke-width="16"/><path d="M90 280H825M330 80V465M580 80V465" stroke="#3c6578" stroke-width="1.5" stroke-dasharray="8 10"/>${buildings}<g fill="#40e6ed"><circle cx="330" cy="280" r="5"/><circle cx="580" cy="280" r="5"/></g><text x="460" y="529" text-anchor="middle" fill="#72a8bc" font-size="11" letter-spacing="6">LOCAL INTELLIGENCE · HUMAN DECISIONS</text></svg>`;
}
function leader() {
  const sorted = [...state.teams].sort((a,b)=>b.score-a.score||a.risk-b.risk);
  return `<div class="eyebrow">Team leaderboard</div><ol>${sorted.map((t,i)=>`<li><span class="rank">${String(i+1).padStart(2,'0')}</span><span class="team-name">${e(t.name)} ${t.autopilot?'◈':''}</span><b>${t.score.toLocaleString()}</b></li>`).join('')}</ol><small>◈ Autopilot team · points from choices + timing</small>`;
}
function awards() {
  const fastest = [...state.teams].sort((a,b)=>Object.values(a.times).reduce((s,x)=>s+x,0)-Object.values(b.times).reduce((s,x)=>s+x,0))[0];
  const revenue = [...state.teams].sort((a,b)=>a.risk-b.risk)[0];
  const trust = [...state.teams].sort((a,b)=>b.trust-a.trust)[0];
  const usage = Object.keys(content.robots).map(r=>[r,state.teams.reduce((s,t)=>s+t.robot_uses[r],0)]).sort((a,b)=>b[1]-a[1]);
  return `<div class="awards">${[['Fastest Containment',fastest.name],['Most Revenue Saved',revenue.name],['Trust Keeper',trust.name],['MVP Robot',usage[0][0]]].map(([a,b])=>`<div class="award"><span>${a}</span><b>${e(b)}</b></div>`).join('')}</div>`;
}
function screenShell() {
  app.innerHTML = `<main class="screen" id="screen"><header class="row between">${brand}<div id="screen-heading"></div><div class="row"><span id="connection" class="connection">Connecting</span><button data-mute class="quiet" aria-label="Mute sound">♪ Sound off</button><div><div class="eyebrow">Join the defense</div><div class="room-code">${e(roomCode)}</div></div></div></header><section class="meters" id="meters" aria-label="Business meters"></section><section class="arena"><div class="panel city-panel"><div class="city-title" id="city-title"></div><div id="city" style="display:contents"></div><div class="city-key"><span>◎ Online</span><span>⚠ Needs help</span><span>❄ Frozen</span><span>✓ Restored</span></div><div id="overlay"></div></div><aside class="side"><div class="panel mission" id="mission"></div><div class="panel leaderboard" id="leaderboard"></div></aside></section><section class="robot-squad" id="squad" aria-label="Local AI robot squad"></section><section class="power" id="power" aria-label="Measured Fury power"></section><footer><span>Fictional scenario · Game values · HP ZGX Fury helps your security team run AI locally. People decide and act.</span><span>Private game AI transport · Sensitive evidence stays on the local inference path.</span></footer></main>`;
}
function renderScreen() {
  if (!$('#screen')) screenShell();
  const a = aggregate(), wave = state.wave_info;
  $('#screen').className = `screen ${state.phase==='wave'?'attack':''}`;
  html('screen-heading',`<div class="banner"><i class="beacon"></i> ${state.paused?'PAUSED':state.phase==='wave'?'ALERT ALERT':state.phase==='translate'?'✓ THREAT CONTAINED':state.phase==='debrief'?'MISSION COMPLETE':'DEFEND NORTHWIND'}</div><div class="notice">${e(state.notice)} ${state.rehearsal?' · ACCELERATED REHEARSAL':''}</div>`);
  html('meters', [['Revenue at Risk',money(a.risk),'Game value · room average · $12,000/min at full downtime','↗'],['Customer Trust',Math.round(a.trust)+' / 100','Game meter · room average','♡'],['Records Exposed',Math.floor(a.records).toLocaleString(),'Fictional records · room average','▧'],['Time to Contain',clock(state.elapsed),state.phase==='wave'?`${clock(state.remaining)} remaining this wave`:'Stopwatch for the current wave','◷']].map(([label,value,sub,icon],i)=>`<div class="panel meter"><div><div class="eyebrow">${label}</div><div class="number ${i===1?'cyan':''}">${value}</div><small>${e(sub)}</small>${i===1?`<div class="bar"><i style="width:${a.trust}%"></i></div>`:''}</div><div class="meter-icon">${icon}</div></div>`).join(''));
  html('city-title',`<div><div class="eyebrow">${e(industryLabel(state.industry))} · fictional customer</div><h2>NORTHWIND <span class="muted">/ HQ</span></h2></div><span class="tag">${state.phase==='wave'?'⚠ BUSINESS UNDER PRESSURE':'◎ LOCAL AI · TEAM RESPONSE'}</span>`);
  html('city',city());
  let overlay = ['lobby','briefing'].includes(state.phase) ? `<div class="city-join"><img class="qr" src="/qr?room=${e(roomCode)}" alt="Scan to join the private game"><div class="eyebrow" style="margin-top:12px">Scan to join</div><b>${e(roomCode)}</b><p>${state.players.length} sellers ready</p></div>` : '';
  if (state.phase === 'translate') overlay = `<div class="translate"><div class="eyebrow">Wave ${state.wave} complete · Translate it</div><h2>Make the value clear.</h2>${wave.translate.map((x,i)=>`<p class="${i===2?'quote':''}">${e(x)}</p>`).join('')}</div>`;
  if (state.phase === 'debrief') overlay = `<div class="translate debrief"><div class="debrief-main"><div class="eyebrow">Mission complete</div><h2>Your team. Your value story.</h2><p>The team made the decisions. Local AI helped it understand the evidence and respond faster.</p>${awards()}<p class="quote">“What sensitive work could your people do faster with AI running locally?”</p></div><div class="debrief-join"><img class="qr" src="/qr?kind=playbook&amp;room=${e(roomCode)}" alt="Scan to download your team Seller Playbook"><p>Scan for your<br>Seller Playbook.</p></div></div>`;
  html('overlay',overlay);
  if (['lobby','briefing'].includes(state.phase)) html('mission',`<div class="eyebrow">${state.phase==='lobby'?'Ready the squad':'Your mission'}</div><h2>Keep Northwind open.</h2><p>Protect revenue, trust and uptime. Your team makes the calls. Local AI helps.</p><p style="margin-top:18px;color:var(--cyan)"><b>${state.players.length} sellers joined</b></p>`);
  else if (state.phase==='debrief') html('mission',`<div class="eyebrow">Seller takeaway</div><h2>Bring the story with you.</h2><p>Fury is a platform for local AI, not a security product. Explore where faster analysis and sensitive data meet.</p><p style="margin-top:18px">Scan the city QR to download your team’s one page Seller Playbook.</p>`);
  else html('mission',`<div class="eyebrow">Wave ${state.wave} / 3</div><div class="villain-row"><div class="villain-pair">${villain(wave.villain)}${state.wave===3?villain('leaky'):''}</div><div><div class="villain-name">${e(content.villains[wave.villain][0])}${state.wave===3?' + LEAKY':''}</div><small>${e(content.villains[wave.villain][1])}</small></div></div><h2>${e(wave.name)}</h2><p>${e(wave.goal)}</p>`);
  html('leaderboard',leader());
  html('squad',Object.keys(content.robots).map(name=>{
    const b=state.bubbles[name],status=b?.status||'idle';
    return `<article class="panel robot-card ${status}" style="--robot:${content.robots[name][2]}"><div class="robot-top">${robot(name,status)}<div><div class="status">${status==='working'?'● Analyzing locally':status==='success'?'✓ Analysis ready':status==='alert'?'◇ Team guidance':'◎ Ready'}</div><h3>${name}</h3><div class="job">${e(content.robots[name][1])}</div></div></div><div class="bubble">${e(b?.text||content.robots[name][1])}</div></article>`;
  }).join(''));
  const p = state.power;
  html('power',`<span class="eyebrow">Fury power / live</span><span><strong>${p.active}</strong> agents working · peak ${p.peak}</span><span><strong>${p.tps.toFixed(1)}</strong> tokens/s <small>¹</small></span><span><strong>${p.evidence.toLocaleString()}</strong> evidence items sent for analysis <small>²</small></span><span>Data sent to the cloud: <strong>${p.cloud_bytes} B</strong> <small>³</small></span><span class="scope">¹ Reported tokens / call seconds, last 10s. ² Includes repeated role analysis. ³ Game AI payload counter only. Device traffic and model startup downloads excluded.</span>`);
}
function playerShell() {
  app.innerHTML = `<main class="controller"><header class="row between">${brand}<span id="connection" class="connection">Connecting</span></header><div id="player-title"></div><section class="mini-meters" id="mini-meters"></section><section id="player-mission"></section><div id="player-actions"></div><div class="result-line" id="action-result" role="status"></div><section id="player-bubble"></section><p class="intro-note">Northwind is fictional. All dollar amounts are game values. Local AI assists your team; people choose and act.</p></main>`;
}
function renderPlayer() {
  if (!state.me) return;
  if (!$('#player-title')) playerShell();
  const t = teamState(), wave = state.wave_info;
  html('player-title',`<div class="eyebrow">${e(t.name)} ${t.autopilot?'· ◈ Autopilot':''} ${isStation?'· TABLE STATION':''}</div><h1 style="margin-top:8px">${state.phase==='lobby'?'Ready to defend?':state.phase==='debrief'?'Mission complete.':state.phase==='briefing'?'Meet the squad.':e(wave.name)}</h1><p class="resume-note">Room ${e(roomCode)} · ${e(state.me.name)} · ${state.rehearsal?'Accelerated rehearsal':'Your team’s choices are saved'}</p>`);
  html('mini-meters',`<div class="panel"><small>Revenue at Risk · Game value</small><b>${money(t.risk)}</b></div><div class="panel"><small>Customer Trust</small><b>${Math.round(t.trust)} / 100</b></div><div class="panel"><small>Records Exposed · Fictional</small><b>${Math.floor(t.records)}</b></div><div class="panel"><small>Time to Contain</small><b>${clock(state.elapsed)}</b></div>`);
  let mission='', actions='';
  if (state.paused) mission='<div class="panel brief"><div class="eyebrow">Paused by facilitator</div><h2>Take a breath.</h2><p>Your progress is saved. The game clock is paused.</p></div>';
  else if (state.phase==='lobby') mission='<div class="panel brief"><div class="eyebrow">Your mission</div><h2>Keep Northwind open.</h2><p>You protect a fictional customer’s business. Choose actions together. Local AI helps you understand the evidence.</p><p style="margin-top:12px">Waiting for the facilitator to start.</p></div>';
  else if (state.phase==='briefing') mission=`<div class="panel brief"><div class="eyebrow">Three waves · one business</div><h2>You make the calls.</h2><p>Check a payment. Sort an inbox storm. Restore frozen systems.</p></div><div class="stack">${Object.keys(content.robots).map(n=>`<div class="panel row" style="padding:12px">${robot(n)}<div><b>${n}</b><p>${e(content.robots[n][1])}</p></div></div>`).join('')}</div>`;
  else if (state.phase==='translate') mission=`<div class="panel translate-card"><div class="eyebrow">Wave ${state.wave} complete · Translate it</div><h2>Tell the value story.</h2>${wave.translate.map(x=>`<p>${e(x)}</p>`).join('')}</div>`;
  else if (state.phase==='debrief') {
    mission=`<div class="panel brief"><div class="eyebrow">Your team’s results</div><h2>${t.score.toLocaleString()} points</h2><p>${t.fast} Fast Response bonuses · ${Object.values(t.times).reduce((s,n)=>s+n,0).toFixed(1)} seconds across the waves.</p><p style="margin-top:12px">Revenue protected versus full wave downtime: <b>${money(Math.max(0,120000-t.risk))}</b>. Game value, using ten minutes at $12,000 per minute.</p>${awards()}<p style="margin-top:20px">“Your team could use local AI to understand sensitive evidence and respond faster.”</p><a class="button primary" href="/api/rooms/${e(roomCode)}/playbook.pdf?team=${e(t.id)}" style="margin-top:18px">Download Seller Playbook PDF ↓</a></div><div class="panel leaderboard">${leader()}</div>`;
  } else if (t.completed) mission='<div class="panel brief"><div class="eyebrow">✓ Wave contained</div><h2>Your business is recovering.</h2><p>Your team finished this wave. Think about how you would explain the value to a customer.</p></div>';
  else if (state.phase==='wave') {
    mission=`<div class="panel brief"><div class="eyebrow">⚠ Wave ${state.wave} / 3 · ${clock(state.remaining)} remaining</div><h2>${e(wave.goal)}</h2><p>★ Right action in the first 10 seconds: +25 points.</p></div>`;
    if(state.wave===1) actions=`<div class="panel brief"><small>Fictional invoice INV-104</small><p><b>$48,000 due in 15 minutes.</b> Sender and reply address differ. New bank details. “Do not call the usual contact.”</p></div><div class="actions">${[['analyze','⌕','Ask SHERLOCK to check it','AI flags warning signs. +100 points. After both checks: downtime risk stops; Trust +4, capped at 100.'],['verify','☎','Call the vendor to verify','Use a trusted number. +100 points. After both checks: downtime risk stops; Trust +4, capped at 100.'],['pay','$','Pay it now','Game value: +$48,000 at risk. Customer Trust −8.']].map(([a,icon,title,effect])=>`<button class="action-card" data-action="${a}" ${t.progress.includes(a)?'disabled':''}><span class="symbol">${icon}</span><span><strong>${title}${t.progress.includes(a)?' ✓':''}</strong><small>${e(effect)}</small></span></button>`).join('')}</div>`;
    else {
      if(state.wave===2) selectedRobot='SCOUT';
      const expected = Object.keys(content.robots)[t.progress.length];
      actions=`${state.wave===3?`<p class="muted">Next: <b>${e(expected)}</b> · +100 points for the right role. Wrong order: guidance, no penalty.</p><div class="robot-picks">${Object.keys(content.robots).map(n=>`<button data-robot="${n}" draggable="true" class="${selectedRobot===n?'selected':''}">${robot(n)}${n}</button>`).join('')}</div><small>Tap a robot, then a building. You can also drag a robot.</small><div class="panel effect-preview" role="note"><b>Meter effect before you deploy</b><p>${e(({SCOUT:'No immediate meter change. Find the problem so the team can respond.',SHERLOCK:'No immediate meter change. Explain the evidence before isolation.',SHIELD:'Stops new records exposure. Downtime risk continues until restoration.',PATCH:'Restores all buildings. Stops new downtime risk and trust loss.',SCRIBE:'Completes the response. Trust +4, capped at 100. Existing losses remain.'})[selectedRobot])}</p></div>`:'<div class="row" style="margin:12px 0">'+robot('SCOUT')+'<p>200 fictional emails. 12 fakes. +100 points per building. Meter effect: each scan stops new downtime and record loss at that building. All six safe: Trust +4, capped at 100.</p></div>'}<div class="building-buttons" style="margin-top:14px">${state.buildings.map((n,i)=>`<button data-deploy="${i}" ${state.wave===2&&t.progress.includes(i)?'disabled':''}><span>${e(n)}</span><small>${state.wave===2&&t.progress.includes(i)?'✓ Quarantined':`${e(selectedRobot)} → deploy`}</small></button>`).join('')}</div>`;
    }
  }
  html('player-mission',mission);
  html('player-actions',actions);
  html('action-result',e(t.last_action));
  const bubble = state.bubbles[selectedRobot] || Object.values(state.bubbles).at(-1);
  html('player-bubble',bubble?`<div class="panel bubble"><div class="eyebrow">${e(bubble.robot)} · ${bubble.status==='working'?'Analyzing locally':'Team guidance'}</div><p style="margin-top:8px">${e(bubble.text)}</p></div>`:'');
}
function adminShell() {
  app.innerHTML=`<main class="admin"><header class="row between">${brand}<div class="row"><a href="/stations" id="stations-link">Station setup</a><button data-logout class="quiet">Sign out</button></div></header><div class="two-col"><section class="panel control-panel"><div class="eyebrow">Facilitator console</div><h1 style="font-size:38px;margin:12px 0">Run the room.</h1><div id="room-select"></div><form id="create-form"><div class="admin-form"><div><label for="industry">Customer industry</label><select id="industry" name="industry">${Object.keys(content.industries).map(i=>`<option value="${i}">${i[0].toUpperCase()+i.slice(1).replaceAll('_',' ')}</option>`).join('')}</select></div><div><label for="teams">Teams</label><select id="teams" name="teams">${Array.from({length:8},(_,i)=>`<option ${i===7?'selected':''}>${i+1}</option>`).join('')}</select></div></div><button class="primary" style="margin-top:16px">Open new room</button></form><p class="resume-note">Choose the industry before the session. Password and room state are stored locally.</p></section><section class="panel control-panel" id="show-controls"><h2>Open a room to begin.</h2></section></div><section id="admin-live"></section></main>`;
}
async function initAdmin() {
  try {
    const data=await api('/api/admin'); admin=true;
    adminShell();
    html('room-select',data.rooms.length?`<label for="existing-room">Existing room</label><div class="row"><select id="existing-room">${data.rooms.map(r=>`<option value="${e(r.code)}" ${r.code===roomCode?'selected':''}>${e(r.code)} · ${e(r.phase)}</option>`).join('')}</select><button data-open-room>Open</button></div>`:'');
    if(roomCode) connect();
  } catch {
    app.innerHTML=`<main class="admin"><header>${brand}</header><form class="panel login-box" id="login-form"><div class="eyebrow">Facilitator access</div><h2 style="margin-top:12px">Welcome, host.</h2><p class="muted" style="margin-top:12px">Use the local password created on first launch.</p><label for="password">Password</label><input type="password" id="password" name="password" autocomplete="current-password" required maxlength="200"><button class="primary">Open controls</button><p class="resume-note">On the Fury: ./siege status shows the local password file location.</p></form></main>`;
  }
}
function renderAdmin() {
  if(!$('#show-controls')) return;
  $('#stations-link').href='/stations?room='+e(roomCode);
  html('show-controls',`<div class="row between"><div><div class="eyebrow">Room ${e(roomCode)}</div><h2 style="margin-top:8px">${e(state.phase)} ${state.wave?'· Wave '+state.wave:''}</h2></div><span id="connection" class="connection">Connected</span></div><p style="margin:14px 0;color:var(--amber)">${e(state.notice)} · ${clock(state.remaining)} ${state.paused?'PAUSED':''}</p><div class="controls"><button class="primary" data-control="start">Start</button><button data-control="pause">${state.paused?'Resume':'Pause'}</button><button data-control="next">Next</button><button data-control="skip">Skip</button><button data-control="replay">Replay wave</button><button class="danger" data-control="reset">Reset room</button></div><div class="controls" style="margin-top:14px"><button data-control="autopilot_all" data-value="true">Autopilot all ON</button><button data-control="autopilot_all" data-value="false">Autopilot all OFF</button><button data-control="intensity" data-value="${state.intensity==='reduced'?'standard':'reduced'}">Intensity: ${e(state.intensity)}</button><button data-control="sound" data-value="${!state.sound}">Sound: ${state.sound?'on':'off'}</button></div><div class="row" style="margin-top:18px"><a class="button" href="/screen?room=${e(roomCode)}" target="_blank">Open big screen ↗</a><a href="/play?room=${e(roomCode)}">Player link</a></div><p class="resume-note">${state.players.length} devices · ${state.power.active} real model calls working · ${state.fallback_count||0} scripted fallbacks${state.rehearsal?' · ACCELERATED REHEARSAL':''}</p>`);
  html('admin-live',`<div class="two-col" style="margin-top:20px"><div class="panel control-panel"><div class="eyebrow">Team rescue</div><div class="teams">${state.teams.map(t=>`<div class="team-control"><b>${e(t.name)}</b><p><small>${t.score} points · ${t.completed?'✓ Contained':t.progress.length+' actions'}</small></p><button data-team="${t.id}" data-auto="${!t.autopilot}">${t.autopilot?'◈ Autopilot ON':'Autopilot OFF'}</button></div>`).join('')}</div></div><div class="panel control-panel"><div class="eyebrow">Live AI and fallback log</div><div class="agent-log">${Object.values(state.bubbles).map(b=>`<p><b>${e(b.robot)}</b> · ${b.scripted?'◇ SCRIPTED':e(b.status)}<br>${e(b.text)}</p>`).join('')||'<p>Agents start in the briefing.</p>'}</div></div></div><div class="panel control-panel" style="margin-top:20px"><div class="eyebrow">Nickname moderation · tap to hide</div><div class="names" style="margin-top:12px">${state.players.map(p=>`<button data-hide="${e(p.id)}">${p.connected?'●':'○'} ${e(p.name)} · T${e(p.team)}</button>`).join('')}</div></div>`);
}
function applyState(next) {
  const previous=state;
  state=next;
  document.body.className = `${state.intensity==='reduced'||reduced.matches?'reduced':'standard'} ${isStation?'kiosk':''}`;
  if(path==='/screen') renderScreen();
  else if(path==='/facilitator') renderAdmin();
  else if(path==='/play'||isStation) renderPlayer();
  if(path==='/screen') soundForState(previous);
}
function connection(online) { const el=$('#connection'); if(el){el.textContent=online?'● Connected':'○ Reconnecting · progress saved';el.dataset.online=online;} }
function connect() {
  if(!roomCode) return;
  if(socket) {socket.onclose=null; socket.close();}
  clearTimeout(reconnectTimer);
  socket=new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/ws/${encodeURIComponent(roomCode)}`);
  socket.onopen=()=>{socket.send(JSON.stringify({type:'hello',...(saved?.token?{token:saved.token}:{})}));connection(true);};
  socket.onmessage=event=>{
    const packet=JSON.parse(event.data);
    if(packet.state){applyState(packet.state);connection(true);}
    if(packet.type==='notice')toast(packet.text);
  };
  socket.onclose=event=>{
    connection(false);
    if(event.code===1008 && saved?.token){toast('Please rejoin the room with a fresh link.');return;}
    reconnectTimer=setTimeout(connect,1000);
  };
  socket.onerror=()=>connection(false);
}
async function joinForm() {
  if(!roomCode) {
    app.innerHTML=`<main class="controller"><header>${brand}</header><form id="code-form" class="panel join-box"><div class="eyebrow">Join your squad</div><h2 style="margin-top:12px">Enter the room code.</h2><label for="code">Six character code</label><input id="code" name="code" required maxlength="6" minlength="6" autocomplete="off" autocapitalize="characters"><button class="primary">Continue</button></form></main>`;
    return;
  }
  const snapshot=await api('/api/rooms/'+roomCode);
  if(saved?.token||isStation){await doJoin(isStation?'Table station':'Seller',isStation?q.get('team'):null);return;}
  app.innerHTML=`<main class="controller"><header>${brand}</header><form id="join-form" class="panel join-box"><div class="eyebrow">Room ${e(roomCode)}</div><h2 style="margin-top:12px">Pick your squad.</h2><label for="nickname">Nickname</label><input id="nickname" name="nickname" required maxlength="24" autocomplete="off" value="Seller"><label for="team">Team</label><select id="team" name="team"><option value="">Assign me a team</option>${snapshot.teams.map(t=>`<option value="${t.id}">${e(t.name)}</option>`).join('')}</select><button class="primary">Join the defense</button><p class="resume-note">Only a nickname is saved. Your browser remembers this room.</p></form></main>`;
}
async function doJoin(name,team) {
  const result=await api('/api/join',{code:roomCode,name,team:team||null,token:saved?.token||null,station:isStation?q.get('station'):null});
  saved={token:result.token};
  try{localStorage.setItem(`siege:${roomCode}:${isStation?q.get('team'):'player'}`,JSON.stringify(saved));}catch{}
  applyState(result.state); connect();
}
async function stations() {
  if(!roomCode) {
    const data=await api('/api/admin');
    app.innerHTML=`<main class="station-setup"><header class="row between">${brand}<a href="/facilitator">Console</a></header><h1>Prepare the tables.</h1><p style="margin:20px 0">Choose a room to create fixed-team station links.</p><div class="stack">${data.rooms.map(r=>`<a class="button" href="/stations?room=${e(r.code)}">${e(r.code)}</a>`).join('')}</div></main>`;
    return;
  }
  const links=await api(`/api/rooms/${roomCode}/stations`);
  app.innerHTML=`<main class="station-setup"><header class="row between">${brand}<a href="/facilitator?room=${e(roomCode)}">Console</a></header><div class="eyebrow">Room ${e(roomCode)}</div><h1 style="margin-top:12px">Tables ready. Teams ready.</h1><p style="margin-top:20px;color:var(--muted)">Open each link on its table laptop. It joins automatically. Use browser fullscreen for kiosk mode.</p><button data-print style="margin-top:16px">Print station QR cards</button><div class="stations-grid">${links.map(x=>`<article class="panel station-card"><h2>Team ${e(x.team.padStart(2,'0'))}</h2><img class="qr" src="${e(x.qr)}" alt="Fixed Team ${e(x.team)} station QR"><a href="${e(x.url)}">${e(x.url)}</a></article>`).join('')}</div></main>`;
}
app.addEventListener('submit',async event=>{
  event.preventDefault(); const form=event.target;
  try {
    if(form.id==='login-form'){await api('/api/login',{password:form.password.value});await initAdmin();}
    if(form.id==='create-form'){const r=await api('/api/rooms',{industry:form.industry.value,teams:Number(form.teams.value)});roomCode=r.code;history.replaceState(null,'','/facilitator?room='+roomCode);applyState(r);connect();}
    if(form.id==='code-form'){location.href='/play?room='+encodeURIComponent(form.code.value.toUpperCase());}
    if(form.id==='join-form'){await doJoin(form.nickname.value,form.team.value);}
  }catch(error){toast(error.message);}
});
app.addEventListener('click',async event=>{
  const button=event.target.closest('button');if(!button)return;
  try {
    if(button.hasAttribute('data-open-room')){roomCode=$('#existing-room').value;history.replaceState(null,'','/facilitator?room='+roomCode);connect();}
    if(button.hasAttribute('data-logout')){await api('/api/logout',{});socket?.close();location.href='/facilitator';}
    if(button.hasAttribute('data-control')){
      const command=button.dataset.control;
      if(command==='reset'&&!confirm('Reset this room for a new group? Team results will clear.'))return;
      let value=button.dataset.value;
      if(value==='true'||value==='false')value=value==='true';
      applyState(await api(`/api/rooms/${roomCode}/control`,{command,value:value??null}));
    }
    if(button.hasAttribute('data-auto'))applyState(await api(`/api/rooms/${roomCode}/control`,{command:'autopilot',value:{team:button.dataset.team,enabled:button.dataset.auto==='true'}}));
    if(button.hasAttribute('data-hide'))await api(`/api/rooms/${roomCode}/control`,{command:'hide',value:button.dataset.hide});
    if(button.hasAttribute('data-robot')){selectedRobot=button.dataset.robot;renderPlayer();}
    if(button.hasAttribute('data-action'))sendAction(button.dataset.action);
    if(button.hasAttribute('data-deploy'))sendAction(selectedRobot,Number(button.dataset.deploy));
    if(button.hasAttribute('data-print'))window.print();
    if(button.hasAttribute('data-mute')){await toggleSound();}
  }catch(error){toast(error.message);}
});
function sendAction(action,building) {
  if(!socket||socket.readyState!==WebSocket.OPEN){toast('Reconnecting. Your team progress is saved.');return;}
  socket.send(JSON.stringify({type:'action',action,...(building===undefined?{}:{building})}));
}
app.addEventListener('dragstart',event=>{const b=event.target.closest('[data-robot]');if(b)event.dataTransfer.setData('text/plain',b.dataset.robot);});
app.addEventListener('dragover',event=>{if(event.target.closest('[data-deploy]'))event.preventDefault();});
app.addEventListener('drop',event=>{const b=event.target.closest('[data-deploy]');if(b){event.preventDefault();const r=event.dataTransfer.getData('text/plain');if(content.robots[r])sendAction(r,Number(b.dataset.deploy));}});
let audioContext=null, localMuted=true;
function tone(frequency,duration=.15,type='sine',delay=0,endFrequency=null){
  if(path!=='/screen'||localMuted||!state?.sound||audioContext?.state!=='running')return;
  const at=audioContext.currentTime+delay,osc=audioContext.createOscillator(),gain=audioContext.createGain();
  osc.type=type;osc.frequency.setValueAtTime(frequency,at);
  if(endFrequency)osc.frequency.exponentialRampToValueAtTime(endFrequency,at+duration);
  gain.gain.setValueAtTime(0,at);gain.gain.linearRampToValueAtTime(.025,at+.025);gain.gain.exponentialRampToValueAtTime(.0001,at+duration);
  osc.connect(gain);gain.connect(audioContext.destination);osc.start(at);osc.stop(at+duration+.03);
}
function soundLabel(){
  const b=$('[data-mute]');if(b)b.textContent=localMuted?'♪ Sound off':state?.sound?'♪ Sound on':'♪ Ready · host muted';
}
async function toggleSound(){
  if(path!=='/screen')return;
  audioContext=audioContext||new(window.AudioContext||window.webkitAudioContext)();
  await audioContext.resume();localMuted=!localMuted;soundLabel();
  if(!localMuted){if(state.sound)tone(660,.15);else toast('Audio ready. Enable sound in the facilitator console when needed.');}
}
function soundForState(previous){
  soundLabel();
  if(!previous)return;
  if(state.phase==='wave'&&(previous.phase!=='wave'||previous.wave!==state.wave)){
    tone(180,1,'sine',0,420);tone(260,.6,'sine',.5,160);
  }
  if(state.phase==='translate'&&previous.phase!=='translate'){
    [261.63,329.63,392].forEach((n,i)=>tone(n,.65,'sine',i*.08));
  }
  for(const [name,b]of Object.entries(state.bubbles))if(b.status==='success'&&previous.bubbles[name]?.status==='working')tone(720,.08,'sine',0,950);
}
async function main(){
  content=await api('/api/content');
  if(path==='/facilitator')return initAdmin();
  if(path==='/stations')return stations();
  if(path==='/play'||isStation)return joinForm();
  if(path==='/screen'){
    if(!roomCode){app.innerHTML=`<main class="welcome"><header>${brand}</header><h1>Open a room first.</h1><p style="margin-top:20px"><a class="button primary" href="/facilitator">Facilitator console</a></p></main>`;return;}
    screenShell();applyState(await api('/api/rooms/'+roomCode));connect();return;
  }
  app.innerHTML=`<main class="welcome"><header class="row between">${brand}<span class="tag">PRIVATE TEAM EXPERIENCE</span></header><section class="panel hero"><div><div class="eyebrow">Northwind needs your team.</div><h1>Keep the<br>business<br><span style="color:var(--cyan)">moving.</span></h1><p>A living city. Three attacks. Five friendly robots powered by local AI on an HP ZGX Fury.</p><a class="button primary" href="/play">Join the defense →</a><a class="button quiet" href="/facilitator">Run a session</a></div><div class="art">${Object.keys(content.robots).map(n=>`<div style="text-align:center">${robot(n)}<div class="eyebrow">${n}</div></div>`).join('')}<p style="width:100%;text-align:center;font-size:15px">Your team makes the calls.<br>The squad helps you make them faster.</p></div></section><p class="intro-note">A fictional business simulation. Local AI helps a security team spot, explain and contain problems faster. Fury is not a security product.</p></main>`;
}
main().catch(error=>{app.innerHTML=`<main class="welcome"><header>${brand}</header><div class="panel" style="padding:30px"><h2>Let’s get you connected.</h2><p style="margin-top:18px">${e(error.message)}</p><a class="button" href="/facilitator" style="margin-top:18px">Open facilitator console</a><a class="button" href="/play" style="margin-top:18px">Join a room</a></div></main>`;});
// Original Canvas particles, no third-party animation libraries, images, fonts or CDNs.
const canvas=$('#particles'),ctx=canvas.getContext('2d');
let points=Array.from({length:35},()=>({x:Math.random(),y:Math.random(),v:.00003+Math.random()*.00004}));
const envelope=document.createElement('canvas');envelope.width=18;envelope.height=13;const envelopeContext=envelope.getContext('2d');envelopeContext.strokeStyle='#ffd279';envelopeContext.strokeRect(1,1,16,11);envelopeContext.beginPath();envelopeContext.moveTo(1,1);envelopeContext.lineTo(9,7);envelopeContext.lineTo(17,1);envelopeContext.stroke();
let lastFrame=0;
function animate(t){
  requestAnimationFrame(animate);
  if(reduced.matches||state?.intensity==='reduced'||document.hidden)return;
  if(t-lastFrame<16)return;lastFrame=t;
  if(canvas.width!==innerWidth||canvas.height!==innerHeight){canvas.width=innerWidth;canvas.height=innerHeight;}
  ctx.clearRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#40e6ed';
  for(const p of points){p.y=(p.y-p.v*(state?.wave===2?4:1)+1)%1;const x=p.x*canvas.width,y=p.y*canvas.height;if(state?.phase==='wave'&&state.wave===2){ctx.drawImage(envelope,x,y);}else ctx.fillRect(x,y,2,2);}
}
requestAnimationFrame(animate);
