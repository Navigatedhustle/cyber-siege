#!/usr/bin/env python3
"""Unretried schema trials plus a real sustained load and independent smoke test.

A short diagnostic run alone never qualifies a model. An explicit schema rerun may
reuse a completed 30 minute health window for the exact unchanged configuration
when that window ended no more than one hour before this run, with Docker proving the same runtime has
not restarted since that window began. Minimum qualifying health window
is 1800 seconds with at least 200 first attempt schema trials at 98% validity.
"""
import argparse
import asyncio
import hashlib
import json
import sys
import subprocess
import time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.ai.router import ModelRouter
from app.ai.schemas import SpecialistResult,LeadResult,ReviewResult
from app.ai.retrieval import search_logs,evidence_rows
from app.ai.validate import validate_ids
from app.ai.specialists import investigate_specialist
from app.ai.lead import lead
from app.ai.twist_check import review
from app.gpu import GPU

ROLES=['identity','email','endpoint','data_access','lead','twist_check']

def fixture(role):
    if role in ROLES[:4]:
        rows=search_logs(role,'invoice')['rows']
        return {'logs':rows,'instructions':'Return at most three material anomaly findings and entities, at most 35 words per finding and four log IDs each. Do not catalog routine events.'},SpecialistResult,{r['id'] for r in rows}
    rows=evidence_rows(['EML9001','EDR9001','EDR9002','NET9001','IDP9001','FIL9001','FIL9002','FIL9003','FIL9005'],True)
    if role=='lead':
        return {'logs':rows,'instructions':'Reconstruct the chain in chronological order. Each event explanation at most 12 words, one main action without addresses or session strings. Cite events and summary.'},LeadResult,{r['id'] for r in rows}
    return {'logs':rows,'decision':'escalate','new_event_log_id':'FIL9003','normal_backup_log_id':'FIL9005','instructions':'Independently assess the new service account access against its normal backup baseline, citing both FIL9003 and FIL9005 and connecting the earlier attack chain. Explanation at most 50 words. Uncertainty at most 20 words. Finish sentences and cite evidence.'},ReviewResult,{r['id'] for r in rows}

async def gate(key,router,args):
    config=router.config[key]; client=router.clients[key]
    begin=time.monotonic();started=datetime.now(timezone.utc).isoformat()
    prior_health=None
    if args.health_evidence:
        prior_health=json.loads(Path(args.health_evidence).read_text())
        if (prior_health.get('model_id')!=config['model_id'] or any(prior_health.get('config',{}).get(field)!=config.get(field) for field in ('model_id','base_url','serving_stack','concurrency_cap','max_tokens','reasoning')) or
            not prior_health.get('healthy_entire_window') or prior_health.get('elapsed_seconds',0)<1800 or
            (datetime.now(timezone.utc)-datetime.fromisoformat(prior_health['finished_at'])).total_seconds()>3600):
            raise ValueError('Health evidence must be recent, continuously healthy for 30 minutes, and for this unchanged model endpoint and runtime workload limits')
        name={'hero':'hp-nemotron-serve','challenger':'cyber-siege-challenger'}[key]
        inspected=subprocess.run(['sg','docker','-c',f"docker inspect --format '{{{{json .State}}}}' {name}"],capture_output=True,text=True,timeout=5)
        runtime=json.loads(inspected.stdout)
        server_start=datetime.fromisoformat(runtime['StartedAt'].replace('Z','+00:00'))
        if not runtime['Running'] or server_start>datetime.fromisoformat(prior_health['started_at']):
            raise ValueError('The model container restarted after the measured health window began; run a fresh 30 minute gate')
    report={'model':key,'model_id':config['model_id'],'started_at':started,'trials':[],'health_samples':[],'passed':False,'config':config}
    Path('runtime/gates').mkdir(parents=True,exist_ok=True)
    path=Path('runtime/gates')/f'{key}.json'
    def persist():path.write_text(json.dumps(report,indent=2)+'\n')
    async def call(index,role):
        payload,schema,allowed=fixture(role);usage=[];at=time.monotonic()
        try:
            value,meta=await client.complete(role,payload,schema,lambda n,r:usage.append(n),allowed_ids=allowed)
            data=validate_ids(value,allowed)
            trial={'index':index,'role':role,'valid':True,'latency_seconds':time.monotonic()-at,'completion_tokens':sum(n for n in usage if n is not None),'data':data}
        except Exception as exc:
            trial={'index':index,'role':role,'valid':False,'latency_seconds':time.monotonic()-at,'error':str(exc)[:400]}
        return trial
    healthy=True;index=0
    while index<args.calls or time.monotonic()-begin<args.seconds:
        group=range(index,min(index+args.concurrency,max(args.calls,index+args.concurrency)))
        batch=await asyncio.gather(*(call(i,ROLES[i%len(ROLES)] if key=='hero' else 'twist_check') for i in group))
        report['trials'].extend(batch);index+=len(batch)
        try:
            response=await client.http.get(config['base_url'].removesuffix('/v1')+'/health',timeout=5)
            current=response.is_success
        except Exception: current=False
        healthy=healthy and current
        report['health_samples'].append({'elapsed':time.monotonic()-begin,'healthy':current,'gpu':GPU().sample()})
        report['elapsed_seconds']=time.monotonic()-begin
        report['valid_calls']=sum(x['valid'] for x in report['trials'])
        report['total_calls']=len(report['trials'])
        persist()
        print(key,report['total_calls'],report['valid_calls'],'valid',int(report['elapsed_seconds']),'seconds',flush=True)
        # Spread representative requests across the entire health window.
        if index>=args.calls and time.monotonic()-begin<args.seconds:await asyncio.sleep(min(5,max(0,args.seconds-(time.monotonic()-begin))))
    scope={'id':'model-gate','label':'REHEARSAL','created':started,'replay':False}
    async def emit(data):pass
    try:
        if key=='hero':
            findings=await asyncio.gather(*(investigate_specialist(router,r,'invoice',scope,emit) for r in ROLES[:4]))
            smoke=await lead(router,findings,scope)
            ids={i for item in smoke['data']['events'] for i in item['log_ids']}
            needed=[{'EML9001'},{'EDR9001','EDR9002','NET9001'},{'IDP9001'},{'FIL9001','FIL9002'}]
            smoke_ok=all(bool(ids&group) for group in needed)
        else:
            payload,schema,allowed=fixture('lead')
            payload['instructions']='Reconstruct the attack chain from the fictional logs in chronological events. Include the supplier invoice, browser session theft, replayed sign in, finance download and new service account access contrasted with its normal backup. In the service account timeline event cite BOTH FIL9003 and FIL9005 and compare their source and backup timing. Cite each source in the timeline, not only the summary. Explain each event in at most 12 words, with one main action. Do not issue a verdict or score.'
            value,meta=await client.complete('scenario_smoke',payload,schema,lambda n,r:None,allowed_ids=allowed)
            data=validate_ids(value,allowed);smoke={'data':data,**meta}
            ids={i for event in data['events'] for i in event['log_ids']}
            needed=[{'EML9001'},{'EDR9001','EDR9002','NET9001'},{'IDP9001'},{'FIL9001','FIL9002'},{'FIL9003'},{'FIL9005'}]
            smoke_ok=all(bool(ids&group) for group in needed)
        report['smoke']={'passed':smoke_ok,'result':smoke}
    except Exception as exc: report['smoke']={'passed':False,'error':str(exc)}
    report['elapsed_seconds']=time.monotonic()-begin
    report['validity_rate']=report['valid_calls']/max(1,report['total_calls'])
    report['healthy_entire_window']=healthy
    report['health_evidence']=str(args.health_evidence) if prior_health else None
    report['sustained_health_seconds']=prior_health['elapsed_seconds'] if prior_health else report['elapsed_seconds']
    report['passed']=bool(healthy and (prior_health is not None or args.seconds>=1800 and report['elapsed_seconds']>=1800) and report['total_calls']>=200 and report['validity_rate']>=.98 and report['smoke']['passed'])
    report['finished_at']=datetime.now(timezone.utc).isoformat();persist()
    doc=Path('docs/MODEL_PLAN.md')
    with doc.open('a') as stream:
        stream.write(f"\n## Gate {key} · {report['finished_at']}\n\n{report['valid_calls']}/{report['total_calls']} first attempt schema and citation valid calls; {report['elapsed_seconds']:.2f} seconds in this run; sustained health evidence {report['sustained_health_seconds']:.2f} seconds ({report['health_evidence'] or 'this run'}); continuous sampled health {healthy}; scenario smoke {report['smoke']['passed']}; qualified **{report['passed']}**. Raw report: {path}.\n")
    return report['passed']

async def main(args):
    router=ModelRouter();await router.probe()
    keys=[args.model] if args.model else router.lineup(True)
    try:
        if not keys:raise RuntimeError('No healthy local models. No gate can be claimed.')
        results=await asyncio.gather(*(gate(k,router,args) for k in keys))
    finally:await router.close()
    if not all(results):raise SystemExit(1)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--model');p.add_argument('--calls',type=int,default=200);p.add_argument('--seconds',type=float,default=1800);p.add_argument('--concurrency',type=int,default=4);p.add_argument('--health-evidence')
    asyncio.run(main(p.parse_args()))
