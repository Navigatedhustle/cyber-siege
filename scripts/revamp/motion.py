#!/usr/bin/env python3
"""Foreground 1080p motion measurement, kept separate from multi-page screenshot workload."""
import asyncio
import json
import os
import time
from harness import ROOT,Server
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'runtime/browsers')
from playwright.async_api import async_playwright

async def main():
    server=Server('revamp-motion-'+str(int(time.time())),8098,scale=1)
    try:
        room=server.create(8);code=room['code']
        server.client.post(f'/api/rooms/{code}/control',json={'command':'intensity','value':'standard'})
        for command in ['start','next','next','next']:
            server.client.post(f'/api/rooms/{code}/control',json={'command':command})
        async with async_playwright() as p:
            browser=await p.chromium.launch()
            page=await browser.new_page(viewport={'width':1920,'height':1080})
            await page.goto(server.base+'/screen?room='+code)
            await page.wait_for_selector('.city-art')
            await page.bring_to_front();await asyncio.sleep(1)
            intervals=await page.evaluate('''() => new Promise(resolve => {
                const values=[];let previous;
                function frame(t){if(previous!==undefined)values.push(t-previous);previous=t;
                    if(values.length>=300)resolve(values);else requestAnimationFrame(frame);}
                requestAnimationFrame(frame);
            })''')
            await browser.close()
        report={'scope':'Foreground single Chromium projector page, 1920x1080, standard motion, actual live WebSocket snapshots, 8-team Phisher wave with discrete building beacons and Canvas envelope rain.',
                'frames':len(intervals),'average_fps':round(1000/(sum(intervals)/len(intervals)),2),'frame_interval_p95_ms':round(sorted(intervals)[284],2),
                'target_fps':60}
        report['near_60fps']=report['average_fps']>=55 and report['frame_interval_p95_ms']<25
        (ROOT/'docs/revamp-motion.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    finally:server.close()

if __name__=='__main__':asyncio.run(main())
