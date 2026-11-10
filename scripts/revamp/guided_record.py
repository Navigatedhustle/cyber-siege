#!/usr/bin/env python3
"""Normal-speed 1080p record of the current guided story; all files stay private/local."""
import asyncio,json,os,time
from fractions import Fraction
from pathlib import Path
from harness import ROOT,Server
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'runtime/browsers')
from playwright.async_api import async_playwright

async def main():
 server=Server('guided-record-'+str(int(time.time())),8096,scale=1)
 directory=Path('/home/gb300/siege/backup');raw=directory/'guided-raw';raw.mkdir(parents=True,exist_ok=True)
 errors=[];started=time.monotonic();events=[]
 try:
  async with async_playwright() as p:
   browser=await p.chromium.launch()
   context=await browser.new_context(viewport={'width':1920,'height':1080},record_video_dir=str(raw),record_video_size={'width':1920,'height':1080})
   page=await context.new_page();page.on('pageerror',lambda x:errors.append(str(x)))
   await page.goto(server.base+'/');await page.get_by_role('button',name='Start the story').wait_for()
   await page.evaluate("() => {const b=document.createElement('div');b.textContent='RECORDED · GUIDED DEMO';b.style.cssText='position:fixed;right:10px;bottom:8px;padding:6px;background:#071321;border:1px solid #ffd279;color:#ffd279;font:10px Arial;z-index:100';document.body.append(b);}")
   await asyncio.sleep(3);await page.get_by_role('button',name='Start the story').click()
   for wave in [1,2,3]:
    await page.get_by_role('button',name='Deploy local AI squad').wait_for()
    events.append({'wave':wave,'stage':'policy_gate','seconds':round(time.monotonic()-started,2)});print(json.dumps(events[-1]),flush=True)
    await asyncio.sleep(5)
    await page.get_by_role('button',name='Deploy local AI squad').click()
    events.append({'wave':wave,'stage':'squad_deployed','seconds':round(time.monotonic()-started,2)})
    label='Build my Account Action Card' if wave==3 else 'Continue to the next challenge'
    await page.get_by_role('button',name=label).wait_for(timeout=45000)
    events.append({'wave':wave,'stage':'human_review_and_value','seconds':round(time.monotonic()-started,2)});print(json.dumps(events[-1]),flush=True)
    await asyncio.sleep(7)
    await page.get_by_role('button',name=label).click()
   await page.locator('#account').wait_for();await asyncio.sleep(15)
   source=await page.video.path();await context.close();await browser.close()
  calls=[json.loads(x) for x in (server.data/'model_calls.jsonl').read_text().splitlines()]
 finally:server.close()
 import av
 video=directory/'guided-session.mp4';reader=av.open(str(source));writer=av.open(str(video),'w')
 stream=writer.add_stream('libx264',rate=25);stream.width=1920;stream.height=1080;stream.pix_fmt='yuv420p';stream.options={'crf':'24','preset':'ultrafast','threads':'8'}
 count=0
 for frame in reader.decode(video=0):
  frame=frame.reformat(width=1920,height=1080,format='yuv420p');frame.pts=count;frame.time_base=Fraction(1,25)
  for packet in stream.encode(frame):writer.mux(packet)
  count+=1
 for packet in stream.encode():writer.mux(packet)
 writer.close();reader.close()
 with av.open(str(video)) as check:
  v=check.streams.video[0];duration=float(v.duration*v.time_base)
  assert v.width==1920 and v.height==1080 and duration>100
 report={'path':str(video),'duration_s':duration,'width':1920,'height':1080,'codec':'h264','frames':count,'normal_speed':True,'silent':True,
         'events':events,'console_errors':errors,'actual_model_calls':len(calls),'fallback_count':sum(c['scripted'] for c in calls),
         'cloud_lane':'labeled scripted customer-policy block; no cloud model called','city_actions':'fictional runbook only; production approval required','bytes':video.stat().st_size}
 (ROOT/'docs/guided-story-recording.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
 assert not errors

if __name__=='__main__':asyncio.run(main())
