#!/usr/bin/env python3
"""Capture actual screen activity at a selected phase. Never seed illustrative data."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from playwright.async_api import async_playwright
from app.config import settings
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH',str(Path(__file__).resolve().parents[1]/'runtime/browsers'))

async def main(args):
    base=f'http://127.0.0.1:{settings.app_port}'
    async with httpx.AsyncClient(trust_env=False) as client:
        for _ in range(240):
            state=(await client.get(base+'/api/public')).json()
            if state['session']['phase']==args.phase:break
            await asyncio.sleep(.5)
        else:raise RuntimeError('Target phase not observed')
    await asyncio.sleep(args.delay)
    report=[]
    async with async_playwright() as playwright:
        browser=await playwright.chromium.launch()
        for width,height in [(1920,1080),(1280,720)]:
            page=await browser.new_page(viewport={'width':width,'height':height},reduced_motion='reduce')
            errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
            await page.goto(base+'/screen');await page.wait_for_timeout(500)
            size=await page.evaluate('({height:document.documentElement.scrollHeight,width:document.documentElement.scrollWidth})')
            file=f'runtime/phase-{args.phase}-{width}.png';await page.screenshot(path=file,full_page=True)
            report.append({'phase':args.phase,'viewport':[width,height],'document':size,'errors':errors,'file':file})
            await page.close()
        await browser.close()
    Path(f'runtime/phase-{args.phase}-layout.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if any(row['errors'] or row['document']['width']>row['viewport'][0] or row['document']['height']>row['viewport'][1] for row in report):raise SystemExit(1)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',type=int,required=True);p.add_argument('--delay',type=float,default=3);asyncio.run(main(p.parse_args()))
