import asyncio
import json
import secrets
from pathlib import Path
import pytest
import httpx
import subprocess
from revamp.engine import Engine,GameError
from revamp import settings
from revamp.server import create_app

@pytest.fixture
def game(tmp_path):
    e=Engine(tmp_path)
    yield e
    e.db.close()

def test_idempotent_personal_sessions_and_durable_resume(game,tmp_path):
    a,token=game.experience('a'*32,guided=False)
    b,other=game.experience('b'*32,guided=False)
    assert a['code']!=b['code'] and token!=other
    assert game.experience('a'*32,guided=False)[1]==token
    game.experience_control(a,'start','manufacturing');game.experience_control(a,'next')
    game.action(a,'1','analyze')
    restored=Engine(tmp_path)
    try:
        result,same=restored.experience('a'*32)
        assert same==token and result['industry']=='manufacturing'
        assert result['teams']['1']['progress']==['analyze']
        assert restored.experience('b'*32)[0]['phase']=='lobby'
    finally:restored.db.close()

def test_reset_restart_isolation_and_no_skip(game):
    a,ta=game.experience('a'*32,guided=False);b,tb=game.experience('b'*32,guided=False)
    for r in [a,b]:game.experience_control(r,'start');game.experience_control(r,'next')
    game.action(b,'1','analyze');before=b['teams']['1']['score']
    with pytest.raises(GameError):game.experience_control(a,'next')
    a['card']={'account':'Private account'}
    game.experience_control(a,'restart')
    assert a['phase']=='wave' and a['story']['stage']=='cloud_check' and a['card']=={} and a['teams']['1']['score']==0
    assert b['phase']=='wave' and b['teams']['1']['score']==before and b['teams']['1']['progress']==['analyze']
    game.experience_control(a,'reset');assert a['phase']=='lobby'
    assert game.owned_experience(ta)['code']==a['code']
    with pytest.raises(GameError):game.owned_experience(tb+'wrong')

@pytest.mark.asyncio
async def test_personal_lesson_cards_wait_for_user(game):
    r,_=game.experience('c'*32,guided=False);game.experience_control(r,'start');r['remaining']=0
    task=asyncio.create_task(game.tick())
    try:
        await asyncio.sleep(.3);assert r['phase']=='briefing'
        game.experience_control(r,'next');r['remaining']=0
        await asyncio.sleep(.3);assert r['phase']=='translate'
        r['remaining']=0;await asyncio.sleep(.3);assert r['phase']=='translate'
    finally:
        task.cancel()
        await asyncio.gather(task,return_exceptions=True)

@pytest.mark.asyncio
async def test_single_entry_auth_and_card_boundaries(tmp_path,monkeypatch):
    monkeypatch.setattr(settings,'DATA',tmp_path)
    app=create_app();app.state.engine.agents=None
    async with app.router.lifespan_context(app), httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://127.0.0.1') as client:
        for path in ['/screen','/play','/station','/stations','/facilitator','/playbook']:
            response=await client.get(path,follow_redirects=False)
            assert response.status_code==307 and response.headers['location']=='/'
        assert 'experience.js' in (await client.get('/')).text
        qr=await client.get('/api/experience/share.png',params={'url':'http://127.0.0.1:8090/'})
        assert qr.status_code==200 and qr.content.startswith(b'\x89PNG')
        assert (await client.get('/api/experience/share.png',params={'url':'https://outside.example/'})).status_code==400
        result=(await client.post('/api/experience',json={'nonce':'x'*32})).json();token=result['token'];code=result['state']['code']
        auth={'Authorization':'Bearer '+token}
        assert (await client.post('/api/experience/control',json={'command':'start'})).status_code==400
        assert (await client.get('/api/experience/card.pdf',headers=auth)).status_code==400
        engine=app.state.engine;r=engine.room(code)
        for _ in range(8):engine.advance(r)
        assert r['phase']=='debrief'
        private='PRIVATE_ACCOUNT_42'
        response=await client.post('/api/experience/card',headers=auth,json={'account':private,'next_step':'Discuss the next step <script>bad</script>'})
        assert response.status_code==200
        assert private not in (await client.get('/api/rooms/'+code)).text
        assert private not in json.dumps(r['bubbles'])
        pdf=await client.get('/api/experience/card.pdf',headers=auth)
        assert pdf.status_code==200 and pdf.content.startswith(b'%PDF')
        assert 'HP-Account-Action-Card.pdf' in pdf.headers['content-disposition']
        file=tmp_path/'card.pdf';file.write_bytes(pdf.content)
        annotations=subprocess.check_output(['pdfinfo','-url',str(file)],text=True)
        for url in json.loads((settings.ROOT/'config/hp_resources.json').read_text())['resources']:
            assert url['url'] in annotations
        assert (await client.post('/api/experience/control',headers=auth,json={'command':'reset'})).json()['phase']=='lobby'

@pytest.mark.asyncio
async def test_shared_analysis_survives_owner_reset_without_mixing_results(game):
    from revamp.ai import LocalAgents
    a,ta=game.experience('a'*32,guided=False);b,tb=game.experience('b'*32,guided=False)
    agents=LocalAgents(game.emit,game.data);await agents.http.aclose()
    entered=asyncio.Event();release=asyncio.Event();requests=[]
    async def respond(request):
        requests.append(request);entered.set();await release.wait()
        chunks=[{'choices':[{'delta':{'content':'Review the changed bank details with a trusted vendor contact.'}}]}, {'choices':[],'usage':{'completion_tokens':12}}]
        return httpx.Response(200,text=''.join('data: '+json.dumps(x)+'\n\n' for x in chunks)+'data: [DONE]\n\n',headers={'Content-Type':'text/event-stream'})
    agents.http=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    first=asyncio.create_task(agents.bubble(a,'SHERLOCK',1,a['generation']))
    await entered.wait()
    second=asyncio.create_task(agents.bubble(b,'SHERLOCK',1,b['generation']))
    await asyncio.sleep(.05)
    game.experience_control(a,'reset');release.set()
    await asyncio.gather(first,second)
    assert len(requests)==1
    assert a['phase']=='lobby' and a['bubbles']=={}
    assert b['bubbles']['SHERLOCK']['status']=='success' and b['bubbles']['SHERLOCK']['shared']
    assert agents.tokens==12 and b['power']['tokens']==0
    assert b['teams']['1']['progress']==[] and a['teams']['1']['progress']==[]
    await agents.close()
