#!/usr/bin/env python3
"""Verify real recorded replay with both model HTTP servers actually stopped."""
import asyncio
import json
import sys
import time
from datetime import date,timedelta,datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from app.config import settings
from app.ai import replay

async def main():
    report={'at':datetime.now(timezone.utc).isoformat(),'label':'REPLAY from REHEARSAL','endpoint_checks':{}}
    async with httpx.AsyncClient(timeout=10,trust_env=False) as client:
        for port in [8000,8001]:
            try:
                response=await client.get(f'http://127.0.0.1:{port}/v1/models')
                raise RuntimeError(f'Model endpoint {port} still responds ({response.status_code}); stop the managed models before this proof')
            except httpx.ConnectError:report['endpoint_checks'][str(port)]='connection refused'
        client.base_url=f'http://127.0.0.1:{settings.app_port}'
        async def request(method,path,**kwargs):
            response=await client.request(method,path,**kwargs);response.raise_for_status();return response.json()
        await request('POST','/api/login',json={'pin':settings.facilitator_pin})
        async def command(action,**extra):return await request('POST','/api/control',json={'action':action,**extra})
        state=await command('create',label='REHEARSAL');report['session_id']=state['session']['id'];await command('replay')
        phones=[];alerts=['identity','invoice','files']
        for index in range(3):
            joined=await request('POST','/api/join',json={'name':f'Replay QA {index+1}','join_code':state['session']['join_code']});phones.append({'Authorization':'Bearer '+joined['token']})
        await command('next')
        for alert,header in zip(alerts,phones):await request('POST','/api/pick',headers=header,json={'alert':alert})
        await command('next');at=time.monotonic()
        for header in phones:await request('POST','/api/investigate',headers=header,json={})
        while time.monotonic()-at<120:
            state=await request('GET','/api/facilitator')
            if all(t.get('investigation',{}).get('status') in ('done','failed') for t in state['teams']):break
            await asyncio.sleep(.25)
        report['investigations']=[{'alert':t['pick'],'status':t['investigation']['status'],'cached':t['investigation'].get('cached'),'recorded_at':t['investigation'].get('recorded_at'),'duration_seconds':t['investigation'].get('duration_seconds'),'original_timing_seconds':replay.load(t['pick'])['events'][-1]['elapsed']} for t in state['teams']]
        report['live_compute_hidden']=state['metrics'] is None
        report['live_investigations']=state['investigations_completed'];report['teams_served_live']=state['served']
        await command('twist')
        for header in phones:await request('POST','/api/decision',headers=header,json={'decision':'escalate','evidence':['token','session','twist']})
        await command('next');await command('next')
        for index,header in enumerate(phones):await request('POST','/api/card',headers=header,json={'account':f'Fictional replay account {index+1}','industry':'technology','owner':'Replay Seller','target_date':(date.today()+timedelta(days=14)).isoformat()})
        state=await request('GET','/api/facilitator');report['commitments']=state['commitment_count']
        metrics=await request('GET','/export?kind=metrics');report['usage_events']=sum(e.get('type')=='usage' for e in metrics['events'])
        report['passed']=report['live_compute_hidden'] and report['live_investigations']==0 and report['teams_served_live']==0 and report['usage_events']==0 and report['commitments']==3 and all(r['status']=='done' and r['cached'] and abs(r['duration_seconds']-r['original_timing_seconds'])<3 for r in report['investigations'])
        Path('runtime/replay-proof.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':asyncio.run(main())
