import asyncio
from datetime import date,timedelta
import pytest
from tests.test_end_to_end import client

async def wait_for(c,header,predicate):
    for _ in range(300):
        state=(await c.get('/api/me',headers=header)).json()
        if predicate(state):return state
        await asyncio.sleep(.01)
    raise AssertionError('Expected personal progress did not complete')

async def begin(c,nonce):
    response=await c.post('/api/experience/start',json={'client_id':nonce})
    assert response.status_code==200,response.text
    value=response.json()
    return value,{'Authorization':'Bearer '+value['token']}

async def act(c,header,action,phase=None,reveal=None):
    body={'action':action}
    if phase is not None:body['expected_phase']=phase
    if reveal is not None:body['expected_reveal']=reveal
    response=await c.post('/api/experience/control',headers=header,json=body)
    assert response.status_code==200,response.text
    return response

async def test_open_access_and_idempotent_anonymous_start(client):
    c,_=client
    assert (await c.get('/api/facilitator')).status_code==200
    assert (await c.get('/export')).status_code==200
    assert (await c.post('/api/login',json={'pin':'anything'})).json()=={'sign_in_required':False}
    page=(await c.get('/')).text
    assert 'Start experience' in page and 'Run the workshop' not in page
    control=(await c.get('/facilitator')).text
    assert 'id="login"' not in control and 'type="password"' not in control
    first,header=await begin(c,'individual-browser-one')
    repeated,_=await begin(c,'individual-browser-one')
    assert first['participant_id']==repeated['participant_id']
    assert first['token']==repeated['token']
    assert first['state']['session']['phase']==2 and first['state']['session']['self_paced']
    assert (await c.get('/api/public')).json()['joined']==1
    resumed=(await c.post('/api/experience/start',headers=header,json={})).json()
    assert resumed['participant_id']==first['participant_id']

async def test_individual_phases_and_twist_are_isolated_from_room_and_other_people(client):
    c,_=client
    _,a=await begin(c,'independent-person-a')
    _,b=await begin(c,'independent-person-b')
    for _ in range(3):await c.post('/api/control',json={'action':'next'})
    await c.post('/api/control',json={'action':'twist'})
    assert (await c.get('/api/me',headers=a)).json()['session']['phase']==2
    assert (await c.get('/api/logs/FIL9003',headers=a)).status_code==404
    await c.post('/api/pick',headers=a,json={'alert':'invoice'})
    await act(c,a,'next',2)
    await act(c,a,'next',2)  # A retried click cannot skip another step.
    assert (await c.get('/api/me',headers=a)).json()['session']['phase']==3
    assert (await c.get('/api/me',headers=b)).json()['session']['phase']==2
    assert (await c.post('/api/investigate',headers=a,json={})).status_code==200
    await wait_for(c,a,lambda s:s['team']['investigation']['status']=='done')
    assert (await c.post('/api/decision',headers=a,json={'decision':'escalate','evidence':['twist']})).status_code==409
    await act(c,a,'twist',3)
    assert (await c.get('/api/logs/FIL9003',headers=a)).status_code==200
    assert (await c.get('/api/logs/FIL9003',headers=b)).status_code==404
    assert (await c.get('/api/me',headers=b)).json().get('twist') is None
    assert (await c.post('/api/card',headers=a,json={'account':'Too soon','industry':'technology','owner':'Seller','target_date':(date.today()+timedelta(days=14)).isoformat()})).status_code==409

async def test_three_individuals_complete_without_presenter_actions(client):
    c,app=client
    people=[await begin(c,'self-paced-person-'+str(i)) for i in range(3)]
    for index,(_,header) in enumerate(people):
        await c.post('/api/pick',headers=header,json={'alert':['identity','invoice','files'][index]})
        await act(c,header,'next',2)
        await c.post('/api/investigate',headers=header,json={})
    for _,header in people:
        state=await wait_for(c,header,lambda s:s['team']['investigation']['status']=='done')
        assert not state['team']['investigation']['cached']
        await act(c,header,'twist',3)
        response=await c.post('/api/decision',headers=header,json={'decision':'escalate','evidence':['token','session','twist']})
        assert response.status_code==200
        state=await wait_for(c,header,lambda s:len(s['team'].get('reviews',[]))==2)
        await act(c,header,'next',3)
        assert (await c.get('/api/me',headers=header)).json()['customer_story']=='Customer story not loaded'
        assert (await c.post('/api/experience/control',headers=header,json={'action':'next','expected_phase':4})).status_code==409
        await act(c,header,'overdrive',4)
        await wait_for(c,header,lambda s:s['session']['overdrive']=='done')
        for beat in range(6):await act(c,header,'reveal',4,beat)
        await act(c,header,'next',4)
        result=(await c.post('/api/card',headers=header,json={'account':'Fictional individual account','industry':'technology','owner':'Individual Seller','target_date':(date.today()+timedelta(days=14)).isoformat()})).json()
        assert (await c.get('/card/'+result['id']+'.pdf')).content.startswith(b'%PDF')
    final=(await c.get('/api/public')).json()
    assert final['served']==3 and final['investigations_completed']==3 and final['commitment_count']==3
    assert final['session']['phase']==3  # Room projection never paced the individuals.
    _,late=await begin(c,'late-individual-person')
    assert (await c.get('/api/me',headers=late)).json()['session']['phase']==2

async def test_individual_replay_requires_no_model_or_presenter_advancement(client):
    from app.ai import replay
    c,app=client
    result={'data':{'events':[{'explanation':'A supplier invoice arrives.','log_ids':['EML9001']}],'summary':'The invoice starts the incident.','summary_log_ids':['EML9001']},'model':'hero','cached':False}
    replay.save('invoice',result,[{'elapsed':.02,'data':{'agent':'email','status':'done'}}],{'label':'REHEARSAL','created':'2026-11-09T00:00:00+00:00'})
    await c.post('/api/control',json={'action':'replay'})
    async def forbidden(*args,**kwargs):raise AssertionError('Replay called inference')
    for model in app.state.router.clients.values():model.complete=forbidden
    _,header=await begin(c,'individual-replay-browser')
    await c.post('/api/pick',headers=header,json={'alert':'invoice'});await act(c,header,'next',2)
    await c.post('/api/investigate',headers=header,json={})
    state=await wait_for(c,header,lambda s:s['team']['investigation']['status']=='done')
    assert state['team']['investigation']['cached'] and state['metrics'] is None
    await act(c,header,'twist',3)
    await c.post('/api/decision',headers=header,json={'decision':'escalate','evidence':['token','session','twist']})
    await act(c,header,'next',3)
    assert (await c.get('/api/me',headers=header)).json()['session']['phase']==4
    assert (await c.get('/api/public')).json()['investigations_completed']==0
    assert not [e for e in app.state.db.events(state['session']['id']) if e['type']=='usage']


def test_individual_response_time_uses_own_event_release():
    from app.participants import response_seconds
    room={'twist_at':100}
    person={'mode':'individual','joined_at':200,'decision_at':340,'progress':{'twist_at':300}}
    assert response_seconds(room,person)==40
    assert response_seconds(room,{'joined_at':50,'decision_at':150})==50

async def test_restart_preserves_personal_progress_and_marks_extra_review_retryable(client):
    from app.main import create_app
    c,app=client
    value,header=await begin(c,'individual-restart-person')
    person=app.state.db.get('team',value['participant_id'])
    person['progress'].update(phase=4,reveal=2,twist=True,overdrive='running')
    person['pick']='invoice'
    app.state.db.put('team',person['id'],person)
    restarted=create_app(app.state.db,app.state.router)
    import httpx
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=restarted),base_url='http://127.0.0.1:8080') as recovered:
        result=(await recovered.get('/api/me',headers=header)).json()
    assert result['team']['id']==person['id'] and result['team']['pick']=='invoice'
    assert result['session']['phase']==4 and result['session']['reveal']==2
    assert result['session']['overdrive']=='interrupted'
