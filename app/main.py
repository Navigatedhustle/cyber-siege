"""Cyber Siege: local, durable team experience and facilitator API."""
import asyncio
import csv
import io
import json
import logging
import re
import secrets
import time
import zipfile
from collections import Counter
from contextlib import asynccontextmanager
from datetime import date, timedelta
from pathlib import Path
import httpx
import qrcode
import yaml
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from app.config import ROOT, settings
from app.db import Database
from app.sse import EventBus
from app.phases import new_session, control, remaining, NAMES
from app.ai.router import ModelRouter
from app.ai.specialists import investigate_specialist
from app.ai.lead import lead
from app.ai.retrieval import logs, START_ORDER
from app.ai import replay, overdrive
from app.ai.twist_check import two_model_check
from app.metrics import Telemetry
from app.gpu import GPU
from app.cards import templates, build_card, clean_text
from app.pdf import card_html, render_pdf
from app.scoring import score
from scenario.alerts import ALERTS
from scenario.answer_key import EVIDENCE
from scenario.twist import TWIST
from app.participants import context as person_context,prepare as prepare_person,is_individual,advance as advance_person,introduce_event,response_seconds

log=logging.getLogger(__name__)

class Join(BaseModel):
    name: str = Field(min_length=1,max_length=24)
    join_code: str
class Pick(BaseModel):
    alert: str
class Decision(BaseModel):
    decision: str
    evidence: list[str] = Field(max_length=3)
class CardInput(BaseModel):
    account: str = Field(max_length=80)
    industry: str
    owner: str = Field(max_length=80)
    target_date: str
class Login(BaseModel):
    pin: str
class Command(BaseModel):
    action: str
    confirm: bool=False
    label: str='LIVE'
    team_id: str|None=None
    name: str|None=None
class PersonalAction(BaseModel):
    action: str
    expected_phase: int|None=None
    expected_reveal: int|None=None
class PersonalStart(BaseModel):
    client_id: str|None=Field(default=None,min_length=16,max_length=100)


def create_app(database=None,model_router=None):
    db=database or Database()
    bus=EventBus()
    telemetry=Telemetry(db)
    router=model_router or ModelRouter(telemetry=telemetry)
    router.telemetry=telemetry
    gpu=GPU()
    stored=db.get('meta','active')
    session=db.get('session',stored['id']) if stored else None
    if not session:
        session=new_session()
        db.put('session',session['id'],session); db.put('meta','active',{'id':session['id']})
    session.setdefault('started',session['phase']>1)
    session.setdefault('mode','individual')
    if session.get('overdrive')=='running':
        session['overdrive']='interrupted'
        db.put('session',session['id'],session)
    for team in db.all('team'):
        if team.get('progress',{}).get('overdrive')=='running':
            team['progress']['overdrive']='interrupted'
            db.put('team',team['id'],team)
        if team.get('investigation',{}).get('status')=='running':
            team['investigation']['status']='interrupted'
            db.put('team',team['id'],team)
    telemetry.restore(session['id'])
    tasks=set()
    public_health={'reachable':None,'checked_at':None}
    def spawn(coro):
        task=asyncio.create_task(coro)
        tasks.add(task); task.add_done_callback(tasks.discard)
        return task
    def persist():
        db.put('session',session['id'],session)
        bus.publish('state',{'session_id':session['id']})
    def teams():
        return sorted(db.for_session('team',session['id']),key=lambda t:(t['joined_at'],t['id']))
    def store_team(team):
        db.put('team',team['id'],team)
        if is_individual(team):
            bus.publish('team',{'id':team['id']},team['id'])
            bus.publish('room',{'id':team['id']},'screen')
        else:bus.publish('team',{'id':team['id']})
    def warnings():
        result=[f"Draft template: {v['industry']}" for v in templates().values() if v['status']=='draft']
        if not (ROOT/'content/customer_story.md').exists(): result.append('Customer story not loaded')
        deployment=yaml.safe_load((ROOT/'content/deployment.yaml').read_text())
        result += [f'Deployment fact awaiting confirmation: {k}' for k,v in deployment.items() if v.get('confirm',True)]
        if not settings.lab_request_url: result.append('LAB_REQUEST_URL is missing')
        if settings.card_llm_polish: result.append('Card polish requested but has not passed a wording gate; using approved template text')
        if settings.agentic_mode: result.append('Agentic mode requested but not rehearsed; using deterministic retrieval')
        if not router.lineup(): result.append('No qualified live model. Run model gates or use recorded rehearsal.')
        return result
    def public_state(team=None,admin=False):
        effective=person_context(session,team)
        allteams=teams(); metric=telemetry.latest.get(session['id'])
        completed=[r for r in db.for_session('investigation',session['id']) if not r['cached']]
        served={r['team_id'] for r in completed}
        cards=[db.get('card',t['card_id']) for t in allteams if t.get('card_id')]
        safe_teams=[]
        for t in allteams:
            safe={'id':t['id'],'name':t['name'],'pick':t.get('pick'),'agents':{role:{key:value for key,value in agent.items() if key in ('status','model','cached')} for role,agent in t.get('agents',{}).items()},
                  'investigation_status':t.get('investigation',{}).get('status','idle'),'phase':person_context(session,t)['phase']}
            if session['leaderboard'] and session['phase']>=4:
                safe.update(score=t.get('score'),decision_at=t.get('decision_at'),response_seconds=response_seconds(session,t))
            safe_teams.append(safe)
        s={**effective,'remaining_seconds':remaining(effective),'phase_name':NAMES[effective['phase']-1]}
        # Never serialize access tokens, private evidence or owners to public state.
        value={'session':s,'teams':safe_teams,'alerts':ALERTS,'picks':dict(Counter(t.get('pick') for t in allteams if t.get('pick'))),
               'joined':len(allteams),'max_teams':settings.max_teams,'max_participants':settings.max_participants,'served':len(served),'investigations_completed':len(completed),
               'models':[{'key':k,**router.config[k]} for k in router.lineup(session['label']=='REHEARSAL')],
               'metrics':None if session['replay'] else metric,
               'recorded_at':next((x.get('investigation',{}).get('recorded_at') for x in allteams if x.get('investigation',{}).get('cached')),None),
               'commitments':[{'account':c['account'],'owner_first_name':c['owner'].split()[0]} for c in cards if c],
               'commitment_count':len(cards),'industries':{k:v['industry'] for k,v in templates().items()},
               'agent_runs':sum(1 for e in db.events(session['id']) if e.get('type')=='usage'),
               'default_target_date':(date.today()+timedelta(days=14)).isoformat(),
               'join_url':settings.public_base_url.rstrip('/')+'/play?start=1','lab_request_url':settings.lab_request_url}
        if team:
            value['team']={k:v for k,v in team.items() if k!='token'}
            if effective['phase']>=3:
                value['evidence']={k:{'title':v['title'],'log_ids':v['log_ids']} for k,v in EVIDENCE.items() if effective['twist'] or k!='twist'}
            if effective['twist']: value['twist']=TWIST
        if effective['phase']>=4 or admin:
            story=ROOT/'content/customer_story.md'
            value['customer_story']=story.read_text() if story.exists() else 'Customer story not loaded'
            value['deployment']=yaml.safe_load((ROOT/'content/deployment.yaml').read_text())
            value['boundary']={'model_endpoints':[{k:v for k,v in c.items() if k in ('name','model_id','base_url','serving_stack')} for c in router.config.values()],
                               'traffic':'Phone traffic includes team names, choices, timelines, model reviews, selected raw log rows when opened, account and owner entries, target dates and PDF downloads. The app calls configured loopback model endpoints; laptop fallback uses SSH forwards to the Fury.',
                               'retained':'The full synthetic dataset and session database are stored on the app host. Prompts and model outputs are processed by the app and its configured local inference path. Selected evidence and results are delivered to phones.',
                               'runtime_downloads':'Infinity documentation requires internet for attention kernel artifacts. See recorded outbound observations before making broader claims.',
                               'confirmed':not any(v.get('confirm',True) for v in value['deployment'].values())}
            reviews=[r for t in allteams for r in t.get('overdrive_reviews',[]) if not r.get('error')]
            if team and is_individual(team):reviews=[r for r in team.get('overdrive_reviews',[]) if not r.get('error')]
            value['overdrive_agreement']={'agreed':sum(r['data']['verdict']=='supports' for r in reviews),'total':len(reviews)}
        if admin:
            value.update(warnings=warnings(),model_health={k:{**router.config[k],**v,'metrics':(metric or {}).get('models',{}).get(k)} for k,v in router.status.items()},
                         connected_phones=bus.phones,sse_clients=len(bus.clients),public_health=public_health,
                         agent_runs=sum(1 for e in db.events(session['id']) if e.get('type')=='usage'))
            value['teams']=[{k:v for k,v in t.items() if k!='token'} for t in allteams]
        return value
    async def background():
        count=0
        while True:
            try:
                metric_scope=dict(session)
                if any(t.get('progress',{}).get('overdrive')=='running' for t in teams()):metric_scope['overdrive']='running'
                metric=await telemetry.sample(metric_scope,router,gpu)
                bus.publish('metrics',{'sample':metric} if not session['replay'] else {'replay':True})
                if count%30==0 and settings.public_base_url.startswith('https://'):
                    try:
                        async with httpx.AsyncClient(timeout=4,trust_env=False) as client:
                            response=await client.get(settings.public_base_url.rstrip('/')+'/health')
                            public_health.update(reachable=response.is_success,checked_at=time.time())
                    except Exception:
                        public_health.update(reachable=False,checked_at=time.time())
            except asyncio.CancelledError: raise
            except Exception: log.exception('Telemetry poll failed')
            count+=1
            await asyncio.sleep(1)
    async def health_loop():
        while True:
            started=time.monotonic()
            await router.probe()
            if session['label']=='LIVE' and 'hero' not in router.lineup() and not session['replay']:
                session['replay']=True;persist()
            await asyncio.sleep(max(.1,5-(time.monotonic()-started)))
    @asynccontextmanager
    async def lifespan(app):
        await router.probe()
        # A restart preserves submitted decisions and resumes unfinished reviews.
        if not session['replay']:
            for person in teams():
                if is_individual(person) and person.get('decision') and not person.get('reviews'):
                    spawn(check_team(person,person_context(session,person)))
        poll=spawn(background())
        spawn(health_loop())
        yield
        for task in list(tasks): task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)
        await router.close()
    app=FastAPI(title='Cyber Siege: Stop the Breach',lifespan=lifespan)
    app.state.db=db; app.state.router=router; app.state.bus=bus
    app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
    async def admin(request:Request):
        # This workshop deliberately has no sign-in, as requested by its owner.
        return True
    async def phone(request:Request):
        token=request.headers.get('authorization','').removeprefix('Bearer ')
        for team in teams():
            if secrets.compare_digest(team['token'],token): return team
        raise HTTPException(401,'Join this session again')
    def require_phase(*phases,team=None):
        if person_context(session,team)['phase'] not in phases: raise HTTPException(409,'This step is not open yet')
    @app.get('/')
    async def root(): return FileResponse(ROOT/'static/welcome/index.html')
    for surface in ('play','screen','facilitator'):
        def page(name):
            async def serve(): return FileResponse(ROOT/f'static/{name}/index.html')
            return serve
        app.add_api_route('/'+surface,page(surface),methods=['GET'])
    @app.get('/health')
    async def health():
        return {'status':'ok','inference':'local only','hero_available':router.status['hero']['healthy'],
                'qualified_models':router.lineup(),'replay':session['replay'],'session_label':session['label']}
    @app.get('/api/public')
    async def state(): return public_state()
    @app.get('/api/me')
    async def me(team=Depends(phone)): return public_state(team)
    @app.get('/api/facilitator')
    async def facilitator(_=Depends(admin)): return public_state(admin=True)
    @app.post('/api/login')
    async def login(body:Login,request:Request):
        return {'sign_in_required':False}  # Compatibility for existing rehearsal tools.
    @app.post('/api/experience/start')
    async def start_individual(request:Request,body:PersonalStart|None=None):
        token=request.headers.get('authorization','').removeprefix('Bearer ')
        person=next((p for p in teams() if token and secrets.compare_digest(p['token'],token)),None)
        start_key=session['id']+':'+body.client_id if body and body.client_id else None
        if not person and start_key:
            saved=db.get('participant-start',start_key)
            if saved:person=db.get('team',saved['participant_id'])
        if not person:
            active=sum(not p.get('card_id') for p in teams() if is_individual(p))
            if active>=settings.max_participants:raise HTTPException(409,'The experience is at capacity. Please try again shortly.')
            person={'id':secrets.token_hex(8),'token':secrets.token_urlsafe(32),'session_id':session['id'],'name':f'Participant {max([int(p["name"].split()[-1]) for p in teams() if re.fullmatch(r"Participant \d+",p["name"])],default=0)+1:02}','joined_at':time.time(),'agents':{}}
        prepare_person(person);store_team(person)
        if start_key:db.put('participant-start',start_key,{'participant_id':person['id']})
        changed=session.get('mode')!='individual' or session['phase']==1
        session['mode']='individual'
        if session['phase']==1:session.update(phase=3,paused=True,started=True,open=True)
        if changed:persist()
        return {'token':person['token'],'participant_id':person['id'],'state':public_state(person)}
    async def personal_drive(person,scope):
        async def result(original,review):
            current=db.get('team',person['id'])
            if current:current.setdefault('overdrive_reviews',[]).append(review);store_team(current)
        try:await overdrive.run(router,[person],scope,result)
        finally:
            current=db.get('team',person['id'])
            if current:current['progress']['overdrive']='done';store_team(current)
    @app.post('/api/experience/control')
    async def personal_control(body:PersonalAction,team=Depends(phone)):
        if not is_individual(team):raise HTTPException(409,'Press Start experience to continue individually')
        progress=team['progress'];scope=person_context(session,team)
        if body.expected_phase is not None and body.expected_phase!=progress['phase']:return {'ok':True}
        if body.expected_reveal is not None and body.expected_reveal!=progress['reveal']:return {'ok':True}
        try:
            if body.action=='next':advance_person(team,scope['replay'])
            elif body.action=='twist':introduce_event(team)
            elif body.action in ('reveal','previous_reveal'):
                if progress['phase']!=4:raise ValueError('The reveal opens after your decision')
                progress['reveal']=max(0,min(6,progress['reveal']+(1 if body.action=='reveal' else -1)))
            elif body.action=='overdrive':
                if progress['phase']!=4 or not team.get('decision'):raise ValueError('Submit your decision before the extra review')
                if scope['replay']:raise ValueError('Extra live reviews are unavailable during replay')
                if progress['overdrive'] in ('running','done'):return {'ok':True}
                team['overdrive_reviews']=[]
                progress['overdrive']='running';store_team(team);spawn(personal_drive(team,scope))
                return {'ok':True}
            else:raise ValueError('Unknown experience action')
        except ValueError as exc:raise HTTPException(409,str(exc))
        store_team(team);return {'ok':True}
    @app.post('/api/join')
    async def join(body:Join):
        if not session['open'] or session['phase']!=1: raise HTTPException(409,'Lobby is closed')
        if body.join_code.strip().upper()!=session['join_code']: raise HTTPException(400,'Check the join code on the main screen')
        try: name=clean_text(body.name,24)
        except ValueError as exc: raise HTTPException(400,str(exc))
        normalized=re.sub(r'[^a-z]','',name.casefold())
        if any(word in normalized for word in ('fuck','shit','cunt','nigger','bitch','asshole')): raise HTTPException(400,'Choose a room friendly team name')
        if any(t['name'].casefold()==name.casefold() for t in teams()): raise HTTPException(409,'That team name is taken')
        if len(teams())>=settings.max_teams: raise HTTPException(409,'The room is full')
        team={'id':secrets.token_hex(8),'token':secrets.token_urlsafe(32),'session_id':session['id'],'name':name,'joined_at':time.time(),'agents':{}}
        store_team(team)
        return {'token':team['token'],'team_id':team['id']}
    @app.post('/api/pick')
    async def pick(body:Pick,team=Depends(phone)):
        require_phase(2,team=team)
        if body.alert not in {x['id'] for x in ALERTS}: raise HTTPException(400,'Choose one alert')
        team['pick']=body.alert; store_team(team); return {'ok':True}
    async def investigate(team,scope):
        started=time.monotonic(); events=[]
        async def emit(data):
            # Reload latest team to avoid overwriting subsequent facilitator changes.
            current=db.get('team',team['id'])
            if not current: return
            events.append({'elapsed':time.monotonic()-started,'data':data})
            agent=data.get('agent')
            if agent:
                previous=current.setdefault('agents',{}).get(agent,{})
                current['agents'][agent]={**previous,**data}
                if data.get('finding'):
                    current['agents'][agent]['findings']=previous.get('findings',[])+[data['finding']]
            db.put('team',current['id'],current)
            bus.publish('progress',{'team_id':team['id'],**data},team['id'])
            # Screen receives status only, never a private bearer token.
            bus.publish('grid',{'team_id':team['id'],'agent':agent,'status':data.get('status')},'screen')
        async def use_recording():
            recording=replay.load(team['pick'])
            if not recording:raise RuntimeError('No rehearsal recording for this starting alert. Rehearse while hero is available.')
            current=db.get('team',team['id'])
            if current:
                current['investigation'].update(cached=True,recorded_at=recording['recorded_at'])
                store_team(current);bus.publish('refresh',{},team['id'])
            return await replay.replay(team['pick'],emit)
        try:
            if scope['replay']:
                result=await use_recording()
            else:
                try:
                    # Schedule the chosen starting source first, then run every source concurrently.
                    order=START_ORDER[team['pick']]
                    results=await asyncio.gather(*(investigate_specialist(router,role,team['pick'],scope,emit) for role in order))
                    await emit({'agent':'lead','status':'started','query':'Connect verified specialist findings'})
                    result=await lead(router,results,scope)
                    await emit({'agent':'lead','status':'done','model':result['model'],'tokens_used':(result.get('usage') or {}).get('completion_tokens')})
                    result['cached']=False
                    if scope['label']=='REHEARSAL': replay.save(team['pick'],result,events,scope)
                except Exception:
                    log.exception('Live investigation failed; attempting explicitly labeled recording')
                    result=await use_recording()
            current=db.get('team',team['id'])
            if current:
                current['investigation']={'status':'done','duration_seconds':time.monotonic()-started,**result}
                db.put('investigation',secrets.token_hex(12),{'session_id':scope['id'],'team_id':team['id'],'cached':result.get('cached',False),'completed_at':time.time(),'duration_seconds':current['investigation']['duration_seconds']})
                store_team(current)
        except asyncio.CancelledError: raise
        except Exception as exc:
            current=db.get('team',team['id'])
            if current:
                current['investigation']={'status':'failed','error':str(exc)[:200]}
                store_team(current)
        bus.publish('refresh',{},team['id'])
    @app.post('/api/investigate')
    async def launch(team=Depends(phone)):
        require_phase(3,team=team)
        if not team.get('pick'): raise HTTPException(409,'Choose your first alert in phase two')
        if team.get('investigation',{}).get('status') in ('running','done'): return {'ok':True}
        team['investigation']={'status':'running'}; team['agents']={}; store_team(team)
        spawn(investigate(team,person_context(session,team)))
        return {'ok':True}
    async def check_team(team,scope):
        reviews=await two_model_check(router,team,scope)
        current=db.get('team',team['id'])
        if current:
            current['reviews']=reviews; store_team(current)
            bus.publish('refresh',{},team['id'])
    @app.post('/api/decision')
    async def decide(body:Decision,team=Depends(phone)):
        require_phase(3,team=team)
        scope=person_context(session,team)
        if not scope['twist']: raise HTTPException(409,'Open the new event first')
        if scope['locked'] or team.get('decision'): raise HTTPException(409,'Decision already submitted')
        if team.get('investigation',{}).get('status')!='done': raise HTTPException(409,'Finish the investigation first')
        try: points=score(body.decision,body.evidence)
        except ValueError as exc: raise HTTPException(400,str(exc))
        team.update(decision=body.decision,evidence=body.evidence,score=points,decision_at=time.time())
        store_team(team)
        if not scope['replay']: spawn(check_team(team,scope))
        return {'ok':True}
    @app.post('/api/card')
    async def make_card(body:CardInput,team=Depends(phone)):
        require_phase(5,team=team)
        if team.get('card_id'): return {'id':team['card_id']}
        try: card=build_card(team,**body.model_dump())
        except ValueError as exc: raise HTTPException(400,str(exc))
        db.put('card',card['id'],card); team['card_id']=card['id']; store_team(team)
        return {'id':card['id']}
    @app.get('/api/logs/{log_id}')
    async def raw_log(log_id:str,team=Depends(phone)):
        scope=person_context(session,team)
        row=logs().get(log_id)
        if not row or row.get('injected') and not scope['twist']: raise HTTPException(404,'Log unavailable')
        if scope['phase']<3: raise HTTPException(409,'Investigation has not opened')
        return {k:v for k,v in row.items() if k not in ('injected','routine')}
    @app.get('/card/{card_id}.pdf')
    async def pdf(card_id:str):
        card=db.get('card',card_id)
        if not card: raise HTTPException(404,'Card not found')
        payload=await asyncio.to_thread(render_pdf,card)
        return Response(payload,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="account-action-card.pdf"','Cache-Control':'private, no-store'})
    @app.get('/card/{card_id}')
    async def card_page(card_id:str):
        card=db.get('card',card_id)
        if not card: raise HTTPException(404,'Card not found')
        return HTMLResponse(card_html(card),headers={'Cache-Control':'private, no-store'})
    async def drive(scope):
        session['overdrive']='running'; session['overdrive_started_at']=time.time(); persist()
        async def result(team,review):
            current=db.get('team',team['id'])
            if current:
                current.setdefault('overdrive_reviews',[]).append(review); store_team(current)
        try:
            await overdrive.run(router,teams(),scope,result)
        finally:
            if session['id']==scope['id']:
                session['overdrive']='done';session['overdrive_finished_at']=time.time();persist()
    @app.post('/api/rehearsal/combined')
    async def combined_load(_=Depends(admin)):
        if session['label']!='REHEARSAL' or session['phase']!=4:
            raise HTTPException(409,'Combined capacity tests are restricted to rehearsal reveal phase')
        if session['overdrive'] not in ('idle','interrupted'): raise HTTPException(409,'Overdrive already launched')
        current_teams=teams()
        if not current_teams or not all(t.get('decision') for t in current_teams):
            raise HTTPException(409,'Every bot team must first complete and decide its case')
        for team in current_teams:
            team['investigation']={'status':'running'};team['agents']={};store_team(team)
            spawn(investigate(team,dict(session)))
        session['overdrive']='running';persist();spawn(drive(dict(session)))
        return {'ok':True,'teams':len(current_teams)}
    @app.post('/api/control')
    async def controls(body:Command,_=Depends(admin)):
        nonlocal session
        if body.action in ('create','reset'):
            if body.action=='reset' and not body.confirm: raise HTTPException(400,'Confirm reset first')
            if session['overdrive']=='running' or any(t.get('investigation',{}).get('status')=='running' or t.get('progress',{}).get('overdrive')=='running' for t in teams()) or any(s['active'] or s['queue_depth'] for s in router.status.values()): raise HTTPException(409,'Wait for running investigations before resetting')
            if body.label not in ('LIVE','REHEARSAL'): raise HTTPException(400,'Use LIVE or REHEARSAL')
            session=new_session(body.label); db.put('meta','active',{'id':session['id']})
        elif body.action=='overdrive':
            require_phase(4)
            if session['replay']: raise HTTPException(409,'Overdrive requires live inference; replay remains labeled')
            if session['overdrive'] not in ('idle','interrupted'): raise HTTPException(409,'Overdrive already launched')
            session['overdrive']='running'; spawn(drive(dict(session)))
        elif body.action in ('rename','remove'):
            current=db.get('team',body.team_id)
            if not current or current['session_id']!=session['id']: raise HTTPException(404,'Team not found')
            if body.action=='remove': db.delete('team',current['id'])
            else:
                try: current['name']=clean_text(body.name or '',24)
                except ValueError as exc: raise HTTPException(400,str(exc))
                if any(t['id']!=current['id'] and t['name'].casefold()==current['name'].casefold() for t in teams()): raise HTTPException(409,'Name already taken')
                store_team(current)
        else:
            try: control(session,body.action)
            except ValueError as exc: raise HTTPException(400,str(exc))
        persist(); return public_state(admin=True)
    @app.get('/api/events')
    async def events(request:Request):
        audience=request.headers.get('x-surface','screen')
        if audience=='admin': await admin(request)
        elif audience=='phone': audience=(await phone(request))['id']
        else: audience='screen'
        return StreamingResponse(bus.stream(audience),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
    @app.get('/api/qr.png')
    async def qr():
        image=qrcode.make(settings.public_base_url.rstrip('/')+'/play?start=1')
        stream=io.BytesIO(); image.save(stream,format='PNG')
        return Response(stream.getvalue(),media_type='image/png')
    @app.get('/export')
    async def export(kind:str='commitments',_=Depends(admin)):
        allteams=teams()
        cards=[db.get('card',t['card_id']) for t in allteams if t.get('card_id')]
        if kind=='metrics':
            payload=json.dumps({'session':session,'samples':db.samples(session['id']),'events':db.events(session['id'])},indent=2)
            return Response(payload,media_type='application/json',headers={'Content-Disposition':'attachment; filename="metrics.json"'})
        if kind=='cards':
            def archive():
                stream=io.BytesIO()
                with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as z:
                    for c in cards: z.writestr(c['id']+'.pdf',render_pdf(c))
                return stream.getvalue()
            return Response(await asyncio.to_thread(archive),media_type='application/zip',headers={'Content-Disposition':'attachment; filename="cards.zip"'})
        stream=io.StringIO(); writer=csv.writer(stream)
        def safe(value):
            value=str(value)
            return "'"+value if value.startswith(('=','+','-','@','\t','\r')) else value
        if kind=='commitments':
            fields=['session','team','owner','account','industry','target_date','id']; writer.writerow(['session','participant','seller owner','account','industry','target date','card ID'])
            writer.writerows([[safe(c[k]) for k in fields] for c in cards])
        elif kind=='scores':
            writer.writerow(['session','participant','decision','score','response time seconds'])
            writer.writerows([[session['id'],safe(t['name']),t.get('decision',''),t.get('score',{}).get('total',''),response_seconds(session,t)] for t in allteams])
        else: raise HTTPException(400,'Unknown export')
        return Response(stream.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{kind}.csv"'})
    @app.middleware('http')
    async def security_headers(request,call_next):
        if request.method=='POST' and request.headers.get('origin'):
            from urllib.parse import urlparse
            if urlparse(request.headers['origin']).netloc not in {request.headers.get('host'),urlparse(settings.public_base_url).netloc}:
                return Response('Origin rejected',status_code=403)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='no-referrer'
        response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'self'; base-uri 'none'; form-action 'self'"
        if request.url.path.startswith(('/api/','/export','/card/')): response.headers['Cache-Control']='no-store'
        return response
    return app

