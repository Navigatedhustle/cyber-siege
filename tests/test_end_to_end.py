import asyncio
import json
from datetime import date,timedelta
import httpx
import pytest
from app.db import Database
from app.main import create_app
from app.ai.router import ModelRouter
from app.config import settings
from tests.stub_model import make_stub

@pytest.fixture
async def client(tmp_path,monkeypatch):
    from app.ai import replay
    monkeypatch.setattr(replay,"CACHE",tmp_path/"recordings")
    router=ModelRouter()
    for key,c in router.clients.items():
        await c.http.aclose()
        c.http=httpx.AsyncClient(transport=httpx.ASGITransport(app=make_stub()),base_url='http://127.0.0.1:8000')
        await c.health_http.aclose()
        c.health_http=httpx.AsyncClient(transport=httpx.ASGITransport(app=make_stub()),base_url='http://127.0.0.1:8000')
    router.qualified=lambda k:True
    app=create_app(Database(tmp_path/'e2e.db'),router)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://127.0.0.1:8080') as client:
            yield client,app

async def test_legacy_group_session_remains_compatible_with_open_controls(client):
    c,app=client
    assert (await c.get('/api/facilitator')).status_code==200
    assert (await c.get('/export')).status_code==200
    assert (await c.post('/api/login',json={'pin':settings.facilitator_pin})).is_success
    await c.post('/api/control',json={'action':'create','label':'REHEARSAL'})
    state=(await c.get('/api/public')).json(); code=state['session']['join_code']; headers=[]
    for index in range(3):
        result=await c.post('/api/join',json={'name':f'Team {index}','join_code':code}); assert result.is_success
        headers.append({'Authorization':'Bearer '+result.json()['token']})
    assert (await c.post('/api/join',json={'name':'Team 0','join_code':code})).status_code==409
    assert (await c.post('/api/join',json={'name':'Fuck','join_code':code})).status_code==400
    assert (await c.get('/api/public')).json()['teams'][0].get('token') is None
    await c.post('/api/control',json={'action':'next'})
    for header,alert in zip(headers,['identity','invoice','files']):
        assert (await c.post('/api/pick',headers=header,json={'alert':alert})).is_success
    await c.post('/api/control',json={'action':'next'})
    assert (await c.get('/api/logs/FIL9003',headers=headers[0])).status_code==404
    for header in headers: assert (await c.post('/api/investigate',headers=header,json={})).is_success
    for _ in range(300):
        states=[(await c.get('/api/me',headers=h)).json() for h in headers]
        if all(s['team'].get('investigation',{}).get('status')=='done' for s in states): break
        await asyncio.sleep(.01)
    assert all(s['team']['investigation']['status']=='done' for s in states),states
    for s in states: assert not s['team']['investigation']['cached']
    assert (await c.get('/api/me',headers=headers[0])).json()['team']==states[0]['team']
    await c.post('/api/control',json={'action':'twist'})
    for header in headers:
        assert (await c.post('/api/decision',headers=header,json={'decision':'escalate','evidence':['token','session','twist']})).is_success
    for _ in range(100):
        if all(len(t.get('reviews',[]))==2 for t in (await c.get('/api/facilitator')).json()['teams']):break
        await asyncio.sleep(.01)
    assert len((await c.get('/api/me',headers=headers[0])).json()['team']['reviews'])==2
    await c.post('/api/control',json={'action':'next'})
    assert (await c.post('/api/control',json={'action':'overdrive'})).is_success
    for _ in range(100):
        if (await c.get('/api/public')).json()['session']['overdrive']=='done': break
        await asyncio.sleep(.01)
    assert (await c.get('/api/public')).json()['overdrive_agreement']['total']==6
    await c.post('/api/control',json={'action':'next'})
    for index,header in enumerate(headers):
        card=(await c.post('/api/card',headers=header,json={'account':'<script>Account</script>','industry':'technology','owner':'Seller Name','target_date':(date.today()+timedelta(days=14)).isoformat()})).json()
        pdf=await c.get('/card/'+card['id']+'.pdf'); assert pdf.content.startswith(b'%PDF')
        html=(await c.get('/card/'+card['id'])).text
        assert '&lt;script&gt;' in html and '<script>Account' not in html
    assert (await c.get('/api/public')).json()['commitment_count']==3
    assert len((await c.get('/export?kind=commitments')).text.splitlines())==4
    assert (await c.get('/export?kind=cards')).content.startswith(b'PK')
    from app.config import ROOT
    story=ROOT/'content/customer_story.md'
    assert (await c.get('/api/public')).json()['customer_story']==(story.read_text() if story.exists() else 'Customer story not loaded')

async def test_legacy_code_validation_and_no_sign_in_required(client):
    c,_=client
    assert (await c.post('/api/login',json={'pin':'wrong'})).json()=={'sign_in_required':False}
    assert (await c.post('/api/join',json={'name':'X','join_code':'wrong'})).status_code==400
    assert (await c.get('/api/facilitator')).status_code==200


async def test_replay_is_labeled_before_progress_and_adds_no_usage(client):
    from app.ai import replay
    c,app=client
    await c.post('/api/login',json={'pin':settings.facilitator_pin})
    state=(await c.post('/api/control',json={'action':'create','label':'REHEARSAL'})).json()
    result={'data':{'events':[{'explanation':'A supplier invoice arrives.','log_ids':['EML9001']}],'summary':'The invoice starts the incident.','summary_log_ids':['EML9001']},'model':'hero','cached':False}
    replay.save('invoice',result,[{'elapsed':.3,'data':{'agent':'email','status':'done'}}],state['session'])
    await c.post('/api/control',json={'action':'replay'})
    joined=(await c.post('/api/join',json={'name':'Replay QA','join_code':state['session']['join_code']})).json()
    header={'Authorization':'Bearer '+joined['token']}
    await c.post('/api/control',json={'action':'next'})
    await c.post('/api/pick',headers=header,json={'alert':'invoice'})
    await c.post('/api/control',json={'action':'next'})
    async def forbidden(*args,**kwargs):raise AssertionError('Replay called inference')
    for model in app.state.router.clients.values():model.complete=forbidden
    await c.post('/api/investigate',headers=header,json={})
    await asyncio.sleep(.02)
    current=(await c.get('/api/me',headers=header)).json()
    assert current['team']['investigation']['cached'] is True
    assert current['team']['investigation']['status']=='running'
    assert current['metrics'] is None
    await asyncio.sleep(.35)
    current=(await c.get('/api/me',headers=header)).json()
    assert current['team']['investigation']['status']=='done'
    assert current['investigations_completed']==0
    assert not [event for event in app.state.db.events(state['session']['id']) if event['type']=='usage']

async def test_public_grid_omits_full_agent_findings(client):
    c,app=client
    await c.post('/api/login',json={'pin':settings.facilitator_pin})
    state=(await c.post('/api/control',json={'action':'create','label':'REHEARSAL'})).json()
    joined=(await c.post('/api/join',json={'name':'Grid privacy QA','join_code':state['session']['join_code']})).json()
    record=app.state.db.get('team',joined['team_id'])
    record['agents']={'email':{'status':'done','model':'hero','finding':{'summary':'Detailed source finding','log_ids':['EML9001']},'query':'source query'}}
    app.state.db.put('team',record['id'],record)
    public=(await c.get('/api/public')).json()
    assert public['teams'][0]['agents']['email']=={'status':'done','model':'hero'}
    own=(await c.get('/api/me',headers={'Authorization':'Bearer '+joined['token']})).json()
    assert own['team']['agents']['email']['finding']['log_ids']==['EML9001']

async def test_welcome_and_explicit_facilitator_start(client):
    c,_=client
    page=await c.get('/')
    assert page.status_code==200 and 'Start experience' in page.text and 'No sign-in' in page.text
    assert settings.facilitator_pin not in page.text
    assert (await c.get('/static/brand/hp-logo-keyline.png')).headers['content-type']=='image/png'
    assert (await c.post('/api/control',json={'action':'start'})).status_code==200
    await c.post('/api/login',json={'pin':settings.facilitator_pin})
    prepared=(await c.post('/api/control',json={'action':'create','label':'REHEARSAL'})).json()
    assert prepared['session']['paused'] and not prepared['session']['started']
    assert prepared['join_url'].endswith('/play?start=1')
    assert (await c.get('/api/qr.png')).content.startswith(b'\x89PNG')
    started=(await c.post('/api/control',json={'action':'start'})).json()
    repeated=(await c.post('/api/control',json={'action':'start'})).json()
    assert started['session']['started'] and not started['session']['paused']
    assert repeated['session']['deadline']==started['session']['deadline']
    assert repeated['session']['phase']==1
