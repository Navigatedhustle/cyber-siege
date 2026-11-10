#!/usr/bin/env python3
"""Recheck every starting path and retain the prior qualification smoke evidence."""
import asyncio
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ai.router import ModelRouter
from app.ai.specialists import investigate_specialist
from app.ai.lead import lead

async def main():
    router=ModelRouter();await router.probe()
    lead_attempts=[]
    original=router.clients['hero'].complete
    async def capture(role,payload,*args,**kwargs):
        value,meta=await original(role,payload,*args,**kwargs)
        if role=='lead':lead_attempts.append({'data':value.model_dump(),'meta':meta})
        return value,meta
    router.clients['hero'].complete=capture
    scope={'id':'scenario-qa','label':'REHEARSAL','created':datetime.now(timezone.utc).isoformat()}
    async def check(alert):
        events=[]
        async def emit(value):events.append(value)
        try:
            findings=await asyncio.gather(*(investigate_specialist(router,role,alert,scope,emit) for role in ['identity','email','endpoint','data_access']))
            result=await lead(router,findings,scope)
            ids={key for item in result['data']['events'] for key in item['log_ids']}
            passed=all(ids&group for group in [{'EML9001'},{'EDR9001','EDR9002','NET9001'},{'IDP9001'},{'FIL9001','FIL9002'}])
            return {'alert':alert,'passed':bool(passed),'result':result,'events':events}
        except Exception as exc:
            return {'alert':alert,'passed':False,'error':str(exc),'events':events}
    try:
        results=await asyncio.gather(*(check(alert) for alert in ['identity','invoice','files']))
        passed=all(value['passed'] for value in results)
        value={'at':datetime.now(timezone.utc).isoformat(),'passed':passed,'results':results,'lead_attempts':lead_attempts}
        Path('runtime/scenario-check.json').write_text(json.dumps(value,indent=2));print(json.dumps(value,indent=2))
        path=Path('runtime/gates/hero.json');gate=json.loads(path.read_text())
        gate.setdefault('smoke_attempts',[]).append(gate.get('smoke'))
        gate['smoke']=value
        gate['passed']=bool(passed and gate.get('healthy_entire_window') and gate.get('sustained_health_seconds',0)>=1800 and gate.get('total_calls',0)>=200 and gate.get('validity_rate',0)>=.98)
        path.write_text(json.dumps(gate,indent=2))
        if not passed:raise SystemExit(1)
    finally:await router.close()

if __name__=='__main__':asyncio.run(main())
