"""Branded local Account Action Card; explicit links/QR to verified HP resources."""
from base64 import b64encode
from functools import lru_cache
from html import escape
from io import BytesIO
import json
import qrcode
from .settings import ROOT
from .playbook import approved_story

RESOURCE_CONFIG = json.loads((ROOT/'config/hp_resources.json').read_text())
RESOURCES = RESOURCE_CONFIG['resources']
DIFFERENTIATORS = json.loads((ROOT/'config/hp_zgx_differentiators.json').read_text())
SOURCE_BY_ID = {item['id']:item for item in DIFFERENTIATORS['sources']}
LOGO = ROOT/'static/brand/hp-logo-keyline.png'
HYPOTHESES = {
    'healthcare': 'Explore how local AI could help staff review sensitive operational information faster, with people verifying the findings.',
    'manufacturing': 'Explore local AI for reviewing production logs and engineering information, keeping proprietary work close to the team.',
    'retail': 'Explore local AI for sorting store operations and customer service information, so staff can focus on important decisions.',
    'financial_services': 'Explore how local AI could help analysts review sensitive operational evidence and explain findings to colleagues.',
    'public_sector': 'Explore local AI for reviewing service records and operational information under the agency’s data controls.',
    'higher_education': 'Explore shared local AI for research and campus operations, with the relevant data owners reviewing each use case.',
}
QUESTIONS = [
    'Which evidence is approved for external AI services?',
    'Which work needs analysis close to sensitive data?',
    'Which critical workflow needs dedicated AI capacity?',
    'Which actions can agents automate within a safe scope?',
    'Who approves production changes and owns the outcome?',
]

@lru_cache(maxsize=1)
def assets():
    buffer=BytesIO();qrcode.make(RESOURCES[0]['url'],box_size=5,border=2).save(buffer,format='PNG')
    return {'logo':'data:image/png;base64,'+b64encode(LOGO.read_bytes()).decode(),
            'qr':'data:image/png;base64,'+b64encode(buffer.getvalue()).decode()}

CSS='''@page{size:A4;margin:10mm}*{box-sizing:border-box}body{font:8pt Arial,Helvetica,sans-serif;line-height:1.35;color:#173247;margin:0}p{margin:0 0 5px}h1,h2,h3{margin:0}table{border-collapse:collapse;width:100%}td{vertical-align:top}a{color:#006e99}.hero{background:#071c32;color:white;padding:12px 17px;border-bottom:4px solid #00a8df}.hero td{vertical-align:middle}.hero h1{font-size:22pt;line-height:1.04;letter-spacing:-.6pt;margin:7px 0}.kicker{color:#81e5ff;font-size:6.8pt;letter-spacing:1.5px;font-weight:bold}.logo-cell{width:49px}.logo-chip{display:block;background:white;border-radius:50%;padding:8px;width:39px;height:39px}.logo-chip img{width:23px;height:23px;display:block}.edition{font-size:6.6pt;letter-spacing:.8px;text-align:right;color:#bbd5e8;width:90px}.hero-caption{font-size:7.1pt;color:#c3ddec;margin:5px 0 0}.account{padding:10px 0 8px}.eyebrow{font-size:6.4pt;letter-spacing:1.1px;font-weight:bold;text-transform:uppercase;color:#006e99}.account h2{font-size:16pt;line-height:1.12;overflow-wrap:anywhere;margin:4px 0}.meta{color:#526d7e;font-size:6.5pt}.metrics{background:#eef7fb;border:1px solid #d5e9f2;margin-bottom:11px}.metrics td{width:33.3%;padding:7px 10px;border-right:1px solid #d5e9f2}.metrics strong{font-size:15pt;line-height:1.1;color:#006f9e;display:block;margin-bottom:2px}.metrics small{font-size:6.6pt;color:#37566c}.product-heading{margin-bottom:7px}.product-heading h2{font-size:13pt;letter-spacing:-.3px;color:#092d48;margin:3px 0}.product-heading p{font-size:7.3pt;color:#526d7e}.feature-grid{table-layout:fixed;margin-bottom:11px}.feature-grid td{width:33.333%;padding:6px 8px;background:#f0f6fa;border:3px solid white}.feature-grid td.software{background:#eaf7f8}.feature-grid td.certified{background:#edf6ef}.feature-grid a{font-size:8pt;font-weight:bold;text-decoration:none;color:#07547a}.feature-grid .number{font-size:6pt;color:#558398;font-weight:bold;margin-right:5px}.feature-grid .fact{font-size:7.1pt;line-height:1.35;color:#486576;margin:3px 0}.feature-grid .benefit{font-size:7.4pt;line-height:1.4;color:#19394e;margin:0}.feature-grid .benefit b{color:#006d82}.columns{table-layout:fixed}.columns .left{width:52%;padding-right:14px}.columns .right{width:48%;padding-left:14px;border-left:1px solid #d8e5ed}h3{font-size:7.5pt;color:#006f9e;letter-spacing:.4px;text-transform:uppercase;margin:0 0 6px}.hypothesis{font-size:8.4pt;line-height:1.4;font-weight:bold;margin:4px 0}.note{font-size:6.6pt;color:#637b8c;margin-bottom:9px}.questions{padding-left:15px;margin:0;font-size:7.7pt;line-height:1.4}.questions li{margin:4px 0}.next-step{background:#eef8f7;border-top:3px solid #168f9c;padding:10px;font-size:8.5pt;line-height:1.4;overflow-wrap:anywhere;margin-bottom:9px}.checklist{font-size:7.1pt;color:#37566c}.checklist p{margin-bottom:4px}.scope{font-size:6.6pt;line-height:1.4;color:#526d7e;margin-top:7px}.resources{border-top:2px solid #163d58;margin-top:10px;padding-top:8px;break-inside:avoid}.resource-list{width:82%;padding-right:12px}.resource-list h3{margin-bottom:5px}.resource-links{font-size:7.1pt;line-height:1.7}.resource-links a{margin-right:8px;white-space:nowrap;font-weight:bold}.scan{width:18%;text-align:center;vertical-align:middle}.scan img{width:58px;height:58px}.scan p{font-size:6pt;color:#37566c;margin:1px 0 0}.qualifications{font-size:6pt;line-height:1.4;color:#526d7e;margin-top:7px}.qualifications p{margin-bottom:3px}.footer{border-top:1px solid #d8e5ed;margin-top:6px;padding-top:5px;font-size:6pt;line-height:1.4;color:#526d7e}.story{font-size:6.8pt;line-height:1.35;margin-top:8px;background:#f3f7fa;padding:7px;break-inside:avoid}.story b{display:block;margin-bottom:3px}.compact .hero{padding:11px 16px}.compact .hero h1{font-size:22pt;margin:5px 0}.compact .account{padding:7px 0 5px}.compact .account h2{font-size:14pt}.compact .metrics{margin-bottom:8px}.compact .metrics td{padding:5px 8px}.compact .feature-grid{margin-bottom:8px}.compact .feature-grid td{padding:5px 8px}.compact .feature-grid .benefit{font-size:7pt;line-height:1.3}.compact .feature-grid .fact{font-size:6.8pt;margin:2px 0;line-height:1.3}.compact .questions{font-size:7.3pt;line-height:1.3}.compact .questions li{margin:3px 0}.compact .next-step{padding:7px;font-size:7.8pt;margin-bottom:7px}.compact .product-heading{margin-bottom:4px}.compact .scope{font-size:6.1pt}.compact .resources{margin-top:7px;padding-top:6px}.compact .story{margin-top:6px;padding:6px}.compact .qualifications{font-size:5.8pt;line-height:1.3}.compact .footer{font-size:5.8pt;margin-top:4px;padding-top:4px}'''

def action_card_html(room):
    e=escape
    card=room.get('card',{})
    account=card.get('account') or 'Your next customer conversation'
    next_step=card.get('next_step') or 'Book discovery with the business owner and technical champion. Agree one workflow and a measurable pilot.'
    team=room['teams']['1']
    guided=room.get('guided',False)
    achievement=sum(team['robot_uses'].values()) if guided else team['score']
    achievement_label='agent demonstration steps' if guided else 'your game score'
    protected=max(0,120000-team['risk']);media=assets()
    questions=''.join('<li>'+e(q)+'</li>' for q in QUESTIONS)
    cells=[]
    for i,item in enumerate(DIFFERENTIATORS['items']):
        source=SOURCE_BY_ID[item['sources'][0]]
        style='software' if item['id'] in {'ztk','zrt'} else 'certified' if item['id']=='rhel' else ''
        cells.append(f'<td class="{style}"><span class="number">{i+1:02}</span><a href="{e(source["url"],quote=True)}">{e(item["title"])}</a><p class="fact">{e(item["feature"])}</p><p class="benefit"><b>Why care:</b> {e(item["benefit"])}</p></td>')
    rows=''.join('<tr>'+''.join(cells[i:i+3])+'</tr>' for i in range(0,len(cells),3))
    links=''.join(f'<a href="{e(r["url"],quote=True)}">{e(r["title"])} ↗</a>' for r in RESOURCES)
    evidence_links=''.join(f'<a href="{e(SOURCE_BY_ID[k]["url"],quote=True)}">{e(SOURCE_BY_ID[k]["title"])} ↗</a>' for k in ['rhel','redhat_hp'])
    story=approved_story()
    story_html=f'<div class="story"><b>{e(story["title"])}</b>{e(story["text"])} <span class="meta">Internal approval: {e(story["reference"])}</span></div>' if story else ''
    compact=bool(story or len(account)>45 or len(next_step)>150)
    industry=room['industry'].replace('_',' ').title()
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><title>HP Account Action Card</title><style>{CSS}</style></head><body class="{'compact' if compact else ''}"><header class="hero"><table><tr><td class="logo-cell"><span class="logo-chip"><img src="{media['logo']}" alt="HP"></span></td><td><div class="kicker">HP ZGX FURY / ACCOUNT ACTION CARD</div><h1>Start a better AI conversation.</h1></td><td class="edition">YOUR EXPERIENCE.<br>YOUR NEXT MOVE.</td></tr></table><p class="hero-caption">Local AI capacity. An open software path. People in control.</p></header><section class="account"><div class="eyebrow">Prepared for your next conversation</div><h2>{e(account)}</h2><p class="meta">{e(industry)} discovery · Inspired by your fictional Northwind experience</p></section><table class="metrics"><tr><td><strong>{achievement:,}</strong><small>{achievement_label}</small></td><td><strong>{round(team['trust'])}/100</strong><small>customer trust · game meter</small></td><td><strong>${round(protected):,}</strong><small>revenue protected · game value*</small></td></tr></table><section class="product-heading"><div class="eyebrow">The platform story, ready to explain</div><h2>Why HP ZGX Fury / GB300?</h2><p>Match each capability to a customer need. Click any feature title for its source.</p></section><table class="feature-grid">{rows}</table><table class="columns"><tr><td class="left"><h3>01 / The opportunity</h3><p class="hypothesis">{e(HYPOTHESES[room['industry']])}</p><p class="note">Discovery hypothesis, not research about the named account.</p><h3>02 / Ask in discovery</h3><ol class="questions">{questions}</ol></td><td class="right"><h3>03 / Your next step</h3><p class="next-step">{e(next_step)}</p><div class="checklist"><p><b>Pick one workflow.</b> Agree its data, delay and business impact.</p><p><b>Bring the right people.</b> Business owner, IT and data approver.</p><p><b>Define the proof.</b> Set pilot measures, capacity and support needs.</p></div><p class="scope">Live local AI examined fictional evidence. Recovery is simulated; human review is queued. Fury is not a security product. Production AI needs safeguards and authorized tools.</p></td></tr></table>{story_html}<section class="resources"><table><tr><td class="resource-list"><h3>Continue with official resources</h3><div class="resource-links">{links}<br>{evidence_links}</div><div class="qualifications"><p>HP-published FP4 peak; results depend on model, precision and concurrency. Dedicated 200–240V AC required; validate rack, cooling and network needs.</p><p>Storage/options chosen at purchase. ZTK: x86 Windows 11 or Ubuntu 24.04+, VS Code; availability and model access vary.</p><p>RHEL certification covers listed hardware/OS configurations, not this demo or AI applications. Confirm versions, subscriptions and support. HP describes Red Hat AI Factory integration as planned.</p></div></td><td class="scan"><img src="{media['qr']}" alt="QR code to HP ZGX Fury product page"><p>Scan for<br>HP ZGX Fury</p></td></tr></table></section><footer class="footer">*Game value: revenue protected compares this result with ten minutes of full downtime at $12,000/min. Fictional, not a customer forecast. Sources verified {e(DIFFERENTIATORS['verified_on'])}. Benefits are discovery guidance, not measured outcomes. Product availability and specifications may change.</footer></body></html>'''

def render_action_card(room):
    from weasyprint import HTML
    from weasyprint.urls import URLFetcherResponse
    media=assets()
    allowed={media['logo']:LOGO.read_bytes(),media['qr']:__import__('base64').b64decode(media['qr'].split(',',1)[1])}
    def fetch(url,*args,**kwargs):
        if url in allowed:
            return URLFetcherResponse(url,body=allowed[url],headers={'Content-Type':'image/png'})
        raise ValueError('External Account Action Card resources are disabled')
    return HTML(string=action_card_html(room),url_fetcher=fetch).write_pdf()
