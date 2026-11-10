"""One global cap plus a cap per model. Non hero failures fall back explicitly."""
import asyncio
import json
import time
import logging
import httpx
from pathlib import Path
import yaml
from app.config import ROOT, settings, local_endpoint
from .client import ModelClient

log=logging.getLogger(__name__)

class ModelUnavailable(RuntimeError): pass

class ModelRouter:
    def __init__(self, config=None, telemetry=None):
        config=config or yaml.safe_load((ROOT/settings.models_config).read_text())['models']
        self.config=config
        self.clients={}
        self.status={}
        self.caps={}
        self.global_cap=asyncio.Semaphore(settings.agent_concurrency_limit)
        self.telemetry=telemetry
        self.probe_count=0
        for key,row in config.items():
            local_endpoint(row['base_url'])
            local_endpoint(row['metrics_url'])
            self.clients[key]=ModelClient(row)
            self.caps[key]=asyncio.Semaphore(row['concurrency_cap'])
            self.status[key]={'healthy':False,'qualified':False,'queue_depth':0,'active':0,'last_latency':None,'error':'Not probed','fallbacks':0,'consecutive_probe_failures':0,'last_healthy_at':None,'degraded':False,'readiness_blocked':False}

    def qualified(self,key):
        path=ROOT/self.config[key].get('gate_file',f'runtime/gates/{key}.json')
        try:
            gate=json.loads(path.read_text())
            fields=('model_id','serving_stack','concurrency_cap','max_tokens','reasoning','structured_output','gpu_memory_utilization')
            profile_matches=all(gate.get('config',{}).get(field)==self.config[key].get(field) for field in fields)
            return gate.get('passed') is True and gate.get('model_id')==self.config[key]['model_id'] and profile_matches
        except (OSError,ValueError): return False

    async def probe(self):
        self.probe_count+=1
        async def one(key):
            status=self.status[key]
            client=self.clients[key].health_http
            try:
                root=self.config[key]['base_url'].removesuffix('/v1')
                response=await client.get(root+'/health')
                response.raise_for_status()
                if status['last_healthy_at'] is None or self.probe_count%12==0 or not status['healthy']:
                    models=await client.get(self.config[key]['base_url']+'/models')
                    models.raise_for_status()
                    ids=[x['id'] for x in models.json()['data']]
                    if self.config[key]['model_id'] not in ids:
                        status['healthy']=False
                        raise ValueError(f'Configured model ID absent: {ids}')
                if not status.get('readiness_blocked'):
                    status.update(healthy=True,error=None,consecutive_probe_failures=0,last_healthy_at=time.time(),degraded=False)
            except Exception as exc:
                status['consecutive_probe_failures']+=1
                status['degraded']=True
                status['error']=str(exc)[:180] or type(exc).__name__
                if status['last_healthy_at'] is None or status['consecutive_probe_failures']>=3:
                    status['healthy']=False
                log.warning('Model %s health probe failed (%s/3): %s',key,status['consecutive_probe_failures'],status['error'])
            status['qualified']=self.qualified(key)
        await asyncio.gather(*(one(k) for k in self.config))

    def lineup(self, rehearsal=False):
        return [k for k,s in self.status.items() if s['healthy'] and (rehearsal or s['qualified'])]

    def route(self,role,preferred=None,rehearsal=False):
        eligible=self.lineup(rehearsal)
        candidates=[preferred] if preferred else [k for k,c in self.config.items() if role in c['roles']]
        for key in candidates:
            if key in eligible: return key
        if 'hero' in eligible:
            if preferred and preferred!='hero': self.status[preferred]['fallbacks']+=1
            return 'hero'
        raise ModelUnavailable('Hero unavailable or not qualified; recorded rehearsal required')

    async def call(self,role,payload,schema,allowed,preferred=None,rehearsal=False,scope=None,reasoning=None):
        from .validate import validate_ids
        payload={**payload,'allowed_log_ids':sorted(allowed)}
        key=self.route(role,preferred,rehearsal)
        status=self.status[key]
        status['queue_depth']+=1
        admitted=False
        try:
            async with self.caps[key], self.global_cap:
                status['queue_depth']-=1; status['active']+=1
                admitted=True
                started=time.monotonic()
                try:
                    if status.get('readiness_blocked'):raise ModelUnavailable('Model inference is blocked after transport failures; use replay until verified recovery')
                    for attempt in range(2):
                        try:
                            def usage(count,raw):
                                if self.telemetry: self.telemetry.record(key,count,scope,raw)
                            toggle=reasoning if reasoning is not None else self.config[key].get('reasoning_by_role',{}).get(role,self.config[key].get('reasoning',False))
                            result=None
                            result,meta=await self.clients[key].complete(role,payload,schema,usage,reasoning=toggle,allowed_ids=allowed)
                            data=validate_ids(result,allowed)
                            if role=='lead':
                                from .lead import validate_timeline
                                validate_timeline(data,set(payload.get('material_event_ids',[])))
                                timeline_ids={item for event in data['events'] for item in event['log_ids']}
                                missing={source:ids for source,ids in payload.get('source_evidence',{}).items() if ids and not timeline_ids.intersection(ids)}
                                if missing:raise ValueError('Timeline omitted specialist source evidence: '+str(missing)+'. Include its material finding while keeping events concise.')
                            status.update(healthy=True,last_healthy_at=time.time(),consecutive_probe_failures=0,degraded=False,error=None)
                            return {'data':data,'model':key,'model_name':self.config[key]['name'],'lab':self.config[key]['lab'],**meta}
                        except Exception as exc:
                            if attempt: raise
                            log.warning('Retrying %s role %s after %s',key,role,str(exc)[:300])
                            payload={**payload,'retry_instruction':f'Correct this previous output. {str(exc)[:500]}','previous_invalid_output':result.model_dump() if result is not None else None}
                finally:
                    status['active']-=1
                    status['last_latency']=time.monotonic()-started
        except Exception as exc:
            transport_failure=isinstance(exc,httpx.TransportError) or isinstance(exc,httpx.HTTPStatusError) and exc.response.status_code>=500
            if transport_failure:
                status.update(healthy=False,readiness_blocked=True,error='Inference failed despite HTTP health. Verified warmup and app restart required.')
            # Retry a failed secondary using hero, preserving producer attribution.
            if key!='hero' and self.status['hero']['healthy']:
                self.status[key]['healthy']=False
                self.status[key]['fallbacks']+=1
                return await self.call(role,payload,schema,allowed,'hero',rehearsal,scope,reasoning)
            raise
        finally:
            # Cancelled queued requests must not leave phantom queue depth.
            if not admitted: status['queue_depth']=max(0,status['queue_depth']-1)

    async def close(self):
        await asyncio.gather(*(c.close() for c in self.clients.values()))
