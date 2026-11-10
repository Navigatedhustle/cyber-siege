#!/usr/bin/env python3
"""Real no-sign-in participant rehearsal; no presenter advances personal progress."""
import argparse
import asyncio
import json
import sys
import time
import uuid
from datetime import date,timedelta,datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from app.config import settings,ROOT
from scripts.rehearse import phone_updates

async def run(count):
    if settings.app_port==8080:raise SystemExit('Use an isolated review app, for example APP_PORT=8088')
    started=time.monotonic();report={'started_at':datetime.now(timezone.utc).isoformat(),'label':'REHEARSAL','participants':count,'health_samples':[]}
    async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{settings.app_port}',trust_env=False,timeout=120,limits=httpx.Limits(max_connections=200,max_keepalive_connections=100)) as c:
        async def request(method,path,**kwargs):
            response=await c.request(method,path,**kwargs);response.raise_for_status();return response.json()
        state=await request('POST','/api/control',json={'action':'create','label':'REHEARSAL'});report['session_id']=state['session']['id']
        people=[]
        for _ in range(count):
            value=await request('POST','/api/experience/start',json={'client_id':str(uuid.uuid4())});people.append({'Authorization':'Bearer '+value['token']})
        async def action(header,kind,phase=None,beat=None):
            payload={'action':kind}
            if phase is not None:payload['expected_phase']=phase
            if beat is not None:payload['expected_reveal']=beat
            return await request('POST','/api/experience/control',headers=header,json=payload)
        async with phone_updates(c,people) as sse:
            await asyncio.gather(*(request('POST','/api/pick',headers=h,json={'alert':['identity','invoice','files'][i%3]}) for i,h in enumerate(people)))
            await asyncio.gather(*(action(h,'next',2) for h in people));launch=time.monotonic()
            await asyncio.gather(*(request('POST','/api/investigate',headers=h,json={}) for h in people))
            while time.monotonic()-launch<240:
                state=await request('GET','/api/facilitator');report['health_samples'].append({k:v['healthy'] for k,v in state['model_health'].items()})
                if all(t.get('investigation',{}).get('status') in ('done','failed') for t in state['teams']):break
                await asyncio.sleep(.5)
            report['investigation_wall_seconds']=time.monotonic()-launch
            report['investigations']=[{'status':t.get('investigation',{}).get('status'),'cached':t.get('investigation',{}).get('cached'),'seconds':t.get('investigation',{}).get('duration_seconds')} for t in state['teams']]
            if not all(r['status']=='done' for r in report['investigations']):raise RuntimeError('An investigation did not finish')
            await asyncio.gather(*(action(h,'twist',3) for h in people))
            await asyncio.gather(*(request('POST','/api/decision',headers=h,json={'decision':'escalate','evidence':['token','session','twist']}) for h in people))
            review_started=time.monotonic()
            while time.monotonic()-review_started<180:
                state=await request('GET','/api/facilitator')
                report['health_samples'].append({k:v['healthy'] for k,v in state['model_health'].items()})
                if all(t.get('reviews') for t in state['teams']):break
                await asyncio.sleep(.5)
            report['independent_reviews']=sum(len({r['model'] for r in t.get('reviews',[]) if not r.get('error')}) for t in state['teams'])
            await asyncio.gather(*(action(h,'next',3) for h in people))
            await asyncio.gather(*(action(h,'overdrive',4) for h in people));extra_started=time.monotonic()
            while time.monotonic()-extra_started<180:
                state=await request('GET','/api/facilitator')
                report['health_samples'].append({k:v['healthy'] for k,v in state['model_health'].items()})
                if all(t['progress']['overdrive']=='done' for t in state['teams']):break
                await asyncio.sleep(.5)
            report['extra_review_seconds']=time.monotonic()-extra_started
            report['extra_reviews']=sum(len([r for r in t.get('overdrive_reviews',[]) if not r.get('error')]) for t in state['teams'])
            for beat in range(6):await asyncio.gather(*(action(h,'reveal',4,beat) for h in people))
            await asyncio.gather(*(action(h,'next',4) for h in people))
            await asyncio.gather(*(request('POST','/api/card',headers=h,json={'account':f'Fictional individual account {i+1}','industry':'technology','owner':f'Individual seller {i+1}','target_date':(date.today()+timedelta(days=14)).isoformat()}) for i,h in enumerate(people)))
            final=await request('GET','/api/facilitator');report.update(commitments=final['commitment_count'],completed=final['investigations_completed'],connected_phones=final['connected_phones'],sse=dict(sse),elapsed_seconds=time.monotonic()-started,peak_5s=final['metrics']['peak_5s'],peak_at=final['metrics']['peak_at'])
            report['max_investigation_seconds']=max(r['seconds'] for r in report['investigations'])
            report['passed']=len(report['investigations'])==count and all(not r['cached'] for r in report['investigations']) and report['max_investigation_seconds']<75 and report['connected_phones']==count and report['commitments']==count and report['independent_reviews']==count*2 and report['extra_reviews']==count*2 and all(all(sample.values()) for sample in report['health_samples']) and report['elapsed_seconds']<1200
    path=ROOT/f'runtime/individual-load-{count}.json';path.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--participants',type=int,default=45);args=parser.parse_args();asyncio.run(run(args.participants))
