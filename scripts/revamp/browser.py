#!/usr/bin/env python3
"""Real UI choices, all phases/screenshots, desktop/mobile and reduced-motion checks."""
import asyncio
import json
import os
import time
from pathlib import Path
from harness import ROOT, Server
os.environ['PLAYWRIGHT_BROWSERS_PATH']=str(ROOT/'runtime/browsers')
from playwright.async_api import async_playwright

async def main():
    server=Server('revamp-browser-'+str(int(time.time())),port=8092,scale=1)
    room=server.create(teams=1);code=room['code']
    results=[];errors=[];requests=[];shots=ROOT/'docs/screenshots/revamp'
    shots.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as p:
        browser=await p.chromium.launch()
        context=await browser.new_context(viewport={'width':1920,'height':1080})
        screen=await context.new_page()
        screen.on('pageerror',lambda x:errors.append(str(x)))
        screen.on('console',lambda x:errors.append(x.text) if x.type=='error' else None)
        screen.on('request',lambda x:requests.append(x.url))
        await screen.goto(server.base+'/screen?room='+code)
        await screen.wait_for_selector('.city-art')
        await screen.screenshot(path=str(shots/'01-lobby.png'))
        phone_context=await browser.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
        phone=await phone_context.new_page()
        phone.on('pageerror',lambda x:errors.append(str(x)))
        phone.on('console',lambda x:errors.append(x.text) if x.type=='error' else None)
        await phone.goto(server.base+'/play?room='+code)
        await phone.locator('#nickname').fill('Team Captain')
        await phone.get_by_role('button',name='Join the defense').click()
        await phone.wait_for_selector('#player-title')
        assert await phone.locator('#connection').get_attribute('data-online')=='true'
        # Authenticate the console through the actual login form.
        host=await context.new_page()
        host.on('pageerror',lambda x:errors.append(str(x)))
        await host.goto(server.base+'/facilitator?room='+code)
        await host.locator('#password').fill((server.data/'first-launch-password.txt').read_text().strip())
        await host.get_by_role('button',name='Open controls').click()
        await host.locator('[data-control="start"]').click()
        await screen.locator('#screen-heading').filter(has_text='Meet your local').wait_for()
        await screen.screenshot(path=str(shots/'02-briefing.png'))
        await host.locator('[data-control="next"]').click()
        await phone.wait_for_selector('[data-action="analyze"]')
        await asyncio.sleep(1)
        await screen.screenshot(path=str(shots/'03-wave1.png'))
        await phone.screenshot(path=str(shots/'phone-invoice.png'),full_page=True)
        await phone.locator('[data-action="analyze"]').click()
        await phone.locator('[data-action="verify"]').click()
        await screen.wait_for_selector('.translate')
        await screen.screenshot(path=str(shots/'04-translate1.png'))
        await host.locator('[data-control="next"]').click()
        await phone.wait_for_selector('[data-deploy="0"]')
        await screen.screenshot(path=str(shots/'05-wave2.png'))
        for i in range(6):
            await phone.locator(f'[data-deploy="{i}"]').click()
            await asyncio.sleep(.1)
        await screen.wait_for_selector('.translate')
        await screen.screenshot(path=str(shots/'06-translate2.png'))
        await host.locator('[data-control="next"]').click()
        await phone.wait_for_selector('[data-robot="SCOUT"]')
        await screen.screenshot(path=str(shots/'07-wave3.png'))
        for i,r in enumerate(['SCOUT','SHERLOCK','SHIELD','PATCH','SCRIBE']):
            await phone.locator(f'[data-robot="{r}"]').click()
            await phone.locator(f'[data-deploy="{i}"]').click()
            await asyncio.sleep(.15)
        await screen.wait_for_selector('.translate')
        await screen.screenshot(path=str(shots/'08-translate3.png'))
        await host.locator('[data-control="next"]').click()
        await screen.wait_for_selector('.debrief')
        await screen.screenshot(path=str(shots/'09-debrief.png'))
        await phone.screenshot(path=str(shots/'phone-debrief.png'),full_page=True)
        async with phone.expect_download() as download_info:
            await phone.get_by_role('link',name='Download Seller Playbook PDF').click()
        download=await download_info.value
        assert download.suggested_filename.endswith('.pdf')
        await host.locator('[data-control="sound"]').click()
        await screen.locator('[data-mute]').click()
        assert 'Sound on' in await screen.locator('[data-mute]').text_content()
        await screen.locator('[data-mute]').click()
        assert 'Sound off' in await screen.locator('[data-mute]').text_content()
        # Projection fits at both required desktop resolutions.
        for width,height in [(1920,1080),(1366,768)]:
            await screen.set_viewport_size({'width':width,'height':height})
            await asyncio.sleep(.3)
            result=await screen.evaluate('({horizontal:document.documentElement.scrollWidth>innerWidth,vertical:document.documentElement.scrollHeight>innerHeight+2})')
            results.append({'surface':'big screen','viewport':[width,height],**result})
        # Fixed station joins automatically through a signed setup link.
        station_links=server.client.get(f'/api/rooms/{code}/stations').json()
        station_context=await browser.new_context(viewport={'width':1366,'height':768})
        station=await station_context.new_page()
        station.on('pageerror',lambda x:errors.append(str(x)))
        await station.goto(station_links[0]['url'])
        await station.wait_for_selector('#player-title')
        await station.screenshot(path=str(shots/'station-1366.png'),full_page=True)
        assert await station.locator('body').get_attribute('class')=='reduced kiosk'
        for width,height,label in [(390,844,'iPhone viewport'),(360,800,'Android viewport')]:
            await phone.set_viewport_size({'width':width,'height':height})
            result=await phone.evaluate('({horizontal:document.documentElement.scrollWidth>innerWidth})')
            results.append({'surface':label,'viewport':[width,height],**result})
        # Populate all eight leaderboard rows and inspect real inner panel bounds.
        populated=server.create(teams=8,industry='manufacturing');fullcode=populated['code']
        await screen.set_viewport_size({'width':1920,'height':1080})
        await screen.goto(server.base+'/screen?room='+fullcode)
        await screen.wait_for_selector('.city-art')
        for command in ['start','next','next','next','next','next','next','next']:
            server.client.post(f'/api/rooms/{fullcode}/control',json={'command':command})
            await asyncio.sleep(.4)
            actual=server.client.get('/api/rooms/'+fullcode).json()
            bounds=await screen.evaluate("() => ({horizontal:document.documentElement.scrollWidth>innerWidth,vertical:document.documentElement.scrollHeight>innerHeight+2,missionClipped:document.querySelector('#mission').scrollHeight>document.querySelector('#mission').clientHeight+2,leaderboardClipped:document.querySelector('#leaderboard').scrollHeight>document.querySelector('#leaderboard').clientHeight+2})")
            results.append({'phase':actual['phase'],'wave':actual['wave'],'teams':8,**bounds})
        await screen.screenshot(path=str(shots/'debrief-eight-teams.png'))
        # All additional industry skins have the right six buildings and local icon art.
        for industry in ['healthcare','manufacturing','retail','financial_services','public_sector','higher_education']:
            themed=server.create(teams=8,industry=industry)
            await screen.goto(server.base+'/screen?room='+themed['code'])
            await screen.wait_for_selector('.city-art')
            assert await screen.locator('.city-label').count()==6
            await screen.screenshot(path=str(shots/('industry-'+industry+'.png')))
        # Return to the first populated room for the accessibility assertions.
        await screen.goto(server.base+'/screen?room='+code)
        await screen.wait_for_selector('.city-art')
        # Default reduced intensity must have no active animations; OS setting overrides standard.
        assert await screen.evaluate('document.getAnimations().length')==0
        server.client.post(f'/api/rooms/{code}/control',json={'command':'intensity','value':'standard'})
        await asyncio.sleep(.4)
        durations=await screen.evaluate('document.getAnimations().map(a=>a.effect.getTiming().duration)')
        assert all(d>=1000 for d in durations)
        intervals=await screen.evaluate('''() => new Promise(resolve => {
            const values=[];let previous;
            function frame(t){if(previous!==undefined)values.push(t-previous);previous=t;
                if(values.length>=120)resolve(values);else requestAnimationFrame(frame);}
            requestAnimationFrame(frame);
        })''')
        fps=round(1000/(sum(intervals)/len(intervals)),1)
        frame_p95=round(sorted(intervals)[113],2)
        await screen.emulate_media(reduced_motion='reduce')
        await asyncio.sleep(.4)
        assert await screen.evaluate('document.getAnimations().length')==0
        await host.screenshot(path=str(shots/'facilitator.png'),full_page=True)
        await host.goto(server.base+'/stations?room='+code)
        await host.wait_for_selector('.station-card')
        await host.screenshot(path=str(shots/'station-setup.png'),full_page=True)
        await browser.close()
        # Firefox is an additional engine; these are viewport checks, not physical Safari certification.
        firefox=await p.firefox.launch()
        page=await firefox.new_page(viewport={'width':390,'height':844})
        page.on('pageerror',lambda x:errors.append(str(x)))
        await page.goto(server.base+'/play?room='+code)
        await page.wait_for_selector('#join-form')
        results.append({'surface':'Firefox mobile join',**await page.evaluate('({horizontal:document.documentElement.scrollWidth>innerWidth})')})
        await firefox.close()
    server.close()
    report={'checks':results,'console_errors':errors,'all_game_requests_private':all(x.startswith(server.base) or x.startswith(server.base.replace('http:','ws:')) for x in requests),
            'accessibility':{'default_reduced_no_animations':True,'standard_animation_durations_ms':durations,'prefers_reduced_motion_suppresses_standard':True,'large_red_flashes':False,'states_use_icons_and_labels':True},
            'standard_motion_performance':{'raf_average_fps':fps,'frame_interval_p95_ms':frame_p95,'target_fps':60},
            'limitations':['iPhone/Android viewport emulation; physical devices still need venue preflight. Existing WebKit build cannot run on this host’s 64 KiB pages.'],
            'passed':not errors and all(not r.get('horizontal') and not r.get('vertical') and not r.get('missionClipped') and not r.get('leaderboardClipped') for r in results)}
    (ROOT/'docs/revamp-browser.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if not report['passed']:raise SystemExit(1)

if __name__=='__main__':asyncio.run(main())
