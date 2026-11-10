#!/usr/bin/env python3
"""Use isolated browser state to verify layouts without changing session phase.

Run after a rehearsal is parked at the desired phase. Screenshots are private
runtime artifacts; the JSON report contains only layout checks and page errors.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from playwright.async_api import async_playwright
from app.config import settings
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH',str(Path(__file__).resolve().parents[1]/'runtime/browsers'))

async def main():
    report=[]
    async with async_playwright() as playwright:
        for engine in ['chromium','firefox','webkit']:
            try:
                browser=await getattr(playwright,engine).launch()
            except Exception as exc:
                report.append({'engine':engine,'available':False,'error':str(exc)[:300]});continue
            for surface,width,height in [('welcome',1440,1000),('welcome',390,844),('screen',1920,1080),('screen',1280,720),('play',390,844),('play',360,800),('facilitator',1440,1000),('facilitator',1280,800),('facilitator',390,844)]:
                context=await browser.new_context(viewport={'width':width,'height':height},reduced_motion='reduce')
                page=await context.new_page();errors=[];requests=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('request',lambda request:requests.append(request.url))
                await page.goto(f'http://127.0.0.1:{settings.app_port}/'+('' if surface=='welcome' else surface))
                await page.wait_for_timeout(800)
                if surface=='facilitator':
                    await page.wait_for_selector('#console:not(.hidden)')
                overflow=await page.evaluate('document.documentElement.scrollWidth>innerWidth')
                vertical=await page.evaluate('document.documentElement.scrollHeight>innerHeight+2') if surface=='screen' else False
                title=await page.title()
                await page.screenshot(path=f'runtime/browser-{engine}-{surface}-{width}.png',full_page=True)
                local_only=all(url.startswith(f'http://127.0.0.1:{settings.app_port}/') for url in requests)
                report.append({'engine':engine,'available':True,'surface':surface,'viewport':[width,height],'horizontal_overflow':overflow,'projector_vertical_overflow':vertical,'page_errors':errors,'local_requests_only':local_only,'title':title})
                await context.close()
            await browser.close()
    Path('runtime/browser-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if not all(any(row['engine']==engine and row.get('available') for row in report) for engine in ['chromium','firefox']):raise SystemExit('Required Chromium and Firefox checks did not run')
    if any(row.get('horizontal_overflow') or row.get('projector_vertical_overflow') or row.get('page_errors') or row.get('local_requests_only') is False for row in report):raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
