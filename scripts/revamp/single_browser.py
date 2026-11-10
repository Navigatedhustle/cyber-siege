#!/usr/bin/env python3
"""One URL, two isolated browser journeys, true UI reset/restart, PDF and responsive proof."""
import asyncio,json,os,time
from pathlib import Path
from harness import ROOT,Server
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'runtime/browsers')
from playwright.async_api import async_playwright

async def main():
    server=Server('single-browser-'+str(int(time.time())),8092,scale=1)
    shots=ROOT/'docs/screenshots/single';shots.mkdir(parents=True,exist_ok=True)
    errors=[];requests=[];checks=[]
    def watch(page):
        page.on('pageerror',lambda x:errors.append(str(x)))
        page.on('console',lambda x:errors.append(x.text) if x.type=='error' else None)
        page.on('request',lambda x:requests.append(x.url))
    try:
      async with async_playwright() as p:
        browser=await p.chromium.launch()
        desktop=await browser.new_context(viewport={'width':1920,'height':1080},accept_downloads=True)
        mobile=await browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        a=await desktop.new_page();b=await mobile.new_page();watch(a);watch(b)
        await asyncio.gather(a.goto(server.base+'/'),b.goto(server.base+'/'))
        await asyncio.gather(a.get_by_role('button',name='Start experience').wait_for(),b.get_by_role('button',name='Start experience').wait_for())
        assert await a.locator('input').count()==0
        await a.get_by_role('button',name='Share this experience').click()
        await a.locator('.share-qr').wait_for()
        assert await a.locator('#share-url').input_value()==server.base+'/'
        await a.get_by_role('button',name='Done',exact=True).click()
        assert not await a.locator('a[href*="facilitator"]').count()
        await a.screenshot(path=str(shots/'01-start-desktop.png'),full_page=True)
        await b.screenshot(path=str(shots/'start-phone.png'),full_page=True)
        await a.get_by_role('button',name='Start experience').click()
        await a.get_by_role('button',name='Take on the first challenge').click()
        await a.get_by_role('button',name='Ask SHERLOCK to check it').wait_for()
        assert await b.get_by_role('button',name='Start experience').is_visible()
        await a.get_by_role('button',name='Ask SHERLOCK to check it').click()
        await b.get_by_role('button',name='Start experience').click()
        await b.get_by_role('button',name='Take on the first challenge').click()
        await b.get_by_role('button',name='Ask SHERLOCK to check it').click()
        await a.get_by_role('button',name='Call the vendor to verify').click()
        await a.get_by_role('button',name='Continue to the next challenge').wait_for()
        await a.screenshot(path=str(shots/'02-first-lesson.png'),full_page=True)
        # B's reset does not move A or clear A's completion.
        await b.get_by_role('button',name='Reset',exact=True).click()
        await b.get_by_role('button',name='Reset my experience',exact=True).click()
        await b.get_by_role('button',name='Start experience').wait_for()
        assert await a.get_by_role('button',name='Continue to the next challenge').is_visible()
        # Restart is available from the welcome state and begins a fresh briefing.
        await b.get_by_role('button',name='Restart ↻',exact=True).click()
        await b.get_by_role('button',name='Restart now',exact=True).click()
        await b.get_by_role('button',name='Take on the first challenge').wait_for()
        checks.append({'two_simultaneous_browsers':'same URL, independent phase/actions; B reset/restart preserved A','passed':True})
        await a.get_by_role('button',name='Continue to the next challenge').click()
        for i in range(6):
            await a.locator(f'[data-building="{i}"]').click()
            await asyncio.sleep(.1)
        await a.get_by_role('button',name='Continue to the next challenge').wait_for()
        await a.get_by_role('button',name='Continue to the next challenge').click()
        await a.locator('[data-action="SCOUT"][data-building="0"]').wait_for()
        await a.screenshot(path=str(shots/'03-recovery-challenge.png'),full_page=True)
        for i,r in enumerate(['SCOUT','SHERLOCK','SHIELD','PATCH','SCRIBE']):
            await a.locator(f'[data-action="{r}"][data-building="{i}"]').click();await asyncio.sleep(.1)
        await a.get_by_role('button',name='Build my Account Action Card').click()
        await a.locator('#account').fill('Your next customer')
        await a.locator('#next-step').fill('Book a local AI discovery session with the technical champion.')
        await a.screenshot(path=str(shots/'04-action-card-desktop.png'),full_page=True)
        async with a.expect_download() as download:
            await a.get_by_role('button',name='Download my Account Action Card').click()
        file=await download.value
        destination=ROOT/'runtime/account-card-proof/browser-download.pdf';destination.parent.mkdir(exist_ok=True,parents=True)
        await file.save_as(str(destination));assert destination.read_bytes().startswith(b'%PDF')
        await a.reload();await a.locator('#account').wait_for()
        assert await a.locator('#account').input_value()=='Your next customer'
        for width,height in [(1920,1080),(1366,768),(390,844),(360,800)]:
            await a.set_viewport_size({'width':width,'height':height});await asyncio.sleep(.25)
            overflow=await a.evaluate('document.documentElement.scrollWidth>innerWidth')
            assert not overflow, f'Overflow at {width}x{height}'
            assert await a.get_by_role('button',name='Reset',exact=True).is_visible()
            assert await a.get_by_role('button',name='Restart ↻',exact=True).is_visible()
            checks.append({'viewport':[width,height],'horizontal_overflow':overflow,'reset_restart_visible':True})
            if width==390:await a.screenshot(path=str(shots/'action-card-phone.png'),full_page=True)
        # Verify the actual reset confirmation and restart from a completed game.
        await a.get_by_role('button',name='Reset',exact=True).click()
        await a.get_by_role('button',name='Keep playing').click()
        assert await a.locator('#card-form').count()==1
        await a.get_by_role('button',name='Restart ↻',exact=True).click()
        await a.get_by_role('button',name='Restart now',exact=True).click()
        await a.get_by_role('button',name='Take on the first challenge').wait_for()
        await a.get_by_role('button',name='Reset',exact=True).click()
        await a.get_by_role('button',name='Reset my experience',exact=True).click()
        await a.get_by_role('button',name='Start experience').wait_for()
        checks.append({'card_download_resume_restart_reset':'passed','passed':True})
        await browser.close()
        firefox=await p.firefox.launch()
        page=await firefox.new_page(viewport={'width':390,'height':844});watch(page)
        await page.goto(server.base+'/');await page.get_by_role('button',name='Start experience').wait_for()
        await page.get_by_role('button',name='Start experience').click();await page.get_by_role('button',name='Take on the first challenge').wait_for()
        checks.append({'engine':'Firefox','single_entry_start':'passed'})
        await firefox.close()
      report={'passed':not errors,'checks':checks,'console_errors':errors,'local_requests_only':all(url.startswith(server.base) or url.startswith(server.base.replace('http:','ws:')) for url in requests),'screenshots':str(shots),'physical_devices_tested':False}
      (ROOT/'docs/single-experience-browser.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
      assert report['passed'] and report['local_requests_only']
    finally:server.close()

if __name__=='__main__':asyncio.run(main())
