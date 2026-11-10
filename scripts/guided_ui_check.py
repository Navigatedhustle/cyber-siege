#!/usr/bin/env python3
"""Verify two independent, no-sign-in browser experiences using the real models."""
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
    if settings.app_port==8080:raise SystemExit('Use an isolated review app, e.g. APP_PORT=8088. This check creates a rehearsal.')
    base=f'http://127.0.0.1:{settings.app_port}'
    report={'label':'REHEARSAL','page_errors':[],'requests_outside_app':[],'login_requests':[]}
    async with httpx.AsyncClient(base_url=base,trust_env=False) as c:
        (await c.post('/api/control',json={'action':'create','label':'REHEARSAL'})).raise_for_status()
        async def snapshot():return (await c.get('/api/facilitator')).json()
        async def wait_for(test):
            for _ in range(200):
                value=await snapshot()
                if test(value):return value
                await asyncio.sleep(.2)
            raise RuntimeError('Expected individual state did not arrive')
        async with async_playwright() as p:
            browser=await p.chromium.launch()
            contexts=[await browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True,reduced_motion='reduce',accept_downloads=True) for _ in range(2)]
            pages=[await context.new_page() for context in contexts]
            def watch(page):
                page.on('pageerror',lambda error:report['page_errors'].append(str(error)))
                page.on('request',lambda request:report['requests_outside_app'].append(request.url) if not request.url.startswith(base+'/') else report['login_requests'].append(request.url) if '/api/login' in request.url else None)
            for page in pages:
                watch(page);await page.goto(base+'/');button=page.get_by_role('link',name='Start experience',exact=False).first
                bounds=await button.bounding_box();report['start_above_fold']=bounds['y']+bounds['height']<=844
                await button.click();await page.get_by_role('heading',name='Where do you start?',exact=True).wait_for()
                assert await page.locator('input[type=password],#join,#joincode,#name').count()==0
            a,b=pages;report['no_registration_or_room_code']=True
            await wait_for(lambda s:s['connected_phones']==2)
            await c.post('/api/control',json={'action':'next'})
            await a.reload();await a.get_by_role('heading',name='Where do you start?',exact=True).wait_for();report['room_controls_do_not_advance_individual']=True
            await a.click('[data-pick=invoice]');await a.locator('[data-pick=invoice].chosen').wait_for();await a.reload();await a.locator('[data-pick=invoice].chosen').wait_for();report['reload_restores_choice']=True
            await a.locator('[data-personal=investigate]').click();await a.get_by_role('heading',name='Evidence timeline',exact=True).wait_for(timeout=75000)
            await b.get_by_role('heading',name='Where do you start?',exact=True).wait_for();report['other_participant_stays_at_own_step']=True
            await a.locator('[data-log]').first.click();await a.locator('#raw[open]').wait_for();await a.click('#close-log');report['raw_evidence_opens']=True
            await a.locator('[data-personal=twist]').click();await a.locator('#decision').wait_for();await a.select_option('#decision-choice','escalate')
            for key in ['token','session','twist']:await a.check(f'input[name=evidence][value={key}]')
            await a.click('#decision button');await a.locator('.review').nth(1).wait_for(timeout=60000)
            await a.screenshot(path=str(ROOT/'runtime/individual-reviews.png'),full_page=True)
            await a.locator('[data-personal=next]').click();await a.locator('[data-personal=reveal]').wait_for()
            for beat in range(6):
                if beat==2:
                    await a.locator('[data-personal=overdrive]').click();await wait_for(lambda s:any(t.get('progress',{}).get('overdrive')=='done' for t in s['teams']))
                await a.locator('[data-personal=reveal]').click()
                await a.get_by_text(f'YOUR REVEAL / {beat+2} OF 7',exact=False).wait_for()
            await a.locator('[data-personal=next]').click();await a.locator('#card').wait_for();await a.fill('#account','Fictional individual review');await a.select_option('#industry','technology');await a.fill('#owner','Individual Seller')
            state=await snapshot();person=next(t for t in state['teams'] if t.get('decision'))
            await c.post('/api/control',json={'action':'rename','team_id':person['id'],'name':'Participant review'})
            await a.get_by_text('Your individual experience · Participant review',exact=True).wait_for()
            report['draft_preserved']=await a.input_value('#account')=='Fictional individual review'
            await a.click('#card button');await a.get_by_role('link',name='Download your PDF',exact=True).wait_for()
            async with a.expect_download() as pending:await a.get_by_role('link',name='Download your PDF',exact=True).click()
            pdf=await pending.value;await pdf.save_as(ROOT/'runtime/individual-card.pdf');report['pdf_downloaded']=(ROOT/'runtime/individual-card.pdf').read_bytes().startswith(b'%PDF')
            await b.get_by_role('heading',name='Where do you start?',exact=True).wait_for();report['independent_end_to_end']=True
            presenter=await contexts[0].new_page();watch(presenter);await presenter.goto(base+'/facilitator');await presenter.wait_for_selector('#console');report['presenter_has_no_login_form']=await presenter.locator('#login,input[type=password]').count()==0
            final=await snapshot();person=next(t for t in final['teams'] if t.get('card_id'));report.update(session_id=final['session']['id'],cached=person['investigation'].get('cached'),independent_producers=[r.get('model') for r in person['reviews'] if not r.get('error')],commitments=final['commitment_count'])
            await browser.close()
    required=['start_above_fold','no_registration_or_room_code','room_controls_do_not_advance_individual','reload_restores_choice','other_participant_stays_at_own_step','raw_evidence_opens','draft_preserved','pdf_downloaded','independent_end_to_end','presenter_has_no_login_form']
    report['passed']=all(report[k] for k in required) and not report['page_errors'] and not report['requests_outside_app'] and not report['login_requests'] and not report['cached'] and set(report['independent_producers'])=={'hero','challenger'}
    (ROOT/'runtime/individual-ui-proof.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
