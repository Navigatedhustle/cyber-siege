#!/usr/bin/env python3
"""Wall time throughput for a named workload, with all resident models documented.

Run after gates and bots stop. Solo means only one model receives this workload;
other healthy model weights stay resident, matching the deployed memory plan.
"""
import argparse
import asyncio
import json
import sys
import time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ai.router import ModelRouter
from scripts.model_gate import fixture
from app.gpu import GPU

async def main(args):
    from collections import defaultdict
    from types import SimpleNamespace
    counts=defaultdict(int);usage_calls=defaultdict(int)
    def usage(key,count,scope,raw):
        if count is not None:counts[key]+=count
        usage_calls[key]+=1
    router=ModelRouter(telemetry=SimpleNamespace(record=usage));await router.probe();keys=router.lineup(True);report=[]
    try:
        for mode in ['solo','combined']:
            groups=[[key] for key in keys] if mode=='solo' else [keys]
            for group in groups:
                counts.clear();usage_calls.clear();starts={};ends={}
                start=time.monotonic();before=GPU().sample()
                async def one(key,index):
                    starts.setdefault(key,time.monotonic())
                    role=['identity','email','endpoint','data_access'][index%4] if key=='hero' else 'twist_check'
                    payload,schema,allowed=fixture(role)
                    try:return await router.call(role,payload,schema,allowed,key,True)
                    finally:ends[key]=time.monotonic()
                results=await asyncio.gather(*(one(key,index) for key in group for index in range(args.calls)),return_exceptions=True)
                elapsed=time.monotonic()-start
                models={}
                for key in group:
                    values=[r for r in results if isinstance(r,dict) and r['model']==key]
                    tokens=counts[key]
                    models[key]={'completed':len(values),'usage_calls_including_retries':usage_calls[key],'completion_tokens':tokens,'output_tokens_per_wall_second':tokens/elapsed,'active_wall_seconds':ends[key]-starts[key],'output_tokens_per_active_wall_second':tokens/(ends[key]-starts[key]),'request_latencies_seconds':[r['latency_seconds'] for r in values]}
                row={'at':datetime.now(timezone.utc).isoformat(),'mode':mode,'definition':'Only named workload active; all healthy models resident','resident_models':keys,'active_models':group,'calls_per_model':args.calls,'workloads':{'hero':'Two calls each to identity, email, endpoint and data specialists for an eight call run','challenger':'Independent twist reviews'},'wall_seconds':elapsed,'models':models,'errors':[str(r) for r in results if isinstance(r,Exception)],'gpu_before':before,'gpu_after':GPU().sample()}
                report.append(row);print(json.dumps(row),flush=True)
        Path('runtime/model-benchmarks.json').write_text(json.dumps(report,indent=2))
    finally:await router.close()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--calls',type=int,default=8);asyncio.run(main(p.parse_args()))
