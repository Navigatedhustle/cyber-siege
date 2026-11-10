#!/usr/bin/env python3
"""Run a labeled rehearsal against the real app; recordings come from real models."""
import argparse
import asyncio
import json
import sys
import time
from contextlib import asynccontextmanager
from datetime import date,timedelta,datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from app.config import settings

@asynccontextmanager
async def phone_updates(client,phones):
    """Bots keep SSE open and restore snapshots as the phone UI does."""
    stats={'connected':0,'events':0,'snapshots':0}
    async def listen(headers):
        async with client.stream('GET','/api/events',headers={**headers,'X-Surface':'phone'},timeout=None) as response:
            response.raise_for_status();stats['connected']+=1
            async for line in response.aiter_lines():
                if not line.startswith('event:'):continue
                kind=line[6:].strip();stats['events']+=1
                if kind in ('state','team','progress','refresh'):
                    restored=await client.get('/api/me',headers=headers)
                    restored.raise_for_status();stats['snapshots']+=1
    tasks=[asyncio.create_task(listen(headers)) for headers in phones]
    try:
        for _ in range(100):
            if stats['connected']==len(phones):break
            if any(task.done() for task in tasks):
                await asyncio.gather(*(task for task in tasks if task.done()))
            await asyncio.sleep(.05)
        if stats['connected']!=len(phones):raise RuntimeError('Not all bot phone SSE connections opened')
        yield stats
    finally:
        for task in tasks:task.cancel()
        await asyncio.gather(*tasks,return_exceptions=True)

async def run(teams=15,combined=False):
    started=time.monotonic();report={'started_at':datetime.now(timezone.utc).isoformat(),'label':'REHEARSAL','teams':teams,'combined':combined,'health_samples':[]}
    async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{settings.app_port}',timeout=120,trust_env=False) as client:
        async def request(method,path,**kwargs):
            r=await client.request(method,path,**kwargs);r.raise_for_status();return r.json()
        await request('POST','/api/login',json={'pin':settings.facilitator_pin})
        async def control(action,**kwargs):return await request('POST','/api/control',json={'action':action,**kwargs})
        state=await control('create',label='REHEARSAL'); report['session_id']=state['session']['id']
        if not state['model_health']['hero']['healthy']:raise RuntimeError('Hero is not healthy; cannot record a real rehearsal')
        report['settings']={k:v for k,v in state['model_health'].items() if v['healthy']}
        phones=[]
        for index in range(teams):
            result=await request('POST','/api/join',json={'name':f'Rehearsal {index+1:02}','join_code':state['session']['join_code']})
            phones.append({'Authorization':'Bearer '+result['token']})
        async with phone_updates(client,phones) as sse_stats:
            await control('next')
            await asyncio.gather(*(request('POST','/api/pick',headers=h,json={'alert':['identity','invoice','files'][i%3]}) for i,h in enumerate(phones)))
            await control('next');launch=time.monotonic()
            await asyncio.gather(*(request('POST','/api/investigate',headers=h,json={}) for h in phones))
            while time.monotonic()-launch<240:
                state=await request('GET','/api/facilitator')
                report['health_samples'].append({'elapsed':time.monotonic()-launch,'models':{k:v['healthy'] for k,v in state['model_health'].items()}})
                current=state['teams']
                if all(t.get('investigation',{}).get('status') in ('done','failed') for t in current):break
                await asyncio.sleep(.5)
            report['investigations']=[{'team':t['name'],**t.get('investigation',{})} for t in state['teams']]
            report['investigation_wall_seconds']=time.monotonic()-launch
            await control('twist')
            for h,t in zip(phones,state['teams']):
                if t.get('investigation',{}).get('status')=='done':
                    await request('POST','/api/decision',headers=h,json={'decision':'escalate','evidence':['token','session','twist']})
            # Wait for both independent model reviews before starting another workload.
            review_deadline=time.monotonic()+120
            while time.monotonic()<review_deadline:
                state=await request('GET','/api/facilitator')
                if all(t.get('reviews') or not t.get('decision') for t in state['teams']):break
                await asyncio.sleep(.5)
            await control('lock');await control('next')
            if combined:
                report['initial_investigations']=[{'team':r['team'],'duration_seconds':r.get('duration_seconds'),'cached':r.get('cached'),'status':r.get('status')} for r in report['investigations']]
                await request('POST','/api/rehearsal/combined',json={})
            else:
                await control('overdrive')
            overdrive_start=time.monotonic()
            while time.monotonic()-overdrive_start<180:
                state=await request('GET','/api/facilitator')
                report['health_samples'].append({'elapsed':time.monotonic()-launch,'models':{k:v['healthy'] for k,v in state['model_health'].items()}})
                investigations_done=all(t.get('investigation',{}).get('status') in ('done','failed') for t in state['teams'])
                if state['session']['overdrive']=='done' and investigations_done:break
                await asyncio.sleep(.5)
            report['combined_wall_seconds']=time.monotonic()-overdrive_start
            report['overdrive_seconds']=state['session'].get('overdrive_finished_at',time.time())-state['session'].get('overdrive_started_at',time.time())
            if combined:
                report['investigations']=[{'team':t['name'],**t.get('investigation',{})} for t in state['teams']]
            report['overdrive_state']=state['session']['overdrive']
            report['overdrive_agreement']=state['overdrive_agreement']
            for _ in range(7):await control('reveal')
            await control('next')
            for index,h in enumerate(phones):
                await request('POST','/api/card',headers=h,json={'account':f'Fictional evaluation account {index+1}','industry':list(state['industries'])[index%10],'owner':f'Seller {index+1}','target_date':(date.today()+timedelta(days=14)).isoformat()})
            final=await request('GET','/api/facilitator')
            report.update(connected_phones_at_finish=final['connected_phones'],commitments=final['commitment_count'],metrics=final['metrics'],models_live=[m['key'] for m in final['models']],
                          completed=final['investigations_completed'],elapsed_seconds=time.monotonic()-started)
            durations=[r.get('duration_seconds',999) for r in report['investigations']]
            report['sse_bots']=dict(sse_stats)
            report['passed']=sse_stats['connected']==teams and final['connected_phones']==teams and all(not r.get('cached') and r.get('status')=='done' for r in report.get('initial_investigations',[])) and all(r.get('status')=='done' and not r.get('cached') for r in report['investigations']) and len(durations)==teams and max(durations)<75 and report['overdrive_state']=='done' and report['commitments']==teams and report['elapsed_seconds']<1200 and all(all(s['models'].get(k,False) for k in report['models_live']) for s in report['health_samples'])
            metrics=await request('GET','/export?kind=metrics')
            out=Path('exports')/report['session_id'];out.mkdir(parents=True,exist_ok=True)
            (out/'metrics.json').write_text(json.dumps(metrics,indent=2))
            (out/'rehearsal.json').write_text(json.dumps(report,indent=2))
            for kind,ext in [('commitments','csv'),('scores','csv'),('cards','zip')]:
                r=await client.get('/export',params={'kind':kind});r.raise_for_status();(out/f'{kind}.{ext}').write_bytes(r.content)
            summary={k:v for k,v in report.items() if k not in ('investigations','metrics','settings','health_samples')}
            summary['durations_seconds']=durations
            summary['peak_5s']=report['metrics']['peak_5s'] if report['metrics'] else None
            summary['peak_at']=report['metrics']['peak_at'] if report['metrics'] else None
            Path('runtime/last-rehearsal.json').write_text(json.dumps(summary,indent=2))
            print(json.dumps(summary,indent=2),flush=True)
            return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--teams',type=int,default=15);p.add_argument('--combined',action='store_true');args=p.parse_args()
    result=asyncio.run(run(args.teams,args.combined))
    if not result['passed']:raise SystemExit(1)
