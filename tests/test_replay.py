import json
import pytest
from app.ai import replay

@pytest.fixture
def recording(tmp_path,monkeypatch):
    monkeypatch.setattr(replay,'CACHE',tmp_path)
    result={'data':{'events':[{'explanation':'A supplier invoice arrives.','log_ids':['EML9001']}],'summary':'The invoice begins the incident.','summary_log_ids':['EML9001']},'model':'hero','cached':False}
    events=[{'elapsed':.01,'data':{'agent':'email','status':'started'}},{'elapsed':.03,'data':{'agent':'email','status':'done'}}]
    session={'created':'2026-11-09T00:00:00+00:00','label':'REHEARSAL'}
    replay.save('invoice',result,events,session)
    return tmp_path/'invoice.json'

async def test_replay_preserves_timing_without_usage(recording,monkeypatch):
    pauses=[];events=[]
    async def sleep(delay):pauses.append(delay)
    async def emit(data):events.append(data)
    monkeypatch.setattr(replay.asyncio,'sleep',sleep)
    result=await replay.replay('invoice',emit)
    assert pauses==pytest.approx([.01,.02])
    assert result['cached'] is True
    assert all(e['cached'] for e in events)
    assert result['recorded_at']=='2026-11-09T00:00:00+00:00'

def test_bad_recordings_never_become_replay(recording):
    value=json.loads(recording.read_text());value['session_label']='LIVE';recording.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='recorded rehearsal'):replay.load('invoice')
    value['session_label']='REHEARSAL';value['events'][0]['data']['finding']={'summary':'Invented evidence','log_ids':['IDP9999']};recording.write_text(json.dumps(value))
    with pytest.raises(ValueError):replay.load('invoice')
