"""Deterministic bounded retrieval. No hidden key or twist enters an early prompt."""
import json
import math
import re
from datetime import datetime
from functools import lru_cache
from app.config import ROOT

SOURCES={'identity':{'idp'},'email':{'email'},'endpoint':{'endpoint','proxy_dns'},'data_access':{'file'}}
START_ORDER={'identity':['identity','data_access','endpoint','email'], 'invoice':['email','endpoint','identity','data_access'], 'files':['data_access','identity','endpoint','email']}

def model_row(row):
    value={k:v for k,v in row.items() if k not in ('injected','routine')}
    if row.get('scheduled_window'):
        times=re.findall(r'(\d{2}):(\d{2})',row['scheduled_window'])
        if len(times)==2:
            clock=datetime.fromisoformat(row['timestamp'])
            minute=clock.hour*60+clock.minute
            start,end=[int(hour)*60+int(part) for hour,part in times]
            value['derived_within_scheduled_window']=start<=minute<=end
    if row.get('expected_src_ip'):
        value['derived_matches_expected_source']=row['src_ip']==row['expected_src_ip']
    if row.get('bytes',0)>=1000**3:
        value['size_note']=f"{math.floor(row['bytes']/1000**3*10)/10} GB, not TB; source bytes are authoritative"
    return value

@lru_cache(maxsize=1)
def logs():
    return {row['id']:row for row in json.loads((ROOT/'data/events.json').read_text())}

def search_logs(role, alert, twist=False, budget_chars=5500):
    sources=SOURCES[role]
    rows=[x for x in logs().values() if x['source'] in sources and (twist or not x.get('injected'))]
    # All alerts concern the same employee; entity, uncommon public IP and session link the sources.
    def anomaly(row):
        return (4*(row.get('user')=='m.brooks')
                + 5*(row.get('risk')=='new_network')
                + 5*(row.get('action') in {'attachment_open','browser_token_access','https_post','directory_enumeration','bulk_download'})
                + 3*('harb0rparts.example' in row.get('domain',''))
                + 2*(row.get('path','').startswith('/finance'))
                + (not row.get('src_ip','10.').startswith('10.'))
                + 10*any(key in row for key in ('risk','scheduled_window','change_ticket','travel_ticket','message_id','auth_method','artifact')))
    ranked=sorted(rows,key=lambda x:(anomaly(x),x['timestamp']),reverse=True)
    selected=[]; size=0
    for row in ranked:
        encoded=json.dumps(row)
        if size+len(encoded)>budget_chars or len(selected)>=8: break
        selected.append(model_row(row)); size+=len(encoded)
    return {'rows':sorted(selected,key=lambda x:(x['timestamp'],x['id'])), 'events_scanned':len(rows),
            'query':f'{role}: source and 36 hour window; m.brooks, session and network anomalies; starting alert {alert}'}

def evidence_rows(ids, twist=False):
    dataset=logs()
    return [model_row(dataset[x]) for x in ids if x in dataset and (twist or not dataset[x].get('injected'))]
