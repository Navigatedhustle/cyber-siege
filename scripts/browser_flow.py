#!/usr/bin/env python3
"""A real browser completes one labeled rehearsal through the public UI and APIs."""
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

async def main():
    report={'label':'REHEARSAL','page_errors':[]}
    async with httpx.AsyncClient(base_url=f'http://127.0.0.1:{settings.app_port}',trust_env=False) as admin:
        response=await admin.post('/api/login',json={'pin':settings.facilitator_pin});response.raise_for_status()
        async def command(action,**extra):
            r=await admin.post('/api/control',json={'action':action,**extra});r.raise_for_status();return r.json()
        state=await command('create',label='REHEARSAL');report['session_id']=state['session']['id']
        async with async_playwright() as playwright:
            browser=await playwright.chromium.launch()
            context=await browser.new_context(viewport={'width':390,'height':844},accept_downloads=True)
            page=await context.new_page();page.on('pageerror',lambda error:report['page_errors'].append(str(error)))
            await page.goto(f'http://127.0.0.1:{settings.app_port}/play')
            await page.fill('#name','Browser QA');await page.fill('#joincode',state['session']['join_code'])
            await page.click('#join button');await page.get_by_role('heading',name='You are in.').wait_for()
            await command('next');await page.locator('[data-pick="invoice"]').wait_for()
            await page.click('[data-pick="invoice"]');await page.wait_for_selector('[data-pick="invoice"].chosen')
            await page.reload();await page.wait_for_selector('[data-pick="invoice"].chosen');report['reconnect_restored']=True
            await command('next');await page.click('#launch')
            await page.get_by_role('heading',name='Evidence timeline',exact=True).wait_for(timeout=75000)
            await page.screenshot(path='runtime/browser-phone-evidence.png',full_page=True)
            await page.locator('[data-log]').first.click();await page.wait_for_selector('#raw[open]');await page.click('#close-log');report['raw_evidence_opens']=True
            await command('twist');await page.locator('#decision').wait_for()
            await page.select_option('#decision-choice','escalate')
            for value in ['token','session','twist']:await page.check(f'input[name="evidence"][value="{value}"]')
            await page.click('#decision button');await page.get_by_text('Decision received:',exact=False).wait_for()
            await page.locator('.review').nth(1).wait_for(timeout=60000)
            await page.screenshot(path='runtime/browser-phone-reviews.png',full_page=True)
            await command('next');await command('next')
            await page.locator('#card').wait_for();await page.fill('#account','<script>Fictional QA account</script>');await page.select_option('#industry','manufacturing');await page.fill('#owner','Carlos QA')
            await page.click('#card button');await page.get_by_role('link',name='Download your PDF').wait_for()
            async with page.expect_download() as download:
                await page.get_by_role('link',name='Download your PDF').click()
            result=await download.value;await result.save_as('runtime/browser-flow-card.pdf');report['pdf_downloaded']=Path('runtime/browser-flow-card.pdf').read_bytes().startswith(b'%PDF')
            report['phone_horizontal_overflow']=await page.evaluate('document.documentElement.scrollWidth>innerWidth')
            state=(await admin.get('/api/facilitator')).json();team=state['teams'][0]
            report['cached']=team['investigation'].get('cached');report['duration_seconds']=team['investigation'].get('duration_seconds');report['independent_producers']=[r.get('model') for r in team.get('reviews',[]) if not r.get('error')]
            report['commitments']=state['commitment_count']
            await browser.close()
    report['passed']=not report['page_errors'] and report['pdf_downloaded'] and not report['cached'] and not report['phone_horizontal_overflow'] and len(set(report['independent_producers']))==2
    Path('runtime/browser-flow-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)
if __name__=='__main__':asyncio.run(main())
