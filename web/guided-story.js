const e=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const roles=['SCOUT','SHERLOCK','SHIELD','PATCH','SCRIBE'];
const tasks=['Scan the local evidence','Identify the issue','Isolate the demo threat','Apply the demo recovery plan','Notify a human reviewer'];
const cloudArt=()=>`<svg viewBox="0 0 110 82" class="cloud-bot" aria-label="Illustrated cloud AI assistant" role="img"><path d="M20 53Q3 53 6 35Q8 23 23 23Q27 5 47 8Q64 0 77 19Q98 14 101 35Q112 54 91 56Z" fill="#26384b" stroke="#a7b9ca" stroke-width="2"/><rect x="32" y="25" width="45" height="29" rx="9" fill="#071321" stroke="#becddb" stroke-width="2"/><circle cx="44" cy="38" r="4" fill="#ccdee9"/><circle cx="64" cy="38" r="4" fill="#ccdee9"/><path d="M44 48H64" stroke="#ccdee9" stroke-width="2"/><rect x="76" y="48" width="24" height="21" rx="4" fill="#644727" stroke="#ffd279" stroke-width="2"/><path d="M82 48V43Q88 32 94 43V48" fill="none" stroke="#ffd279" stroke-width="3"/></svg>`;

export function guidedDecision(state,content,robot,villain){
 const s=state.story,t=state.teams[0],w=state.wave_info;
 const head=`<div class="row between"><div class="eyebrow">Guided incident ${state.wave} / 3</div><span class="tag">${s.running?'◉ SQUAD DEPLOYED':'⚠ ATTACK DETECTED'}</span></div><h1>${e(s.title)}</h1><div class="story-threat">${villain(w.villain)}<p>${e(s.attack)}</p>${state.wave===3?`<div class="leaky-partner">${villain('leaky')}<small>+ LEAKY</small></div>`:''}</div>`;
 if(state.paused)return head+`<div class="resume-bar"><b>Your story is paused.</b><p>The city, runbook and your progress are held.</p><button data-command="pause">Resume my experience →</button></div>`;
 if(!s.running&&s.cursor===0){
 const checking=s.stage==='cloud_check',beat=Math.min(2,Math.floor((s.cloud_elapsed||0)/1.6));
 return head+`<section class="cloud-gate ${checking?'request-checking':'request-denied'}"><div class="cloud-gate-top">${cloudArt()}<div><small>1 · CLOUD FRONTIER REQUEST CHECK</small><h2>${checking?'Checking the request…':'DENIED · Scenario policy'}</h2></div></div><p class="policy-caption">${e(s.cloud.label)}. No cloud model was called.</p>${evidenceConsole(state,'cloud')}<ol class="request-checks">${['Read the requested task','Check sensitive-evidence permission','Check automated-action permission'].map((x,i)=>`<li><span>${!checking||i<beat?'✓':i===beat?'◉':'○'}</span>${x}</li>`).join('')}</ol>${checking?'<p class="cloud-speech">Scripted preflight running locally. No evidence is uploaded.</p>':`<p class="cloud-speech">“${e(s.cloud.bubble)}”</p><div class="policy-bar">▣ Customer policy: keep incident evidence local. This selected external route cannot run this workflow.</div>`}</section>${checking?'<div class="local-deploy-ready"><span class="fury-chip">FURY</span><p>The local squad is standing by while the scenario check completes.</p></div>':`<div class="local-deploy-ready"><span class="fury-chip">FURY</span><p><b>2 · Deploy inside the approved boundary.</b><br>Your local model can use the evidence here. Scoped tools and human approval govern the response.</p></div><button class="primary" data-command="deploy">Deploy local AI squad →</button><p class="sub-note">One click. Five roles. Live local analysis. City-only recovery.</p><div class="capacity-case"><b>Critical work needs a capacity plan.</b><p>Evaluate dedicated local inference when external approvals, quotas or connectivity constrain a workflow. Plan power, resilience and operational support too.</p></div>`}${comparisonNotes(content)}`;
 }
 const anyFallback=Object.values(state.bubbles).some(b=>b.status==='alert');
 return head+`<div class="deployment-status"><i class="deployment-dot"></i><div><strong>The squad is on it.</strong><small>${anyFallback?'Continuity guidance keeps the demonstration running.':'Scan → identify → contain → recover → human review. Local analysis; city-only actions.'}</small></div></div>${evidenceConsole(state,'local')}<ol class="agent-runbook">${roles.map((name,i)=>{
 const done=i<s.cursor,active=i===s.cursor,model=state.bubbles[name];
 return `<li class="${done?'step-done':active?'step-active':'step-queued'}"><span class="runbook-state">${done?'✓':active?'›':i+1}</span><div class="runbook-avatar">${robot(name,model?.status||'idle')}</div><div><b>${name}</b><p>${tasks[i]}</p><small>${done?'Completed in the demo':active?'Demonstration step in progress':'Queued automatically'}${model?.status==='working'?' · AI analyzing':model?.status==='success'?' · analysis ready':''}</small>${done?`<p class="step-result">${e(s.events?.[i]?.title||'Demo step completed.')}</p>`:''}${active&&model?.text?`<div class="role-finding"><span>${model.status==='alert'?'Continuity guidance':model.status==='working'?'Streaming local analysis':model.shared?'Shared local analysis':'Live local analysis'}</span><p>“${e(model.text)}”</p></div>`:''}</div></li>`;
 }).join('')}</ol><p class="runbook-scope">▣ Simulation scope: Northwind city only. Production changes require authorized tools and approvals.</p><button class="quiet" data-command="pause">Pause my experience</button>${comparisonNotes(content)}`;
}

export function evidenceConsole(state,route){
 const s=state.story,local=route==='local';
 return `<section class="evidence-console ${local?'local-evidence':''}" aria-label="Fictional evidence preview"><div><b>${local?'LOCAL EVIDENCE SCAN':'REQUESTED EVIDENCE · LOCAL PREVIEW'}</b><span>${local?'On this Fury':'Cloud upload: 0 B'}</span></div><p>${e(s.evidence)}</p><pre>${(s.log_preview||['Fictional evidence loaded locally. Restart to view the updated preview.']).map(e).join('\n')}</pre><small>${local?'Existing local model analyzes the full fictional dataset. Recovery changes only the demo city.':'Scripted request check. Displayed here, never sent to a cloud model.'}</small></section>`;
}

export function comparisonNotes(content){return `<details class="comparison-notes"><summary>What is actually blocked here?</summary><p>Cloud frontier models can help with authorized cybersecurity. In this fictional scenario, <b>Northwind’s data and action policy</b> denies the selected external route. This is a scripted request check, not a live provider refusal or a model benchmark.</p><p>Some legitimate requests may trigger safety checks. Providers also offer enterprise data controls and capacity options. API quotas are not evidence of an inevitable cloud shortage. Evaluate local capacity for your own workload; local AI still needs safeguards, permissions, reliable infrastructure and human approval.</p><div class="story-source-links">${content.story_sources.map(x=>`<a href="${e(x.url)}" target="_blank" rel="noopener noreferrer">${e(x.title)} ↗</a>`).join('')}</div></details>`;}

export function guidedWorld(state,content,robot){
 if(!state.guided||!state.story||!['wave','translate'].includes(state.phase))return '';
 const s=state.story;
 const positions=[[22,18],[48,8],[75,18],[30,58],[68,57]];
 return `<div class="agent-city-overlay ${s.running?'deployed':'standby'} ${state.paused?'paused-scene':''}" aria-label="Animated demonstration agents; actual AI counters are shown separately">${roles.map((name,i)=>{
 const [x,y]=positions[i],done=i<s.cursor,active=s.running&&i===s.cursor;
 return `<div class="mission-bot ${active?'mission-active':done?'mission-done':''}" style="--agent-x:${x}%;--agent-y:${y}%;--agent-color:${content.robots[name][2]};--delay:${i*.18}s"><div class="agent-platform"></div>${robot(name,done?'success':'idle')}<b>${name}</b><span>${done?'✓ Demo step done':active?'Demo action':'Local squad'}</span></div>`;
 }).join('')}<span class="scene-scope">Fictional city · guided demonstration</span></div>`;
}

export function deploymentLanes(state){
 if(!state.guided||!state.story||!['wave','translate'].includes(state.phase))return '';
 const deployed=state.story.cursor>0||state.story.running;
 return `<div class="deployment-lanes"><div class="deployment-lane cloud-lane">${cloudArt()}<div><b>Cloud path</b><small>▣ Evidence held by customer policy</small></div><span class="route-end">×</span></div><div class="deployment-lane local-lane ${deployed?'route-live':''}"><span class="fury-device"><i></i><i></i><i></i><b>ZGX</b></span><div><b>HP ZGX Fury</b><small>${deployed?'✓ Local analysis · scoped demo actions':'◎ Local squad ready'}</small></div><span class="route-end">${deployed?'→':'○'}</span></div></div>`;
}

export function valueBeat(state){
 if(!state.guided||!state.story||!['wave','translate'].includes(state.phase))return '';
 const v=state.story.value;
 return `<aside class="local-value" aria-label="Why local AI matters"><div class="eyebrow">Connect it to the customer</div><h3>${e(v.title)}</h3><p>${e(v.body)}</p><blockquote>${e(v.seller)}</blockquote></aside>`;
}

export function humanHandoff(state){
 const review=state.story?.human_review;
 if(!review)return '';
 return `<div class="human-handoff"><span>♙</span><div><b>Human review queued in the demo</b><p>${e(review.text)}</p><small>In-app demonstration only. No email, page or production change was sent.</small></div></div>`;
}
