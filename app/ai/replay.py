"""Replay uses recorded rehearsal events and timings, never invented progress."""
import asyncio
import json
from datetime import datetime
from app.config import ROOT
from .validate import validate_ids
from .retrieval import logs
from .schemas import LeadResult
from .lead import material_event, validate_timeline

CACHE=ROOT/'data/cache'

def validate_recorded_timeline(value):
    ids={key for event in value['events'] for key in event['log_ids']}|set(value['summary_log_ids'])
    validate_timeline(value,{key for key in ids if material_event(logs()[key])})

def load(alert):
    path=CACHE/f'{alert}.json'
    if not path.exists(): return None
    value=json.loads(path.read_text())
    if value.get('session_label')!='REHEARSAL':raise ValueError('Replay source must be a recorded rehearsal')
    datetime.fromisoformat(value['recorded_at'])
    allowed={key for key,row in logs().items() if not row.get('injected')}
    value['result']['data']=validate_ids(LeadResult.model_validate(value['result']['data']),allowed)
    validate_recorded_timeline(value['result']['data'])
    previous=0
    for event in value['events']:
        if not isinstance(event['elapsed'],(int,float)) or event['elapsed']<previous:
            raise ValueError('Recording timings must be ordered and nonnegative')
        previous=event['elapsed']
        validate_ids(event['data'],allowed)
    return value

def save(alert,result,events,session):
    if session['label']!='REHEARSAL' or result.get('cached'):
        raise ValueError('Only successful real rehearsal inference may become a recording')
    validate_ids(LeadResult.model_validate(result['data']),{key for key,row in logs().items() if not row.get('injected')})
    validate_recorded_timeline(result['data'])
    CACHE.mkdir(parents=True,exist_ok=True)
    value={'alert':alert,'recorded_at':session['created'],'session_label':session['label'],'result':result,'events':events}
    (CACHE/f'{alert}.json').write_text(json.dumps(value,indent=2)+'\n')

async def replay(alert,emit):
    recording=load(alert)
    if not recording: raise RuntimeError('No rehearsal recording for this starting alert. Rehearse while hero is available.')
    previous=0
    for item in recording['events']:
        await asyncio.sleep(max(0,item['elapsed']-previous))
        previous=item['elapsed']
        await emit({**item['data'],'cached':True,'recorded_at':recording['recorded_at']})
    return {**recording['result'],'cached':True,'recorded_at':recording['recorded_at']}
