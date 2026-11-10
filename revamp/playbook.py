"""One-page local seller playbook. Stories are private, optional and debrief-only."""
import json
from html import escape
from .settings import ROOT
from .content import WAVES

STORY_PATH = ROOT / 'config/stories.local.json'
QUESTIONS = [
    'Which sensitive data must your team analyze without sending it to a cloud service?',
    'Where do people wait longest for evidence, explanations or a clear next step?',
    'Which AI and security workloads would you want to test together locally?',
    'How do your people verify an AI suggestion before taking a business action?',
    'What would a useful local pilot measure: time saved, response speed or data handling?',
]

def approved_story():
    try:
        config = json.loads(STORY_PATH.read_text())
        for item in config.get('stories', []):
            if item.get('approved') is True and isinstance(item.get('text'), str) and item.get('approval_reference'):
                return {'title': str(item.get('title', 'Approved internal story'))[:80],
                        'text': item['text'][:420], 'reference': str(item['approval_reference'])[:80]}
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return None

CSS = '''@page{size:A4;margin:12mm}*{box-sizing:border-box}body{font:9.2pt Arial,Helvetica,sans-serif;color:#102238;line-height:1.35;margin:0}h1{font-size:25pt;line-height:1.08;margin:8px 0 4px;color:#102238}h2{font-size:10pt;margin:12px 0 5px;color:#006775;text-transform:uppercase;letter-spacing:.6px}p{margin:5px 0}ol{margin:4px 0;padding-left:18px}li{margin:4px 0}.brand{font-size:8pt;letter-spacing:1.6px;color:#006775;font-weight:bold}.meta{font-size:8pt;color:#375069}.result{background:#e9f4f7;border-left:3px solid #006775;padding:9px 12px;margin:10px 0}.wave{break-inside:avoid;margin:7px 0}.wave b{color:#006775}.wave p{margin:3px 0}.quote{font-style:italic}.facts{background:#edf1f5;padding:8px 12px;margin:8px 0}.footer{font-size:7.1pt;color:#375069;border-top:1px solid #8ba3b2;margin-top:10px;padding-top:6px}.story{break-inside:avoid}a{color:#006775}@media screen{body{max-width:820px;margin:30px auto;padding:25px;font-size:16px;background:white}h1{font-size:40px}h2{font-size:18px}.meta{font-size:13px}.brand{font-size:13px}.footer{font-size:12px}.result{padding:18px}.wave{margin-top:18px}.download{display:inline-block;padding:16px 22px;background:#006775;color:white;border-radius:8px;text-decoration:none;font-weight:bold;margin:15px 0}}@media print{.download{display:none}}'''

def playbook_html(room, team, download_link=None):
    e = escape
    dollars = lambda v: '$' + format(round(v), ',')
    total_time = sum(team['times'].values())
    story = approved_story()
    story_html = f'<section class="story"><h2>{e(story["title"])}</h2><p>{e(story["text"])}</p><p class="meta">Internal approval: {e(story["reference"])}</p></section>' if story else ''
    waves = ''.join(f'<section class="wave"><b>{i}. {e(w["name"])}</b>' + ''.join(f'<p class="{"quote" if j==2 else ""}">{e(line)}</p>' for j, line in enumerate(w['translate'])) + '</section>' for i, w in WAVES.items())
    questions = ''.join('<li>' + e(x) + '</li>' for x in QUESTIONS)
    link = f'<a class="download" href="{e(download_link, quote=True)}">Download your one page PDF</a>' if download_link else ''
    power = room['power']
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(team['name'])} · Seller Playbook</title><style>{CSS}</style></head><body><div class="brand">CYBER SIEGE / HP ZGX FURY</div><h1>Your local AI value story.</h1><p class="meta">{e(team['name'])} · Northwind, a fictional {e(room['industry'].replace('_', ' '))} customer · Room {e(room['code'])}</p>{link}<div class="result"><p><b>What happened:</b> Your team faced a payment trap, fake emails and frozen systems.</p><p><b>Your results:</b> {team['score']:,} points. {dollars(team['risk'])} revenue at risk. {round(team['trust'])}/100 trust. {int(team['records'])} fictional records exposed.</p><p><b>Your response:</b> {total_time:.1f} seconds across three waves; {team['fast']} Fast Response bonuses. Revenue protected versus ten minutes of full downtime: {dollars(max(0, 120000-team['risk']))}. All dollars are game values.</p></div><h2>Translate the three waves</h2>{waves}<h2>Five discovery questions</h2><ol>{questions}</ol><h2>Where HP ZGX Fury fits</h2><div class="facts"><p>A platform for local AI agents that help your security team spot, explain and contain problems faster. People verify suggestions and take action. Fury is not a security product.</p><p>Measured in this room: {power['peak']} peak simultaneous model calls; {power['evidence']:,} evidence items submitted, including repeated analysis; {power['tokens']:,} reported output tokens. Game AI requests used the local loopback model path. Cloud AI payload bytes: {power['cloud_bytes']}.</p></div>{story_html}<div class="footer">Fictional game values, not customer or industry statistics. Counter scope: game AI HTTP payloads only; private device traffic and model startup downloads excluded. Internal discovery aid. Ask your customer what success should look like.</div></body></html>'''

def render_pdf(room, team):
    from weasyprint import HTML
    def reject_remote(url, *args, **kwargs):
        raise ValueError('Playbook resources must be local; external loading is disabled')
    return HTML(string=playbook_html(room, team), url_fetcher=reject_remote).write_pdf()
