from datetime import date,timedelta
from app.cards import templates,build_card,HYPOTHESIS,has_dash,PROSE_FIELDS
from app.metrics import TokenWindow,parse_counter
from app.pdf import render_pdf

def test_all_templates_and_rendered_cards_are_grounded():
    assert len(templates())==10
    team={'session_id':'test','id':'1','name':'team'}
    for key,t in templates().items():
        assert t['status'] in ('draft','approved')
        card=build_card(team,'<script>Account</script>',key,'Seller',(date.today()+timedelta(days=14)).isoformat())
        assert card['hypothesis']==HYPOTHESIS
        for field in PROSE_FIELDS:
            assert card['prose'][field]==t[field]
            assert not has_dash(str(card['prose'][field]))
    assert has_dash('some\u2011text')
    assert has_dash('some-text')
    assert render_pdf(card).startswith(b'%PDF')

def test_measured_windows_and_peak():
    w=TokenWindow(); w.add(10,10); w.add(11,20)
    assert w.rates(11.5)['tps_1s']==20
    assert w.rates(11.5)['tps_5s']==6
    assert w.rates(20)['tps_5s']==0
    assert w.peak==6
    assert w.peak_at==11.5
    assert parse_counter('# hi\nvllm:generation_tokens_total{model="test"} 123\n')==('vllm:generation_tokens_total',123)
    assert parse_counter('anything 9')==(None,None)

async def test_per_model_sum_session_isolation_and_peak_correction(tmp_path,monkeypatch):
    from types import SimpleNamespace
    from app.metrics import Telemetry
    from app.db import Database
    import app.metrics as metrics
    now=[100.0]
    monkeypatch.setattr(metrics.time,'time',lambda:now[0])
    telemetry=Telemetry(Database(tmp_path/'metrics.db'))
    class Response:
        is_success=True
        text='vllm:generation_tokens_total 0'
    response=Response()
    class Client:
        async def get(self,*args,**kwargs):return response
    router=SimpleNamespace(config={k:{'metrics_url':'http://127.0.0.1:8000/metrics','name':k,'serving_stack':'test'} for k in ['hero','challenger']},status={k:{'healthy':True,'active':1} for k in ['hero','challenger']},clients={k:SimpleNamespace(http=Client()) for k in ['hero','challenger']})
    gpu=SimpleNamespace(sample=lambda:None)
    session={'id':'s','label':'LIVE','phase':3,'overdrive':'idle'}
    await telemetry.sample(session,router,gpu)
    now[0]=101;response.text='vllm:generation_tokens_total 1000'
    sample=await telemetry.sample(session,router,gpu)
    assert sample['total']['tps_5s']==400
    # Other traffic was visible on a busy global server. Once streams settle the source changes.
    now[0]=102
    for value in router.status.values():value['active']=0
    sample=await telemetry.sample(session,router,gpu)
    assert sample['peak_5s']==0
    assert all(row['source']=='app streamed usage' for row in sample['models'].values())
    telemetry.record('hero',50,session,{})
    telemetry.record('challenger',25,session,{})
    sample=await telemetry.sample(session,router,gpu)
    assert sample['total']['tps_5s']==15
    assert sample['total']['total_tokens']==75
    assert sample['peak_5s']==15
    other={**session,'id':'other','label':'REHEARSAL'}
    assert (await telemetry.sample(other,router,gpu))['total']['total_tokens']==0

async def test_app_usage_source_never_scrapes_unusable_server_metrics(tmp_path):
    from types import SimpleNamespace
    from app.metrics import Telemetry
    from app.db import Database
    class Forbidden:
        async def get(self,*args,**kwargs):raise AssertionError('Unsupported metrics endpoint was scraped')
    router=SimpleNamespace(config={'hero':{'metrics_source':'app_usage','metrics_url':'http://127.0.0.1:8000/metrics','name':'Hero','serving_stack':'Infinity'}},status={'hero':{'healthy':True,'active':0}},clients={'hero':SimpleNamespace(http=Forbidden())})
    session={'id':'s','label':'LIVE','phase':3,'overdrive':'idle'}
    telemetry=Telemetry(Database(tmp_path/'no-scrape.db'));telemetry.record('hero',50,session,{})
    sample=await telemetry.sample(session,router,SimpleNamespace(sample=lambda:None))
    assert sample['models']['hero']['source']=='app streamed usage'
    assert sample['total']['total_tokens']==50
