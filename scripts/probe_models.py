#!/usr/bin/env python3
"""Probe protocol behavior, including a deliberately contradictory schema enum."""
import asyncio
import json
import sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from app.ai.router import ModelRouter
from app.metrics import parse_counter

async def main():
    router=ModelRouter();await router.probe();report={}
    try:
        for key in router.lineup(True):
            config=router.config[key];http=router.clients[key].http
            schema={'type':'object','properties':{'proof':{'type':'string','enum':['SCHEMA_ENFORCED']}},'required':['proof'],'additionalProperties':False}
            body={'model':config['model_id'],'messages':[{'role':'user','content':'Return only JSON with proof equal to SCHEMA_IGNORED. Do not use any other value.'}],'max_tokens':120,'temperature':0,'stream':True,'stream_options':{'include_usage':True},'response_format':{'type':'json_schema','json_schema':{'name':'ProtocolProbe','strict':True,'schema':schema}}}
            if key=='hero':body['chat_template_kwargs']={'enable_thinking':False}
            else:body['reasoning_effort']='low'
            chunks=[];usage=None
            async with http.stream('POST',config['base_url']+'/chat/completions',json=body) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith('data:'):continue
                    raw=line[5:].strip()
                    if raw=='[DONE]':break
                    value=json.loads(raw)
                    if value.get('usage'):usage=value['usage']
                    for choice in value.get('choices',[]):chunks.append(choice.get('delta',{}).get('content') or '')
            text=''.join(chunks)
            metrics=await http.get(config['metrics_url'])
            models=await http.get(config['base_url']+'/models')
            health=await http.get(config['base_url'].removesuffix('/v1')+'/health')
            report[key]={'at':datetime.now(timezone.utc).isoformat(),'models':models.json(),'health_status':health.status_code,'metrics_format':metrics.headers.get('content-type'),'metrics_counter':parse_counter(metrics.text),'metrics_excerpt':metrics.text[:500],'stream_usage':usage,'contradictory_schema_output':text,'schema_enum_enforced':text.strip()=='{"proof": "SCHEMA_ENFORCED"}' or (json.loads(text).get('proof')=='SCHEMA_ENFORCED' if text else False)}
        Path('docs/model-probes.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    finally:await router.close()
if __name__=='__main__':asyncio.run(main())
