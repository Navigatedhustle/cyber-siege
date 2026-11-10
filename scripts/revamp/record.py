#!/usr/bin/env python3
"""Record a full normal-speed show locally; no model or unrelated process is stopped."""
import asyncio
import json
import os
import time
from pathlib import Path
from fractions import Fraction
from harness import ROOT,Server
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'runtime/browsers')
from playwright.async_api import async_playwright

async def record():
    server=Server('revamp-record-'+str(int(time.time())),port=8096,scale=1)
    room=server.create(8);code=room['code']
    directory=Path('/home/gb300/siege/backup');directory.mkdir(parents=True,exist_ok=True)
    phases=[];started=time.monotonic();video_path=None
    try:
        async with async_playwright() as p:
            browser=await p.chromium.launch()
            ctx=await browser.new_context(viewport={'width':1920,'height':1080},record_video_dir=str(directory/'raw'),record_video_size={'width':1920,'height':1080})
            page=await ctx.new_page();errors=[]
            page.on('pageerror',lambda x:errors.append(str(x)))
            await page.goto(server.base+'/screen?room='+code)
            await page.wait_for_selector('.city-art')
            await page.evaluate("() => { const badge=document.createElement('div');badge.textContent='RECORDED BACKUP · AUTOPILOT · QR NOT ACTIVE';badge.style.cssText='position:fixed;bottom:40px;left:32px;padding:8px 12px;background:#071321;border:1px solid #ffd279;color:#ffd279;font:12px Arial;z-index:50';document.body.append(badge); }")
            server.client.post(f'/api/rooms/{code}/control',json={'command':'intensity','value':'standard'})
            server.client.post(f'/api/rooms/{code}/control',json={'command':'autopilot_all','value':True})
            server.client.post(f'/api/rooms/{code}/control',json={'command':'start'})
            last=None;debrief_start=None;last_progress=0
            while time.monotonic()-started<1000:
                current=server.client.get(f'/api/rooms/{code}').json()
                phase=(current['phase'],current['wave'])
                if phase!=last:
                    entry={'phase':phase[0],'wave':phase[1],'wall_s':round(time.monotonic()-started,2)}
                    phases.append(entry);print(json.dumps(entry),flush=True);last=phase
                if current['phase']=='debrief':
                    debrief_start=debrief_start or time.monotonic()
                    if time.monotonic()-debrief_start>=120:break
                if time.monotonic()-last_progress>30:
                    print('Recording '+str(round(time.monotonic()-started))+'s',flush=True);last_progress=time.monotonic()
                await asyncio.sleep(.5)
            else:raise AssertionError('Normal-speed session did not complete')
            video_path=await page.video.path()
            await ctx.close();await browser.close()
        calls=[json.loads(line) for line in (server.data/'model_calls.jsonl').read_text().splitlines()]
        metadata={'normal_speed':True,'viewport':[1920,1080],'phases':phases,'wall_s':round(time.monotonic()-started,2),
                  'raw_video':str(video_path),'console_errors':errors,'fallbacks':sum(c['scripted'] for c in calls),
                  'model_call_max_s':max(c['latency_s'] for c in calls),'runtime_path':str(server.data)}
        (directory/'session.json').write_text(json.dumps(metadata,indent=2))
    finally:server.close()
    # Existing local Playwright ffmpeg lacks H264. PyAV's packaged local codec provides it.
    import av
    source=av.open(str(video_path));target=av.open(str(directory/'session.mp4'),'w')
    output=target.add_stream('libx264',rate=25);output.width=1920;output.height=1080;output.pix_fmt='yuv420p'
    output.options={'crf':'24','preset':'ultrafast','threads':'8'}
    frames=0
    for frame in source.decode(video=0):
        frame=frame.reformat(width=1920,height=1080,format='yuv420p')
        frame.pts=frames;frame.time_base=Fraction(1,25)
        for packet in output.encode(frame):target.mux(packet)
        frames+=1
    for packet in output.encode():target.mux(packet)
    target.close();source.close()
    check=av.open(str(directory/'session.mp4'));stream=check.streams.video[0]
    metadata.update(mp4=str(directory/'session.mp4'),codec=stream.codec_context.name,frames=frames,duration_s=float(stream.duration*stream.time_base),width=stream.width,height=stream.height)
    assert stream.width==1920 and stream.height==1080 and metadata['duration_s']>=800
    check.close()
    (directory/'session.json').write_text(json.dumps(metadata,indent=2))
    (ROOT/'docs/revamp-recording.json').write_text(json.dumps({k:v for k,v in metadata.items() if k!='raw_video'},indent=2))
    print(json.dumps(metadata,indent=2))

if __name__=='__main__':asyncio.run(record())
