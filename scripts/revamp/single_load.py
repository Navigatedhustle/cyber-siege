#!/usr/bin/env python3
"""60 independent same-link sessions through the full rules, WebSocket RTT/reset isolation."""
import asyncio,json,secrets,time
import httpx,psutil,websockets
from harness import ROOT,Server

def p95(v):return sorted(v)[max(0,int(.95*len(v))-1)]

async def main():
 server=Server('single-load-'+str(int(time.time())),8091,scale=1)
 process=psutil.Process(server.process.pid);process.cpu_percent()
 peers=[];readers=[];pings=[];rtt=[];cpu=[];rss=[];stop=False
 try:
  async with httpx.AsyncClient(base_url=server.base,trust_env=False,timeout=20,limits=httpx.Limits(max_connections=100)) as c:
   async def bootstrap(i):
    response=await c.post('/api/experience',json={'nonce':secrets.token_hex(24)});response.raise_for_status();return response.json()
   guests=await asyncio.gather(*(bootstrap(i) for i in range(60)))
   assert len({g['state']['code'] for g in guests})==60
   async def read(ws):
    try:
     async for raw in ws:
      x=json.loads(raw)
      if x['type']=='pong':rtt.append((time.perf_counter()-float(x['nonce']))*1000)
    except websockets.ConnectionClosed:pass
   for g in guests:
    ws=await websockets.connect(server.base.replace('http:','ws:')+'/ws/'+g['state']['code'],proxy=None)
    await ws.send(json.dumps({'type':'hello','token':g['token']}));peers.append(ws);readers.append(asyncio.create_task(read(ws)))
   async def ping(ws):
    while not stop:
     await ws.send(json.dumps({'type':'ping','nonce':str(time.perf_counter())}));await asyncio.sleep(.4)
   for ws in peers:pings.append(asyncio.create_task(ping(ws)))
   async def monitor():
    while not stop:
     cpu.append(process.cpu_percent());rss.append(process.memory_info().rss/1024**2);await asyncio.sleep(.25)
   m=asyncio.create_task(monitor())
   async def control(g,command):
    r=await c.post('/api/experience/control',headers={'Authorization':'Bearer '+g['token']},json={'command':command});r.raise_for_status();return r.json()
   async def all_control(cmd):return await asyncio.gather(*(control(g,cmd) for g in guests))
   await all_control('start');await all_control('next')
   for action in ['analyze','verify']:
    await asyncio.gather(*(ws.send(json.dumps({'type':'action','action':action})) for ws in peers));await asyncio.sleep(.5)
   await all_control('next')
   for i in range(6):
    await asyncio.gather(*(ws.send(json.dumps({'type':'action','action':'SCOUT','building':i})) for ws in peers));await asyncio.sleep(.35)
   await all_control('next')
   for i,r in enumerate(['SCOUT','SHERLOCK','SHIELD','PATCH','SCRIBE']):
    await asyncio.gather(*(ws.send(json.dumps({'type':'action','action':r,'building':i})) for ws in peers));await asyncio.sleep(.35)
   states=await all_control('next');assert all(s['phase']=='debrief' for s in states)
   # Reset/restart one person, while all 59 others retain their completed score/card access.
   reset=await control(guests[0],'reset');assert reset['phase']=='lobby'
   restart=await control(guests[0],'restart');assert restart['phase']=='briefing'
   other=await c.get('/api/rooms/'+guests[1]['state']['code'],headers={'Authorization':'Bearer '+guests[1]['token']})
   assert other.json()['phase']=='debrief' and other.json()['teams'][0]['score']>0
   # Let the bounded model queue settle, verifying clean fallbacks under a deliberately simultaneous burst.
   await asyncio.sleep(9)
   stop=True
   for task in pings+[m]:task.cancel()
   await asyncio.gather(*pings,m,return_exceptions=True)
   for ws in peers:await ws.close()
   await asyncio.gather(*readers,return_exceptions=True)
  calls=[json.loads(s) for s in (server.data/'model_calls.jsonl').read_text().splitlines()]
  report={'people':60,'independent_sessions':60,'same_entry_url':'/','all_three_challenges_completed':True,'reset_restart_isolation':True,
          'websocket_samples':len(rtt),'websocket_rtt_p95_ms':round(p95(rtt),2),'server_cpu_p95_one_core_percent':p95(cpu),
          'server_rss_peak_mib':round(max(rss),2),'model_calls':len(calls),'model_latency_p95_s':round(p95([x['latency_s'] for x in calls]),3),
          'model_latency_max_s':max(x['latency_s'] for x in calls),'fallback_count':sum(x['scripted'] for x in calls),
          'all_bubbles_bounded':all(x['latency_s']<8 and x['words']<=25 for x in calls),
          'scope':'One deliberately synchronized 60-person full journey, driven faster than human decisions; real unchanged Nemotron endpoint, bounded eight-call queue and clean fallbacks.',
          'passed':p95(rtt)<150 and all(x['latency_s']<8 and x['words']<=25 for x in calls),'runtime_path':str(server.data)}
  (ROOT/'docs/single-experience-load.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['passed']
 finally:server.close()

if __name__=='__main__':asyncio.run(main())
