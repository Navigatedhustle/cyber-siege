#!/usr/bin/env python3
"""Warm the real room-sized concurrency, outside all live session counters."""
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ai.router import ModelRouter
from app.ai.schemas import SpecialistResult,ReviewResult
from app.ai.retrieval import search_logs,evidence_rows

async def main():
    router=ModelRouter();report=[]
    for _ in range(12):
        await router.probe()
        if 'hero' in router.lineup(True):break
        await asyncio.sleep(1)
    if 'hero' not in router.lineup(True):
        await router.close();raise RuntimeError('Hero not ready. Warmup cannot pass without the hero.')
    async def one(key,role):
        if role=='twist_check':
            rows=evidence_rows(['FIL9003','FIL9005','FIL9002','IDP9001','EML9001','EDR9001','NET9001'],True)
            payload={'decision':'escalate','logs':rows,'instructions':'Review new access FIL9003 against baseline FIL9005. Cite both. Explain in at most 50 words and uncertainty in 20 words.'};schema=ReviewResult
        else:
            rows=search_logs(role,'invoice')['rows']
            payload={'logs':rows,'instructions':'Find at most three material anomaly findings, at most 35 words each and four log IDs each. Do not catalog routine events.'};schema=SpecialistResult
        try:
            result=await router.call(role,payload,schema,{row['id'] for row in rows},key,True)
            return {'role':role,**result}
        except Exception as exc:return {'model':key,'role':role,'error':str(exc)}
    try:
        tasks=[]
        for key in router.lineup(True):
            for index in range(router.config[key]['concurrency_cap']):
                role=['identity','email','endpoint','data_access'][index%4] if key=='hero' else 'twist_check'
                tasks.append(one(key,role))
        report=await asyncio.gather(*tasks)
        Path('runtime/warmup.json').write_text(json.dumps(report,indent=2))
        print(json.dumps({'calls':len(report),'models':router.lineup(True),'errors':[r for r in report if r.get('error')],'latencies_seconds':[r.get('latency_seconds') for r in report]},indent=2),flush=True)
    finally:await router.close()
    if not report or any('error' in r for r in report):raise SystemExit(1)
if __name__=='__main__':asyncio.run(main())
