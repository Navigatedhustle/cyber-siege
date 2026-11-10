import {guidedDecision, guidedWorld, deploymentLanes, valueBeat, humanHandoff} from '/assets/guided-story.js?v=log-preflight-1';
import {robot as drawRobot, city, villain} from '/assets/art.js';
const $=s=>document.querySelector(s),app=$('#app');
const e=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const money=v=>'$'+Math.round(v||0).toLocaleString('en-US');
const industryName=v=>v.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
const clock=v=>`${Math.floor(Math.max(0,v)/60)}:${String(Math.floor(Math.max(0,v)%60)).padStart(2,'0')}`;
const order=['SCOUT','SHERLOCK','SHIELD','PATCH','SCRIBE'];
let content,state,token=null,socket,reconnectTimer,toastTimer,dialogAction=null,pending=false,downloading=false,online=false;
function newNonce(){const bytes=new Uint8Array(24);crypto.getRandomValues(bytes);return Array.from(bytes,x=>x.toString(16).padStart(2,'0')).join('');}
const reducedMotion=matchMedia('(prefers-reduced-motion: reduce)');
let calmMotion=false;try{calmMotion=localStorage.getItem('siege:calm-motion')==='true';}catch{}
function motionPreference(){document.body.className=`experience-body ${state?.guided?'guided-mode':''} ${calmMotion||reducedMotion.matches?'reduced':'guided-motion'}`;const b=$('[data-motion]');if(b){b.textContent=calmMotion||reducedMotion.matches?'Reduced motion':'Reduce motion';b.setAttribute('aria-pressed',String(calmMotion||reducedMotion.matches));}}
reducedMotion.addEventListener('change',motionPreference);
let nonce;
try{nonce=localStorage.getItem('siege:individual');if(!nonce){nonce=newNonce();localStorage.setItem('siege:individual',nonce);}}catch{nonce=newNonce();}
const robot=(name,status='idle')=>drawRobot(name,status,content);
const rendered=new Map();
function html(id,value){const el=document.getElementById(id);if(el&&rendered.get(id)!==value){const notesOpen=el.querySelector('details.comparison-notes')?.open;el.innerHTML=value;if(notesOpen&&el.querySelector('details.comparison-notes'))el.querySelector('details.comparison-notes').open=true;rendered.set(id,value);}}
function toast(text){$('#toast').textContent=text;$('#toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),4500);}
async function api(path,body){
 const response=await fetch(path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},...(body===undefined?{}:{body:JSON.stringify(body)})});
 const data=await response.json();if(!response.ok)throw new Error(data.error||'Please retry in a moment.');return data;
}
function shell(){app.innerHTML=`<main class="experience"><header class="experience-header"><div class="brand">CYBER <span>SIEGE</span><small>HP ZGX FURY · YOUR LOCAL AI EXPERIENCE</small></div><div class="header-actions"><button class="quiet share-button" data-share aria-label="Share this experience">Share experience ↗</button><button class="quiet" data-reset>Reset</button><button data-restart>Restart ↻</button></div></header><nav class="experience-progress" aria-label="Your progress"><ol class="journey-steps" id="steps"></ol><div class="story-preferences"><button class="quiet" data-motion aria-pressed="false">Reduce motion</button><span class="connection" id="connection" role="status">Connecting</span></div></nav><div class="journey-layout"><section class="panel world" aria-label="Your fictional customer"><div class="world-head" id="world-head"></div><section class="business-meters" id="meters" aria-label="Your business meters"></section><div class="world-stage"><div class="world-art" id="world-art"></div><div id="guided-world"></div></div><div id="deployment-lanes"></div><div id="story-value"></div><div class="world-key"><span>◎ Online</span><span>⚠ Needs help</span><span>❄ Frozen</span><span>✓ Restored</span></div><div class="local-strip" id="local-strip"></div></section><section class="panel decision" id="decision" aria-label="Your next action"></section></div><section class="squad" aria-label="Your local AI squad"><div class="squad-heading"><div class="eyebrow">Five local roles. One coordinated response.</div><small>Analyzing fictional evidence locally on this Fury</small></div><div class="squad-list" id="squad"></div></section><footer class="experience-footer"><p>Northwind is fictional. All dollar figures are game values. Local AI helps your team understand and contain problems; people decide and act. HP ZGX Fury is not a security product.</p><p>Progress is saved on this device. Reset and Restart affect only your experience.</p></footer></main>`;}
function connected(value){online=value;const el=$('#connection');if(el){el.textContent=value?'● Progress saved':'○ Reconnecting';el.dataset.online=String(value);}}
function update(next){state=next;render();connected(online);}
function render(){
 motionPreference();
 const t=state.teams[0],wave=state.wave_info;
 const current=state.phase==='debrief'?4:state.wave||0;
 html('steps',['Start','Payment','Inbox','Recovery','Your card'].map((label,i)=>`<li class="${i===current?'active':i<current?'done':''}" ${i===current?'aria-current="step"':''}><span class="step-dot">${i<current?'✓':i+1}</span><span>${label}</span></li>`).join(''));
 html('world-head',`<div><div class="eyebrow">${e(industryName(state.industry))} · fictional customer</div><h2>NORTHWIND <span class="muted">/ HQ</span></h2></div><span class="tag">${state.phase==='wave'?'⚠ UNDER PRESSURE':state.phase==='lobby'||state.phase==='briefing'?'◎ READY':'✓ RECOVERING'}</span>`);
 html('meters',`<div><small>Revenue at Risk · Game value</small><b>${money(t.risk)}</b></div><div><small>Customer Trust</small><b>${Math.round(t.trust)}<small> / 100</small></b></div><div><small>Records Exposed · Fictional</small><b>${Math.floor(t.records)}</b></div>`);
 html('world-art',city(state,content));
 html('guided-world',guidedWorld(state,content,robot));
 html('deployment-lanes',deploymentLanes(state));
 html('story-value',valueBeat(state));
 const p=state.shared_power||state.power;
 html('local-strip',`<span><b>${p.active}</b> model calls now · peak <b>${p.peak}</b></span><span><b>${p.evidence}</b> evidence items submitted</span><span class="secondary-counter"><b>${p.tokens}</b> output tokens</span><span title="Game AI HTTP payloads only; excludes private UI traffic and model startup downloads.">Game AI data to cloud: <b>${p.cloud_bytes} B</b></span><span class="secondary-counter"><b>${p.tps.toFixed(1)}</b> tokens/s · recent calls</span>`);
 let decision='';
 if(state.phase==='lobby')decision=`<div class="eyebrow">The why-local-AI story</div><h1>Under attack.<br>Keep the<br>evidence close.</h1><p class="lead">Watch a cloud request check deny this scenario’s sensitive-evidence workflow. Deploy five local AI roles on an HP ZGX Fury, then see them investigate, demonstrate recovery and prepare a human handoff.</p><div class="value-note"><span class="symbol">◎</span><p>One click deploys the squad. Value cards connect the action to a customer conversation. Leave with your Account Action Card.</p></div><button class="primary" data-command="start">Start the story →</button><p class="sub-note">Everyone uses this link. Your story and progress are your own.</p><details class="industry-options"><summary>Choose a different customer industry</summary><label for="industry">Industry</label><select id="industry">${Object.keys(content.industries).map(key=>`<option value="${key}" ${key===state.industry?'selected':''}>${industryName(key)}</option>`).join('')}</select></details>`;
 else if(state.phase==='briefing')decision=`<div class="eyebrow">Your mission</div><h1>Your people.<br>Your decisions.<br>Local AI help.</h1><p class="lead">Protect revenue, trust and uptime. Ask the robots to explain the evidence, then choose what the team should do.</p><div>${['SCOUT','SHERLOCK','SHIELD'].map(name=>`<div class="robot-line">${robot(name)}<div><b>${name}</b><p>${e(content.robots[name][1])}</p></div></div>`).join('')}</div><button class="primary" data-command="next">Take on the first challenge →</button><p class="sub-note">PATCH helps restore service. SCRIBE helps explain the value. You’ll use the whole squad.</p>`;
 else if(state.phase==='translate')decision=`<div class="eyebrow">✓ Challenge ${state.wave} contained</div><h1>Turn the result<br>into a value story.</h1><div class="translation-lines">${(state.guided&&state.story?state.story.translate:wave.translate).map((line,i)=>`<div><b>${['The customer pain','What local AI helped with','What you can say'][i]}</b><p class="${i===2?'seller-say':''}">${e(line)}</p></div>`).join('')}</div>${state.guided?humanHandoff(state):''}<button class="primary" data-command="next">${state.wave===3?'Build my Account Action Card':'Continue to the next challenge'} →</button>`;
 else if(state.phase==='debrief'){
 const card=state.account_card||{};
 decision=`<div class="eyebrow">Your next customer conversation</div><h1>Make the<br>value personal.</h1><div class="result-summary"><div><b>${state.guided?(state.human_reviews?.length||0)*5:t.score}</b><small>${state.guided?'demo steps completed':'points earned'}</small></div><div><b>${Math.round(t.trust)}/100</b><small>customer trust</small></div><div><b>${state.guided?(state.human_reviews?.length||0):t.fast}</b><small>${state.guided?'human reviews queued':'fast responses'}</small></div></div><div class="card-teaser"><div class="eyebrow">HP · Account Action Card</div><h2>Your next conversation,<br>ready to go.</h2><p>Your game result. Twelve HP platform differentiators and why customers care. Discovery questions, a next step and official resources.</p></div><form class="card-form" id="card-form"><label for="account">Account or opportunity <span class="muted">(optional)</span></label><input id="account" name="account" maxlength="80" value="${e(card.account||'')}" placeholder="The customer you want to speak with" autocomplete="off"><label for="next-step">Your next step <span class="muted">(optional)</span></label><textarea id="next-step" name="next_step" maxlength="200" placeholder="For example: invite the technical champion to a local AI discovery session">${e(card.next_step||'')}</textarea><button class="primary" type="submit" ${downloading?'disabled':''}>${downloading?'Preparing your card…':'Download my Account Action Card ↓'}</button></form><p class="sub-note">One page. Clickable HP links and a QR code. Account details stay on the card and are never sent to the AI model.</p><div class="official-links">${content.hp_resources.map(r=>`<a href="${e(r.url)}" target="_blank" rel="noopener noreferrer">${e(r.title)} ↗</a>`).join('')}</div>`;
 }else if(state.phase==='wave'&&state.guided){decision=guidedDecision(state,content,robot,villain);
 }else if(state.phase==='wave'){
 const head=`<div class="row between"><div class="eyebrow">Challenge ${state.wave} / 3</div><span class="time-chip">◷ ${clock(state.remaining)} remaining</span></div><h1>${e(wave.name)}</h1>`;
 if(state.paused){decision=head+`<div class="resume-bar"><b>Your experience is paused.</b><p>Your place and choices are saved.</p><button data-command="pause">Resume my experience →</button></div>`;}
 else if(state.wave===1){decision=head+`<p class="lead">Finance receives an urgent invoice. How will you protect the payment?</p><div class="invoice"><small>Fictional invoice · INV-104</small><b>$48,000 due in 15 minutes.</b><p>New bank details. The reply address differs from the sender. “Do not call the usual contact.”</p></div><div class="choice-list">${[
 ['analyze','⌕','Ask SHERLOCK to check it','Find the warning signs. After both checks, new downtime risk stops and Trust recovers by up to 4.'],
 ['verify','☎','Call the vendor to verify','Use a trusted number. Combine the human check with AI analysis to protect the payment.'],
 ['pay','$','Pay it now','Game value: +$48,000 at risk and Trust −8. You can still recover.']
 ].map(([a,icon,title,effect])=>`<button class="action-card ${a==='pay'?'risky':''}" data-action="${a}" ${t.progress.includes(a)?'disabled':''}><span class="symbol">${icon}</span><span><strong>${title} ${t.progress.includes(a)?'✓':''}</strong><small>${e(effect)}</small></span></button>`).join('')}</div>`;}
 else{
 const active=state.wave===2?'SCOUT':order[t.progress.length]||'SCRIBE';
 const effect=state.wave===2?'Each scan stops new downtime and record loss at that building. All six safe: Trust +4, capped at 100.':({SCOUT:'Find the problem. No immediate meter change.',SHERLOCK:'Explain the evidence. No immediate meter change.',SHIELD:'Stops new records exposure. Downtime risk continues until restoration.',PATCH:'Restores the buildings. Stops new downtime risk and trust loss.',SCRIBE:'Communicates the recovery. Completes your response; Trust +4, capped at 100.'})[active];
 decision=head+`<p class="lead">${state.wave===2?'200 fictional emails. 12 fakes. Send SCOUT to each building to check and quarantine.':'Spot → explain → isolate → restore → communicate. Deploy the next AI role to a building.'}</p><div class="next-role">${robot(active)}<div><b>${active} is ready</b><p>${e(content.robots[active][1])}</p></div></div><div class="effect-line"><b>Before you deploy:</b> ${e(effect)}</div><div class="deploy-grid">${state.buildings.map((b,i)=>`<button data-action="${active}" data-building="${i}" ${state.wave===2&&t.progress.includes(i)?'disabled':''}><span>${e(b)}</span><small>${state.wave===2&&t.progress.includes(i)?'✓ Checked':`Deploy ${active} →`}</small></button>`).join('')}</div><p class="sub-note">Correct actions: +100 points. Act within 10 seconds for a +25 Fast Response bonus.</p>`;
 }
 if(t.last_action)decision+=`<p class="session-message" role="status">${e(t.last_action.replaceAll('Your team','You').replaceAll('your team','you'))}</p>`;
 if(!state.paused)decision+='<button class="quiet" data-command="pause" style="margin-top:15px">Pause my experience</button>';
 }
 if(!state.guided&&state.phase!=='lobby')decision='<div class="legacy-note">Your saved progress is preserved. Choose <b>Restart</b> to try the new one-click agent story.</div>'+decision;
 html('decision',decision);
 html('squad',order.map(name=>{const bubble=state.bubbles[name],status=bubble?.status||'idle';return`<article class="panel robot-card ${status}" style="--robot:${content.robots[name][2]}"><div class="robot-top">${robot(name,status)}<div><div class="status">${status==='working'?'● Analyzing locally':status==='success'?(bubble?.shared?'✓ Shared local analysis':'✓ Ready'):'◎ Your AI squad'}</div><h3>${name}</h3></div></div><p class="bubble">${e(bubble?.text||content.robots[name][1])}</p></article>`;}).join(''));
}
function connect(){
 clearTimeout(reconnectTimer);if(socket){socket.onclose=null;socket.close();}
 socket=new WebSocket(`${location.protocol==='https:'?'wss:':'ws:'}//${location.host}/ws/${state.code}`);
 socket.onopen=()=>{socket.send(JSON.stringify({type:'hello',token}));connected(true);};
 socket.onmessage=event=>{const packet=JSON.parse(event.data);if(packet.state){update(packet.state);connected(true);}if(packet.type==='notice')toast(packet.text);};
 socket.onclose=()=>{connected(false);reconnectTimer=setTimeout(connect,1000);};socket.onerror=()=>connected(false);
}
async function control(command){
 if(pending)return;pending=true;
 try{update(await api('/api/experience/control',{command,...(command==='start'?{industry:$('#industry')?.value||state.industry}:{})}));}
 finally{pending=false;}
}
function confirmChange(command){
 dialogAction=command;
 const restart=command==='restart';
 $('#confirm-content').innerHTML=`<h2>${restart?'Restart your experience?':'Reset to the welcome screen?'}</h2><p>${restart?'Start the same customer scenario again from the beginning.':'Clear your choices and return to the start so you can choose an industry again.'} Your saved card details and current results will clear. Other people keep their progress.</p><div class="dialog-actions"><button class="quiet" data-cancel>Keep playing</button><button class="${restart?'primary':'danger'}" data-confirm>${restart?'Restart now':'Reset my experience'}</button></div>`;
 $('#confirm-dialog').showModal();
}
app.addEventListener('click',async event=>{
 const b=event.target.closest('button');if(!b)return;
 try{
  if(b.hasAttribute('data-command'))await control(b.dataset.command);
  if(b.hasAttribute('data-action')){
   if(socket?.readyState!==WebSocket.OPEN){toast('Reconnecting. Your choices are saved.');return;}
   socket.send(JSON.stringify({type:'action',action:b.dataset.action,...(b.dataset.building===undefined?{}:{building:Number(b.dataset.building)})}));
  }
  if(b.hasAttribute('data-motion')){calmMotion=!(calmMotion||reducedMotion.matches);try{localStorage.setItem('siege:calm-motion',String(calmMotion));}catch{}motionPreference();}
  if(b.hasAttribute('data-reset'))confirmChange('reset');
  if(b.hasAttribute('data-restart'))confirmChange('restart');
  if(b.hasAttribute('data-share')){
   const url=location.origin+'/';
   $('#confirm-content').innerHTML=`<h2>One link for everyone.</h2><p>Each person gets their own choices, progress and Account Action Card. Share this link with anyone on the same private connection.</p><img class="share-qr" src="/api/experience/share.png?url=${encodeURIComponent(url)}" alt="Scan to open the same experience on your own device"><input id="share-url" value="${e(url)}" readonly aria-label="Experience link"><div class="dialog-actions"><button data-copy>Copy link</button><button data-cancel>Done</button></div>`;dialogAction=null;$('#confirm-dialog').showModal();
  }
 }catch(error){toast(error.message);}
});
$('#confirm-dialog').addEventListener('click',async event=>{
 const b=event.target.closest('button');if(!b)return;
 try{
  if(b.hasAttribute('data-cancel'))$('#confirm-dialog').close();
  if(b.hasAttribute('data-confirm')){const cmd=dialogAction;$('#confirm-dialog').close();await control(cmd);toast(cmd==='restart'?'Your experience restarted.':'Your experience reset.');}
  if(b.hasAttribute('data-copy')){const field=$('#share-url');field.select();if(navigator.clipboard)await navigator.clipboard.writeText(field.value);else document.execCommand('copy');toast('Experience link copied.');}
 }catch(error){toast(error.message);}
});
app.addEventListener('submit',async event=>{
 if(event.target.id!=='card-form')return;event.preventDefault();if(downloading)return;
 const form=event.target,account=form.account.value,next_step=form.next_step.value;
 downloading=true;form.querySelector('button').disabled=true;
 try{
  update(await api('/api/experience/card',{account,next_step}));
  const response=await fetch('/api/experience/card.pdf',{headers:{Authorization:'Bearer '+token}});
  if(!response.ok){const data=await response.json();throw new Error(data.error||'Please retry your download.');}
  const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download='HP-Account-Action-Card.pdf';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);toast('Your Account Action Card is ready.');
 }catch(error){toast(error.message);}finally{downloading=false;render();const button=$('#card-form button');if(button)button.disabled=false;}
});
async function main(){
 content=await api('/api/content');const result=await api('/api/experience',{nonce});token=result.token;shell();update(result.state);connect();
}
main().catch(error=>{app.innerHTML=`<main class="panel error-box"><div class="eyebrow">Cyber Siege</div><h1>Let’s reconnect.</h1><p>${e(error.message)}</p><button class="primary" id="retry">Try again</button></main>`;$('#retry').onclick=()=>location.reload();});
