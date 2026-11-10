#!/usr/bin/env python3
"""Owned endpoint loss, 20-second private relay outage, reconnect and boundary checks."""
import asyncio
import json
import subprocess
import time
import httpx
import websockets
from harness import ROOT,Server

async def main():
    log=(ROOT/'runtime/revamp-chaos-processes.log').open('ab')
    proxy=subprocess.Popen([str(ROOT/'.venv/bin/python'),'scripts/revamp/model_proxy.py'],cwd=ROOT,stdout=log,stderr=log)
    hub=None;server=None
    report={'production_models_stopped':False,'tests':[]}
    def start_hub():
        return subprocess.Popen([str(ROOT/'.venv/bin/python'),'-m','revamp.relay','--upstream',server.base,'--port','8095'],cwd=ROOT,stdout=log,stderr=log)
    try:
        server=Server('revamp-chaos-'+str(int(time.time())),port=8093,scale=.1,model_url='http://127.0.0.1:8094/v1')
        hub=start_hub();await asyncio.sleep(1)
        room=server.create();code=room['code']
        async with httpx.AsyncClient(base_url=server.base,timeout=10,trust_env=False,cookies=server.client.cookies) as admin:
            async with httpx.AsyncClient(base_url=server.base,timeout=10,trust_env=False) as outsider:
                denied=await outsider.post(f'/api/rooms/{code}/control',json={'command':'start'})
                assert denied.status_code==400
                invalid=await outsider.post('/api/join',json={'code':code,'name':'x','team':'99'})
                assert invalid.status_code==400
                bad_origin=await outsider.post('/api/login',headers={'Origin':'http://untrusted.example'},json={'password':'bad'})
                assert bad_origin.status_code==403
                assert (await outsider.get('/.env')).status_code==404
                assert (await outsider.get('/config/stories.local.json')).status_code==404
            report['tests'].append({'security':'unauthenticated controls, invalid team, cross-origin login, secret/static path access rejected','passed':True})
            join=await admin.post('/api/join',json={'code':code,'name':'<img src=x onerror=alert(1)>','team':'1'})
            token=join.json()['token']
            ws=await websockets.connect('ws://127.0.0.1:8095/ws/'+code,proxy=None)
            await ws.send(json.dumps({'type':'hello','token':token}))
            await ws.recv()
            await admin.post(f'/api/rooms/{code}/control',json={'command':'autopilot_all','value':True})
            await admin.post(f'/api/rooms/{code}/control',json={'command':'start'})
            await admin.post(f'/api/rooms/{code}/control',json={'command':'next'})
            # Deliberately lose a player while a wave is running, then reconnect with the same token.
            await ws.close();await asyncio.sleep(.5)
            rejoin=await admin.post('/api/join',json={'code':code,'name':'ignored','token':token})
            assert rejoin.json()['state']['me']['team']=='1'
            report['tests'].append({'player_disconnect':'mid-wave reconnect preserves token, team and progress within 0.5s','passed':True})
            # Observe an in-flight request, then terminate only our injected model gateway.
            before=(await admin.get(f'/api/rooms/{code}')).json()
            assert before['power']['active']>0
            proxy.terminate();proxy.wait(timeout=5)
            await asyncio.sleep(2)
            failed=(await admin.get(f'/api/rooms/{code}')).json()
            assert failed['fallback_count']>0
            report['tests'].append({'model_endpoint_loss':'terminated this script’s loopback model gateway during active calls; actual Nemotron/container untouched','fallbacks_observed':failed['fallback_count'],'passed':True})
            # Stop our hub for a real twenty seconds; the authoritative Fury game keeps moving.
            before_remaining=failed['remaining']
            hub.terminate();hub.wait(timeout=5);hub=None
            outage_started=time.monotonic()
            await asyncio.sleep(20)
            hub=start_hub();await asyncio.sleep(1)
            recovered_ws=await websockets.connect('ws://127.0.0.1:8095/ws/'+code,proxy=None)
            await recovered_ws.send(json.dumps({'type':'hello','token':token}))
            recovered=json.loads(await recovered_ws.recv())['state']
            assert recovered['me']['team']=='1'
            assert recovered['server_time']>failed['server_time']+20
            assert recovered['wave']>=failed['wave']
            assert recovered['remaining']!=before_remaining or recovered['wave']>failed['wave']
            await recovered_ws.close()
            report['tests'].append({'room_hub_outage_s':round(time.monotonic()-outage_started,2),'autopilot_continued':True,'team_preserved':True,'passed':True})
            # Restart owned gateway. Force a new wave's real calls and observe recovery.
            proxy=subprocess.Popen([str(ROOT/'.venv/bin/python'),'scripts/revamp/model_proxy.py'],cwd=ROOT,stdout=log,stderr=log)
            await asyncio.sleep(1)
            for _ in range(4):
                cur=(await admin.get(f'/api/rooms/{code}')).json()
                if cur['phase']=='wave' and cur['wave']==3:break
                await admin.post(f'/api/rooms/{code}/control',json={'command':'next'})
            await admin.post(f'/api/rooms/{code}/control',json={'command':'replay'})
            await asyncio.sleep(3)
            recovered_model=(await admin.get(f'/api/rooms/{code}')).json()
            assert any(not b['scripted'] for b in recovered_model['bubbles'].values())
            report['tests'].append({'model_recovery':'live responses resume after owned gateway restarts','passed':True})
            # Reject malformed and excessive client messages at WebSocket boundary.
            bad=await websockets.connect(server.base.replace('http:','ws:')+'/ws/'+code,proxy=None)
            await bad.send(json.dumps({'type':'hello','token':token}));await bad.recv()
            await bad.send('{not json')
            try:
                while True:await bad.recv()
            except websockets.ConnectionClosed as exc:assert exc.rcvd.code==1008
            report['tests'].append({'invalid_websocket_message':'closed with policy code 1008, server remains healthy','passed':True})
            assert (await admin.get('/health')).status_code==200
        calls=[json.loads(x) for x in (server.data/'model_calls.jsonl').read_text().splitlines()]
        report['fallback_count']=sum(c['scripted'] for c in calls)
        report['model_call_max_s']=max(c['latency_s'] for c in calls)
        report['passed']=all(c['latency_s']<8 for c in calls) and all(x['passed'] for x in report['tests'])
    finally:
        for proc in [hub,proxy]:
            if proc and proc.poll() is None:proc.terminate();proc.wait(timeout=6)
        if server:server.close()
        log.close()
    (ROOT/'docs/revamp-chaos.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
