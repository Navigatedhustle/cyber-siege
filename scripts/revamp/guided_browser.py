#!/usr/bin/env python3
"""Guided browser story: policy truth labels, one-click automation, recovery, human queue, card."""
import asyncio,json,os,time
from pathlib import Path
from harness import ROOT,Server
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'runtime/browsers')
from playwright.async_api import async_playwright

async def main():
 server=Server('guided-browser-'+str(int(time.time())),8092,scale=.25)
 shots=ROOT/'docs/screenshots/guided';shots.mkdir(parents=True,exist_ok=True)
 errors=[];requests=[];checks=[]
 def watch(page):
  page.on('pageerror',lambda x:errors.append(str(x)))
  page.on('console',lambda x:errors.append(x.text) if x.type=='error' else None)
  page.on('request',lambda x:requests.append(x.url))
 try:
  async with async_playwright() as p:
   browser=await p.chromium.launch()
   ac=await browser.new_context(viewport={'width':1920,'height':1080},accept_downloads=True)
   bc=await browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
   a=await ac.new_page();b=await bc.new_page();watch(a);watch(b)
   await asyncio.gather(a.goto(server.base+'/'),b.goto(server.base+'/'))
   await a.get_by_role('button',name='Start the story').wait_for()
   await a.screenshot(path=str(shots/'01-welcome.png'),full_page=True)
   await a.get_by_role('button',name='Start the story').click()
   await a.locator('.request-checking').wait_for()
   assert not await a.get_by_role('button',name='Deploy local AI squad').count()
   await a.screenshot(path=str(shots/'00-cloud-request-check.png'),full_page=True)
   await a.get_by_role('button',name='Deploy local AI squad').wait_for()
   assert 'DENIED' in await a.locator('.request-denied h2').inner_text()
   assert 'INV-104' in await a.locator('.evidence-console pre').inner_text()
   assert await a.locator('.policy-caption').inner_text()=='Customer data policy · scripted illustration. No cloud model was called.'
   assert not await a.locator('[data-action]').count()
   await a.screenshot(path=str(shots/'02-cloud-policy-gate.png'),full_page=True)
   assert await b.get_by_role('button',name='Start the story').is_visible()
   await b.get_by_role('button',name='Start the story').click()
   await b.get_by_role('button',name='Deploy local AI squad').wait_for()
   await b.screenshot(path=str(shots/'phone-policy-gate.png'),full_page=True)
   # One deploy starts all five roles and actions; B remains at its own policy gate.
   await a.get_by_role('button',name='Deploy local AI squad').click()
   await a.locator('.agent-runbook').wait_for()
   assert await a.locator('.mission-bot').count()==5
   assert await b.get_by_role('button',name='Deploy local AI squad').is_visible()
   await asyncio.sleep(.45)
   await a.screenshot(path=str(shots/'03-squad-deployed.png'),full_page=True)
   await a.get_by_role('button',name='Pause my experience',exact=True).click()
   await a.get_by_role('button',name='Resume my experience').wait_for()
   await asyncio.sleep(.4)
   await a.get_by_role('button',name='Resume my experience').click()
   # Accessibility controls suppress motion; OS preference remains authoritative.
   await a.get_by_role('button',name='Reduce motion',exact=True).click()
   assert await a.evaluate('document.getAnimations().length')==0
   await a.get_by_role('button',name='Reduced motion',exact=True).click()
   await a.emulate_media(reduced_motion='reduce');await asyncio.sleep(.2)
   assert await a.evaluate('document.getAnimations().length')==0
   await a.emulate_media(reduced_motion='no-preference')
   await a.get_by_role('button',name='Continue to the next challenge').wait_for(timeout=15000)
   assert await a.locator('.human-handoff').count()==1
   assert 'No email' in await a.locator('.human-handoff').inner_text()
   await a.screenshot(path=str(shots/'04-payment-human-review.png'),full_page=True)
   # B resets independently, even after A's automated response.
   await b.get_by_role('button',name='Reset',exact=True).click()
   await b.get_by_role('button',name='Reset my experience',exact=True).click()
   await b.get_by_role('button',name='Start the story').wait_for()
   assert await a.get_by_role('button',name='Continue to the next challenge').is_visible()
   for wave in [2,3]:
    await a.get_by_role('button',name='Continue to the next challenge').click()
    await a.get_by_role('button',name='Deploy local AI squad').wait_for()
    await a.get_by_role('button',name='Deploy local AI squad').click()
    await a.locator('.agent-runbook').wait_for()
    await a.screenshot(path=str(shots/f'0{wave+3}-incident-{wave}-running.png'),full_page=True)
    if wave==3:
     await a.set_viewport_size({'width':390,'height':844})
     await a.screenshot(path=str(shots/'phone-squad-running.png'),full_page=True)
     assert not await a.evaluate('document.documentElement.scrollWidth>innerWidth')
     await a.set_viewport_size({'width':1920,'height':1080})
    next_name='Build my Account Action Card' if wave==3 else 'Continue to the next challenge'
    await a.get_by_role('button',name=next_name).wait_for(timeout=15000)
   await a.screenshot(path=str(shots/'07-recovery-human-approval.png'),full_page=True)
   assert 'approve' in (await a.locator('.human-handoff').inner_text()).lower()
   await a.get_by_role('button',name='Build my Account Action Card').click()
   await a.locator('#account').fill('Your next customer')
   await a.locator('#next-step').fill('Discuss sensitive evidence, approved local AI tools and the human approval process.')
   async with a.expect_download() as info:await a.get_by_role('button',name='Download my Account Action Card').click()
   download=await info.value;await download.save_as(str(ROOT/'runtime/account-card-proof/guided-browser.pdf'))
   await a.reload();await a.locator('#account').wait_for()
   assert await a.locator('#account').input_value()=='Your next customer'
   for width,height in [(1920,1080),(1366,768),(390,844),(360,800)]:
    await a.set_viewport_size({'width':width,'height':height});await asyncio.sleep(.2)
    overflow=await a.evaluate('document.documentElement.scrollWidth>innerWidth');assert not overflow
    assert await a.get_by_role('button',name='Reset',exact=True).is_visible()
    assert await a.get_by_role('button',name='Restart ↻',exact=True).is_visible()
    checks.append({'viewport':[width,height],'horizontal_overflow':overflow,'reset_restart_visible':True})
   await a.screenshot(path=str(shots/'08-card-phone.png'),full_page=True)
   await a.get_by_role('button',name='Restart ↻',exact=True).click();await a.get_by_role('button',name='Restart now',exact=True).click()
   await a.get_by_role('button',name='Deploy local AI squad').wait_for()
   assert not await a.locator('[data-action]').count()
   await browser.close()
   ff=await p.firefox.launch();page=await ff.new_page(viewport={'width':390,'height':844});watch(page)
   await page.goto(server.base+'/');await page.get_by_role('button',name='Start the story').click()
   await page.get_by_role('button',name='Deploy local AI squad').wait_for();await ff.close()
  report={'passed':not errors,'checks':checks,'cloud_lane':'Scripted customer policy, no cloud request, no blanket provider refusal',
          'cloud_log_preflight_then_denied':True,'capacity_message':'Planning case, no scarcity prediction','one_deploy_per_incident':True,'five_automatic_roles':True,'human_handoff_scoped_to_demo':True,'independent_reset':True,
          'pdf_download_and_resume':True,'reduced_motion_toggle_and_OS':True,'console_errors':errors,
          'runtime_requests_local_only':all(x.startswith(server.base) or x.startswith(server.base.replace('http:','ws:')) for x in requests),
          'clock_scale':.25,'physical_devices_tested':False}
  (ROOT/'docs/guided-story-browser.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));assert report['passed'] and report['runtime_requests_local_only']
 finally:server.close()

if __name__=='__main__':asyncio.run(main())
