"""Required game/security invariants, independent of generated model wording."""
import asyncio
import copy
import json
from pathlib import Path
import httpx
import pytest
from revamp.engine import Engine, GameError, nickname
from revamp.ai import LocalAgents
from revamp import settings

@pytest.fixture
def game(tmp_path):
    engine=Engine(tmp_path)
    yield engine
    engine.db.close()

def test_complete_three_waves_and_pause(game):
    room=game.create('healthcare',8)
    tokens=[game.join(room['code'],'Seller',str(i+1))[0] for i in range(8)]
    game.control(room,'start');game.advance(room)
    assert room['wave']==1
    for tid in room['teams']:
        game.action(room,tid,'analyze');game.action(room,tid,'verify')
    assert room['phase']=='translate'
    game.advance(room)
    game.control(room,'pause')
    with pytest.raises(GameError):game.action(room,'1','SCOUT',0)
    game.control(room,'pause')
    for tid in room['teams']:
        for b in range(6):game.action(room,tid,'SCOUT',b)
    assert room['phase']=='translate'
    game.advance(room)
    before=room['teams']['1']['score']
    game.action(room,'1','PATCH',0)
    assert room['teams']['1']['score']==before
    for tid in room['teams']:
        for i,r in enumerate(['SCOUT','SHERLOCK','SHIELD','PATCH','SCRIBE']):game.action(room,tid,r,i)
    game.advance(room)
    assert room['phase']=='debrief'
    assert all(t['score']==1625 for t in room['teams'].values())
    assert all(len(t['times'])==3 for t in room['teams'].values())
    # Credentials never enter a snapshot, including facilitator snapshots.
    public=json.dumps(game.public(room,admin=True))
    assert all(t not in public for t in tokens)

def test_wrong_payment_recovery_replay_no_score_farming(game):
    room=game.create(teams=2);game.advance(room);game.advance(room)
    game.action(room,'1','pay');game.action(room,'1','analyze');game.action(room,'1','verify')
    assert room['teams']['1']['risk']==48000
    assert room['teams']['1']['completed']
    game.control(room,'replay')
    assert room['teams']['1']['score']==0
    assert room['teams']['1']['risk']==0
    assert not room['teams']['1']['progress']

def test_reconnect_moderation_and_durable_progress(game,tmp_path):
    room=game.create('manufacturing',8)
    token,player=game.join(room['code'],'<script>alert(1)</script>','3')
    assert '<' not in player['name']
    assert nickname('FUCK')=='Friendly seller'
    game.control(room,'hide',player['id'])
    game.advance(room);game.advance(room);game.action(room,'3','analyze')
    second,p=game.join(room['code'],'ignored','1',token=token)
    assert second==token and p['team']=='3'
    assert game.public(room)['players'][0]['name']=='Seller'
    other=Engine(tmp_path)
    try:
        restored=other.room(room['code'])
        assert restored['teams']['3']['progress']==['analyze']
        assert restored['paused'] and not restored['players'][token]['connected']
    finally:other.db.close()

def test_validation_rejects_invalid_inputs(game):
    room=game.create();game.advance(room);game.advance(room);game.advance(room);game.advance(room)
    for building in [-1,6,True,1.5,'0']:
        with pytest.raises(GameError):game.action(room,'1','SCOUT',building)
    with pytest.raises(GameError):game.control(room,'autopilot',{'team':'9','enabled':True})
    with pytest.raises(GameError):game.control(room,'industry','unknown_industry')
    with pytest.raises(ValueError):settings.private_url('https://public.example.com')
    with pytest.raises(ValueError):settings.private_url('http://0.0.0.0:8090')

@pytest.mark.asyncio
async def test_model_failure_falls_back_and_logs(game,monkeypatch):
    room=game.create();agents=LocalAgents(game.emit,game.data)
    async def fail(request):raise httpx.ConnectError('offline')
    await agents.http.aclose()
    agents.http=httpx.AsyncClient(transport=httpx.MockTransport(fail))
    await agents.bubble(room,'SHERLOCK',1,room['generation'])
    assert room['bubbles']['SHERLOCK']['scripted']
    assert len(room['bubbles']['SHERLOCK']['text'].split())<=25
    assert room['power']['active']==0
    assert agents.fallbacks[0]['reason']=='ConnectError'
    assert (game.data/'fallbacks.jsonl').exists()
    assert 'scripted' not in game.public(room)['bubbles']['SHERLOCK']
    assert game.public(room,admin=True)['bubbles']['SHERLOCK']['scripted']
    await agents.close()

@pytest.mark.asyncio
async def test_model_deadline_includes_queue_time(game):
    room=game.create();agents=LocalAgents(game.emit,game.data)
    # A held queue slot exercises the real 7.6-second total deadline without touching any model.
    agents.semaphore=asyncio.Semaphore(0)
    started=asyncio.get_running_loop().time()
    await agents.bubble(room,'SCOUT',2,room['generation'])
    elapsed=asyncio.get_running_loop().time()-started
    assert 7.5<=elapsed<8
    assert room['bubbles']['SCOUT']['scripted']
    assert agents.active==0 and room['power']['active']==0
    await agents.close()

def test_boss_isolation_and_restore_have_business_effect(game):
    room=game.create();game.advance(room)
    game.start_wave(room,3)
    for i,r in enumerate(['SCOUT','SHERLOCK','SHIELD']):game.action(room,'1',r,i)
    assert room['teams']['1']['isolated']
    game.action(room,'1','PATCH',3)
    assert all(b=='restored' for b in room['teams']['1']['buildings'])
    assert not room['teams']['1']['completed']
    game.action(room,'1','SCRIBE',4)
    assert room['teams']['1']['completed']

def test_all_industry_buildings_and_story_approval(game,tmp_path,monkeypatch):
    from revamp.content import INDUSTRIES,INDUSTRY_ICONS
    from revamp import playbook
    for industry,buildings in INDUSTRIES.items():
        assert len(buildings)==6 and len(INDUSTRY_ICONS[industry])==6
        assert game.create(industry)['industry']==industry
    path=tmp_path/'stories.local.json';monkeypatch.setattr(playbook,'STORY_PATH',path)
    path.write_text(json.dumps({'stories':[{'approved':False,'text':'PRIVATE','approval_reference':'x'}]}))
    assert playbook.approved_story() is None
    path.write_text(json.dumps({'stories':[{'approved':True,'text':'PRIVATE'}]}))
    assert playbook.approved_story() is None
    path.write_text(json.dumps({'stories':[{'approved':True,'text':'A'*500,'approval_reference':'Approved test'}]}))
    assert len(playbook.approved_story()['text'])==420

@pytest.mark.asyncio
async def test_payload_counter_tracks_http_exchange_and_blocks_remote(game):
    room=game.create();agents=LocalAgents(game.emit,game.data)
    hooks=agents.http.event_hooks
    await agents.http.aclose()
    def respond(request):
        chunks=[{'choices':[{'delta':{'content':'Review changed bank details with a trusted vendor contact.'}}]},
                {'usage':{'completion_tokens':10},'choices':[]}]
        text=''.join('data: '+json.dumps(c)+'\n\n' for c in chunks)+'data: [DONE]\n\n'
        return httpx.Response(200,text=text,headers={'Content-Type':'text/event-stream'})
    agents.http=httpx.AsyncClient(transport=httpx.MockTransport(respond),event_hooks=hooks)
    await agents.bubble(room,'SHERLOCK',1,room['generation'])
    assert room['power']['local_bytes']>0 and room['power']['cloud_bytes']==0
    assert room['power']['tokens']==10
    assert not room['bubbles']['SHERLOCK']['scripted']
    with pytest.raises(ValueError):await agents.check_target(httpx.Request('POST','https://cloud.example.test'))
    await agents.close()
