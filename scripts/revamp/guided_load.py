#!/usr/bin/env python3
"""60 independent guided stories, live shared analysis and one deployment per incident."""
import asyncio,json,secrets,time
import httpx,psutil,websockets
from harness import ROOT,Server

def p95(xs):return sorted(xs)[max(0,int(len(xs)*.95)-1)]

async def main():
 server=Server('guided-load-'+str(int(time.time())),8091,scale=.08)
 process=psutil.Process(server.process.pid);process.cpu_percent()
 peers=[];reads=[];pings=[];rtt=[];rss=[];cpu=[];latest=[None]*60;stop=False;mon=None
 try:
  async with httpx.AsyncClient(base_url=server.base,timeout=20,trust_env=False,limits=httpx.Limits(max_connections=100)) as c:
   async def bootstrap():
    r=await c.post('/api/experience',json={'nonce':secrets.token_hex(24)});r.raise_for_status();return r.json()
   people=await asyncio.gather(*(bootstrap() for _ in range(60)))
   assert len({x['state']['code'] for x in people})==60
   async def read(i,ws):
    try:
     async for raw in ws:
      x=json.loads(raw)
      if x.get('state'):latest[i]=x['state']
      if x['type']=='pong':rtt.append((time.perf_counter()-float(x['nonce']))*1000)
    except websockets.ConnectionClosed:pass
   for i,g in enumerate(people):
    ws=await websockets.connect(server.base.replace('http:','ws:')+'/ws/'+g['state']['code'],proxy=None)
    await ws.send(json.dumps({'type':'hello','token':g['token']}));peers.append(ws);reads.append(asyncio.create_task(read(i,ws)))
   async def ping(ws):
    while not stop:
     await ws.send(json.dumps({'type':'ping','nonce':str(time.perf_counter())}));await asyncio.sleep(.5)
   pings=[asyncio.create_task(ping(ws)) for ws in peers]
   async def monitor():
    while not stop:
     cpu.append(process.cpu_percent());rss.append(process.memory_info().rss/1024**2);await asyncio.sleep(.25)
   mon=asyncio.create_task(monitor())
   async def control(g,command):
    r=await c.post('/api/experience/control',headers={'Authorization':'Bearer '+g['token']},json={'command':command});r.raise_for_status();return r.json()
   async def all_control(cmd):return await asyncio.gather(*(control(g,cmd) for g in people))
   async def wait_all(phase,wave):
    started=time.monotonic()
    while time.monotonic()-started<15:
     if all(s and s['phase']==phase and s['wave']==wave for s in latest):return
     await asyncio.sleep(.05)
    raise AssertionError('Guided progression did not finish: '+repr([(x['phase'],x['wave'],x.get('story',{}).get('cursor')) if x else None for x in latest]))
   first=await all_control('start')
   assert all(x['story']['stage']=='cloud_check' and x['story']['cloud']['actual_api_request'] is False for x in first)
   for wave in [1,2,3]:
    started=time.monotonic()
    while not all(s and s['wave']==wave and s.get('story',{}).get('stage')=='blocked' for s in latest):
     assert time.monotonic()-started<10,'Cloud preflight did not finish'
     await asyncio.sleep(.05)
    await all_control('deploy');await wait_all('translate',wave)
    assert all(len(s['story']['events'])==5 and s['story']['human_review']['status']=='human_review_required' for s in latest)
    await all_control('next')
    await wait_all('wave' if wave<3 else 'debrief',min(3,wave+1))
   assert all(len(x['human_reviews'])==3 and x['teams'][0]['score']==1500 for x in latest)
   before=latest[1]['teams'][0]['score']
   reset=await control(people[0],'reset');assert reset['phase']=='lobby'
   restart=await control(people[0],'restart');assert restart['story']['stage']=='cloud_check'
   assert latest[1]['phase']=='debrief' and latest[1]['teams'][0]['score']==before
   await asyncio.sleep(.5)
   stop=True
   for t in pings+[mon]:t.cancel()
   await asyncio.gather(*pings,mon,return_exceptions=True)
   for ws in peers:await ws.close()
   await asyncio.gather(*reads,return_exceptions=True)
  calls=[json.loads(x) for x in (server.data/'model_calls.jsonl').read_text().splitlines()]
  report={'people':60,'independent_sessions':60,'incidents_each':3,'deploy_clicks_each':3,'automatic_roles_each':15,
          'all_scenes_finished':True,'human_reviews_each':3,'cloud_model_requests':0,'cloud_lane_label':'scripted customer policy',
          'reset_restart_isolation':True,'websocket_samples':len(rtt),'websocket_rtt_p95_ms':round(p95(rtt),2),
          'server_cpu_p95_one_core_percent':p95(cpu),'server_rss_peak_mib':round(max(rss),2),
          'actual_model_calls':len(calls),'model_latency_p95_s':round(p95([x['latency_s'] for x in calls]),3),
          'model_latency_max_s':max(x['latency_s'] for x in calls),'fallback_count':sum(x['scripted'] for x in calls),
          'all_model_bubbles_bounded':all(x['latency_s']<8 and x['words']<=25 for x in calls),
          'scope':'Three 0.08-scale guided incidents per person, synchronized protocol stress; real unchanged local model, timed city-only runbook, in-app human queue, no cloud calls.',
          'runtime_path':str(server.data)}
  report['passed']=report['all_model_bubbles_bounded'] and report['websocket_rtt_p95_ms']<150
  (ROOT/'docs/guided-story-load.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['passed']
 finally:
  stop=True
  for t in pings+([mon] if mon else []):t.cancel()
  for ws in peers:
   if ws.close_code is None:await ws.close()
  await asyncio.gather(*reads,return_exceptions=True)
  server.close()

if __name__=='__main__':asyncio.run(main())
