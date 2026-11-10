#!/usr/bin/env python3
"""Create a labeled UI rehearsal and check every projector phase without inference."""
import asyncio
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.config import settings,ROOT
import httpx
from playwright.async_api import async_playwright
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH',str(ROOT/'runtime/browsers'))

async def main():
    report=[]
    async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{settings.app_port}',trust_env=False) as client:
        (await client.post('/api/login',json={'pin':settings.facilitator_pin})).raise_for_status()
        async def command(action,**extra):
            response=await client.post('/api/control',json={'action':action,**extra});response.raise_for_status();return response.json()
        state=await command('create',label='REHEARSAL')
        for index in range(15):
            (await client.post('/api/join',json={'name':f'Projector QA team {index+1:02}','join_code':state['session']['join_code']})).raise_for_status()
        async with async_playwright() as p:
            browser=await p.chromium.launch()
            pages=[await browser.new_page(viewport={'width':w,'height':h},reduced_motion='reduce') for w,h in [(1920,1080),(1280,720)]]
            for phase in range(1,6):
                if phase>1:await command('next')
                for beat in range(8) if phase==4 else [0]:
                    if beat:await command('reveal')
                    for page in pages:
                        await page.goto(f'http://127.0.0.1:{settings.app_port}/screen');await page.wait_for_timeout(200)
                        size=await page.evaluate('({width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight})')
                        row={'phase':phase,'beat':beat,'viewport':page.viewport_size,'document':size}
                        row['passed']=size['width']<=page.viewport_size['width'] and size['height']<=page.viewport_size['height']+2
                        report.append(row)
                        if not row['passed']:await page.screenshot(path=f'runtime/overflow-phase-{phase}-beat-{beat}-{page.viewport_size["width"]}.png',full_page=True)
            await browser.close()
    (ROOT/'runtime/projector-all-phases.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if not all(row['passed'] for row in report):raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
