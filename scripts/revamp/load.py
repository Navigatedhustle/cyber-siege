#!/usr/bin/env python3
"""Three complete accelerated sessions, real local inference, 60 players + 4 stations."""
import asyncio
import json
from pathlib import Path
import statistics
import sys
import time
import psutil
import httpx
import websockets
from harness import Server, ROOT

def p95(values):return sorted(values)[max(0,int(len(values)*.95)-1)] if values else None

async def main():
    server=Server('revamp-load-'+str(int(time.time())))
    report={'description':'Three complete rules sessions at 0.06 game time scale, live existing Nemotron endpoint, one room reset between groups. Not a real-time 12-minute human rehearsal.',
            'players':60,'stations':4,'teams':8,'sessions':[],'errors':[]}
    sockets=[];readers=[];pings=[];rtts=[];snapshots=[None]*64;cpu=[];memory=[];stop=False
    process=psutil.Process(server.process.pid);process.cpu_percent()
    async with httpx.AsyncClient(base_url=server.base,timeout=15,trust_env=False,cookies=server.client.cookies) as client:
        room=server.create();code=room['code']
        stations=(await client.get(f'/api/rooms/{code}/stations')).json()
        from urllib.parse import urlsplit,parse_qs
        async def connect(i,token=None):
            if token is None:
                team=str(i%8+1)
                body={'code':code,'name':f'Load Seller {i+1}','team':team}
                if i>=60:
                    link=stations[i-60];params=parse_qs(urlsplit(link['url']).query)
                    body.update(team=link['team'],station=params['station'][0],name=f'Table {i-59}')
                response=await client.post('/api/join',json=body);response.raise_for_status();token=response.json()['token']
            ws=await websockets.connect(server.base.replace('http:','ws:')+'/ws/'+code,proxy=None)
            await ws.send(json.dumps({'type':'hello','token':token}))
            return ws,token
        tokens=[]
        for i in range(64):
            ws,token=await connect(i);sockets.append(ws);tokens.append(token)
        async def read(i,ws):
            try:
                async for raw in ws:
                    packet=json.loads(raw)
                    if packet.get('state'):snapshots[i]=packet['state']
                    if packet['type']=='pong':rtts.append((time.perf_counter()-float(packet['nonce']))*1000)
            except websockets.ConnectionClosed:pass
        for i,ws in enumerate(sockets):readers.append(asyncio.create_task(read(i,ws)))
        async def ping(i):
            while not stop:
                try:await sockets[i].send(json.dumps({'type':'ping','nonce':str(time.perf_counter())}))
                except websockets.ConnectionClosed:pass
                await asyncio.sleep(.5)
        for i in range(64):pings.append(asyncio.create_task(ping(i)))
        async def monitor():
            while not stop:
                cpu.append(process.cpu_percent());memory.append(process.memory_info().rss/1024**2)
                await asyncio.sleep(.5)
        monitor_task=asyncio.create_task(monitor())
        for session in range(3):
            start=time.monotonic();first=len(rtts)
            if session:
                response=await client.post(f'/api/rooms/{code}/control',json={'command':'reset'});response.raise_for_status()
            for command,value in [('autopilot_all',True),('start',None)]:
                response=await client.post(f'/api/rooms/{code}/control',json={'command':command,'value':value});response.raise_for_status()
            phases=set();active_peak=0
            while time.monotonic()-start<80:
                response=await client.get(f'/api/rooms/{code}');response.raise_for_status();current=response.json()
                phases.add((current['phase'],current['wave']))
                active_peak=max(active_peak,current['power']['active'])
                if current['phase']=='debrief':break
                await asyncio.sleep(.15)
            else:raise AssertionError('Full session did not complete')
            assert all(len(t['times'])==3 and t['score']>0 for t in current['teams'])
            assert all(s is not None for s in snapshots)
            report['sessions'].append({'number':session+1,'duration_s':round(time.monotonic()-start,2),'phases':sorted(phases),
                                       'websocket_rtt_p95_ms':round(p95(rtts[first:]),2),'samples':len(rtts)-first,
                                       'active_parallel_agents_observed':active_peak,'scores':[t['score'] for t in current['teams']]})
            print(json.dumps(report['sessions'][-1]),flush=True)
            await asyncio.sleep(1)
        stop=True
        for t in pings+[monitor_task]:t.cancel()
        await asyncio.gather(*pings,monitor_task,return_exceptions=True)
        for ws in sockets:await ws.close()
        await asyncio.gather(*readers,return_exceptions=True)
    server.close()
    calls=[json.loads(x) for x in (server.data/'model_calls.jsonl').read_text().splitlines()]
    report.update(websocket_rtt_p95_ms=round(p95(rtts),2),websocket_samples=len(rtts),server_cpu_p95_one_core_percent=round(p95(cpu),2),
                  server_cpu_max_one_core_percent=max(cpu),server_rss_peak_mib=round(max(memory),2),
                  model_calls=len(calls),model_latency_p95_s=round(p95([r['latency_s'] for r in calls]),3),
                  model_latency_max_s=max(r['latency_s'] for r in calls),fallback_count=sum(r['scripted'] for r in calls),
                  zero_crashes=server.process.returncode in {0,-15},model_calls_bounded=all(r['latency_s']<8 for r in calls),
                  model_bubbles_under_25_words=all(r['words']<=25 for r in calls),runtime_path=str(server.data))
    report['passed']=report['zero_crashes'] and report['websocket_rtt_p95_ms']<150 and report['model_calls_bounded'] and report['model_bubbles_under_25_words']
    (ROOT/'docs/revamp-load.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='sessions'},indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
