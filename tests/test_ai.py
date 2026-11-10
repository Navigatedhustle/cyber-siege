import asyncio
import pytest
from app.ai.validate import validate_ids
from app.ai.schemas import SpecialistResult
from app.ai.router import ModelRouter, ModelUnavailable
from app.ai.retrieval import search_logs

def test_unknown_and_hidden_citations_rejected():
    with pytest.raises(ValueError): validate_ids({'findings':[{'log_ids':['FAKE1']}]},{'IDP9001'})
    for role in ('identity','email','endpoint','data_access'):
        result=search_logs(role,'invoice')
        assert 'FIL9003' not in {x['id'] for x in result['rows']}
        assert result['events_scanned']>=1200

async def test_router_mapping_caps_and_fallback():
    router=ModelRouter()
    for row in router.status.values(): row.update(healthy=True,qualified=True)
    router.qualified=lambda key:True
    assert router.route('identity')=='hero'
    assert router.route('twist_check','challenger')=='challenger'
    router.status['challenger']['healthy']=False
    assert router.route('twist_check','challenger')=='hero'
    active=0; peak=0
    async def complete(*args,**kwargs):
        nonlocal active,peak
        active+=1; peak=max(peak,active)
        await asyncio.sleep(.005)
        active-=1
        return SpecialistResult(findings=[{'summary':'Evidence','log_ids':['IDP9001'],'confidence':'high'}],entities=[]),{'usage':{'completion_tokens':5}}
    router.clients['hero'].complete=complete
    router.caps['hero']=asyncio.Semaphore(2)
    results=await asyncio.gather(*(router.call('identity',{},SpecialistResult,{'IDP9001'},rehearsal=True) for _ in range(8)))
    assert peak==2
    assert all(x['model']=='hero' for x in results)
    router.status['hero']['healthy']=False
    with pytest.raises(ModelUnavailable): router.route('lead')
    await router.close()

async def test_cancelled_queue_and_http_retry():
    router=ModelRouter()
    for status in router.status.values():status.update(healthy=True,qualified=True)
    router.caps['hero']=asyncio.Semaphore(0)
    task=asyncio.create_task(router.call('identity',{},SpecialistResult,{'IDP9001'},rehearsal=True))
    await asyncio.sleep(.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    assert router.status['hero']['queue_depth']==0
    assert router.status['hero']['active']==0
    router.caps['hero']=asyncio.Semaphore(1)
    attempts=0
    async def retry(*args,**kwargs):
        nonlocal attempts
        attempts+=1
        if attempts==1:raise ConnectionError('transient')
        return SpecialistResult(findings=[{'summary':'Evidence','log_ids':['IDP9001'],'confidence':'high'}],entities=[]),{}
    router.clients['hero'].complete=retry
    result=await router.call('identity',{},SpecialistResult,{'IDP9001'},rehearsal=True)
    assert result['model']=='hero' and attempts==2
    await router.close()

def test_inline_invented_log_is_rejected():
    with pytest.raises(ValueError):
        validate_ids({'findings':[{'summary':'See IDP9999','log_ids':['IDP9001']}]},{'IDP9001'})

def test_numeric_claims_and_primary_event_order():
    with pytest.raises(ValueError,match='Numeric size'):
        validate_ids({'events':[{'explanation':'Downloaded 2.7TB.','log_ids':['FIL9002']}],'summary_log_ids':['FIL9002']},{'FIL9002'})
    result=validate_ids({'events':[{'explanation':'The same session downloads 428 files, about 2.7 GB.','log_ids':['FIL9002']},{'explanation':'An unusual sign in follows.','log_ids':['IDP9001','IDP9002']}],'summary_log_ids':['FIL9002']},{'FIL9002','IDP9001','IDP9002'})
    assert result['events'][0]['log_ids'][0]=='IDP9001'

async def test_citation_schema_is_restricted_to_supplied_evidence():
    import httpx,json
    router=ModelRouter();client=router.clients['challenger']
    captured={}
    async def respond(request):
        captured.update(json.loads(request.content))
        value={'findings':[{'summary':'The sign in is unusual.','log_ids':['IDP9001'],'confidence':'high'}],'entities':[]}
        data='data: '+json.dumps({'choices':[{'delta':{'content':json.dumps(value)}}],'usage':{'completion_tokens':10}})+'\n\ndata: [DONE]\n\n'
        return httpx.Response(200,text=data)
    await client.http.aclose();client.http=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    result,_=await client.complete('identity',{},SpecialistResult,lambda *a:None,allowed_ids={'IDP9001'})
    schema=captured['response_format']['json_schema']['schema']
    assert schema['$defs']['Finding']['properties']['log_ids']['items']['enum']==['IDP9001']
    assert result.findings[0].log_ids==['IDP9001']
    await router.close()

def test_backup_window_annotations_and_contradiction_guard():
    from app.ai.retrieval import evidence_rows
    rows=evidence_rows(['FIL9003','FIL9005'],True)
    assert rows[0]['derived_within_scheduled_window'] is False
    assert rows[0]['derived_matches_expected_source'] is False
    assert rows[1]['derived_within_scheduled_window'] is True
    with pytest.raises(ValueError,match='Backup timing'):
        validate_ids({'explanation':'Service account accessed the files during the backup window.','log_ids':['FIL9003','FIL9005']},{'FIL9003','FIL9005'})
    validate_ids({'explanation':'A legitimate backup runs normally, but the new access was outside its window.','log_ids':['FIL9003','FIL9005']},{'FIL9003','FIL9005'})

async def test_changed_model_workload_requires_new_gate(tmp_path):
    import json
    router=ModelRouter()
    path=tmp_path/'gate.json'
    router.config['hero']['gate_file']=str(path)
    path.write_text(json.dumps({'passed':True,'model_id':router.config['hero']['model_id'],'config':dict(router.config['hero'])}))
    assert router.qualified('hero')
    router.config['hero']['max_tokens']+=1
    assert not router.qualified('hero')
    await router.close()

async def test_one_slow_probe_does_not_interrupt_healthy_inference():
    import httpx
    router=ModelRouter();fail=[False]
    async def respond(request):
        if fail[0]:raise httpx.ReadTimeout('temporary metadata stall')
        return httpx.Response(200,json={'data':[{'id':router.config['hero']['model_id']}]})
    await router.clients['hero'].health_http.aclose()
    router.clients['hero'].health_http=httpx.AsyncClient(transport=httpx.MockTransport(respond))
    async def no_challenger(request):return httpx.Response(503)
    await router.clients['challenger'].health_http.aclose()
    router.clients['challenger'].health_http=httpx.AsyncClient(transport=httpx.MockTransport(no_challenger))
    await router.probe();assert router.status['hero']['healthy']
    fail[0]=True
    await router.probe();assert router.status['hero']['healthy'] and router.status['hero']['degraded']
    await router.probe();assert router.status['hero']['healthy']
    await router.probe();assert not router.status['hero']['healthy']
    fail[0]=False
    await router.probe();assert router.status['hero']['healthy'] and not router.status['hero']['degraded']
    await router.close()

async def test_http_health_cannot_clear_failed_inference_readiness():
    import httpx
    router=ModelRouter()
    for status in router.status.values():status.update(healthy=True,qualified=True)
    async def fail(*args,**kwargs):raise httpx.ReadTimeout('inference stalled')
    router.clients['hero'].complete=fail
    with pytest.raises(httpx.ReadTimeout):await router.call('identity',{},SpecialistResult,{'IDP9001'},rehearsal=True)
    assert router.status['hero']['readiness_blocked'] and not router.status['hero']['healthy']
    async def healthy(request):return httpx.Response(200,json={'data':[{'id':router.config['hero']['model_id']}]})
    for model in router.clients.values():
        await model.health_http.aclose();model.health_http=httpx.AsyncClient(transport=httpx.MockTransport(healthy))
    await router.probe()
    assert not router.status['hero']['healthy']
    await router.close()

@pytest.mark.parametrize('problem',['reversed_summary','unsupported_opening','missing_origin_citation'])
def test_timeline_rejects_unsupported_order_and_opening(problem):
    from app.ai.lead import validate_timeline
    value={'events':[{'explanation':'The supplier invoice arrives.','log_ids':['EML9001']},{'explanation':'The finance account signs in from a new network.','log_ids':['IDP9001','IDP9002']}],
           'summary':'The invoice led to stolen access and file activity.','summary_log_ids':['EML9001','IDP9001']}
    validate_timeline(value,{'EML9001','IDP9001'})
    if problem=='reversed_summary':value['summary']='The attack began with sign in, then a phishing email.'
    if problem=='unsupported_opening':value['events'][0]['explanation']='The employee opened the invoice attachment.'
    if problem=='missing_origin_citation':value['summary_log_ids']=['IDP9001']
    with pytest.raises(ValueError):validate_timeline(value,{'EML9001','IDP9001'})

def test_timeline_filters_standalone_comparisons_and_orders_summary_citations():
    from app.ai.lead import validate_timeline
    value={'events':[{'explanation':'An approved backup ran.','log_ids':['FIL9005']},{'explanation':'The invoice email arrives.','log_ids':['EML9001']},{'explanation':'The finance session signs in.','log_ids':['IDP9001']}],
           'summary':'The invoice led to stolen session access.','summary_log_ids':['IDP9001','EML9001','FIL9005']}
    validate_timeline(value,{'EML9001','IDP9001'})
    assert [event['log_ids'][0] for event in value['events']]==['EML9001','IDP9001']
    assert value['summary_log_ids']==['EML9001','IDP9001','FIL9005']

def test_later_event_can_reference_an_opening_already_cited_in_timeline():
    from app.ai.lead import validate_timeline
    value={'events':[{'explanation':'The invoice email arrives.','log_ids':['EML9001']},{'explanation':'The invoice attachment opens.','log_ids':['EDR9001']},{'explanation':'Browser token access follows opening the attachment.','log_ids':['EDR9002']}],
           'summary':'The invoice led to attachment opening and token access.','summary_log_ids':['EML9001','EDR9001','EDR9002']}
    validate_timeline(value,{'EML9001','EDR9001','EDR9002'})
