"""One US Letter page; no remote assets or untrusted HTML in PDF rendering."""
from html import escape
from base64 import b64encode
from functools import lru_cache
from app.config import ROOT
from app.cards import HYPOTHESIS

CSS='''@page{size:Letter;margin:0.5in}body{font:10.5pt Arial,Helvetica,sans-serif;color:#101820}h1{overflow-wrap:anywhere;font-size:24pt;letter-spacing:-.5pt;border-bottom:1px solid #101820;padding-bottom:10px;margin:17px 0}h2{font-size:8pt;color:#004BDF;letter-spacing:1.3px;text-transform:uppercase;margin:16px 0 8px}.block{background:#D1DDF1;padding:12px;margin:12px 0;font-size:10pt;line-height:1.5}p{line-height:1.45;margin:8px 0}li{margin:7px 0}ol{padding-left:21px}.meta{overflow-wrap:anywhere;font-size:9.5pt;line-height:1.6}.card-brand{display:flex;align-items:center;gap:15px;margin-bottom:18px}.card-brand img{width:36px;height:36px;margin-right:14px}.card-brand>span{font-size:8pt;line-height:1.8;letter-spacing:1px;font-weight:bold}.card-brand small{font-size:7pt;font-weight:normal;color:#586579}a{color:#004BDF}@media screen{body{font-size:16px;max-width:820px;margin:40px auto;padding:0 28px}h1{font-size:42px;overflow-wrap:anywhere;margin:28px 0}.meta{font-size:14px}.block{font-size:14px;padding:20px}h2{font-size:11px;letter-spacing:1.8px;margin-top:32px}.card-brand{padding-bottom:24px;border-bottom:1px solid #d7e0ec}.card-brand img{width:48px;height:48px}.card-brand>span{font-size:11px}.card-brand small{font-size:9px}.block a{display:inline-flex;align-items:center;min-height:48px;font-weight:bold}p,li{line-height:1.7}}'''

@lru_cache(maxsize=1)
def logo_data():
    return 'data:image/png;base64,'+b64encode((ROOT/'static/brand/hp-logo-keyline.png').read_bytes()).decode('ascii')


def card_html(card):
    p=card['prose']; e=escape
    questions=''.join('<li>'+e(x)+'</li>' for x in p['questions'])
    link='<a href="'+e(card['lab_request_url'],quote=True)+'">Request a ZGX Virtual Lab discussion</a>' if card['lab_request_url'].startswith('https://') else 'ZGX Virtual Lab discussion link awaits facilitator configuration.'
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>{CSS}</style><title>Account Action Card</title><body><div class="card-brand"><img src="{logo_data()}" alt="HP"><span>HP ZGX FURY<br><small>ACCOUNT ACTION CARD</small></span></div><h1>{e(card['account'])}</h1><div class="block">{HYPOTHESIS}</div><p class="meta">{e(card['industry'])}<br>Conversation owner: {e(card['owner'])}<br>Target date: {e(card['target_date'])}</p><h2>One use case to explore</h2><p>{e(p['use_case'])}</p><h2>Buyer or technical champion to explore</h2><p>{e(p['buyer'])}</p><h2>Three discovery questions</h2><ol>{questions}</ol><h2>Suggested opening message</h2><p>{e(p['opening_message'])}</p><div class="block">{link}</div></body></html>'''

def render_pdf(card):
    try:
        from weasyprint import HTML
        from weasyprint.urls import URLFetcherResponse
        # Only the exact embedded, owner-supplied logo is allowed; no network resources.
        def fetch(url,*args,**kwargs):
            if url==logo_data():return URLFetcherResponse(url,body=(ROOT/'static/brand/hp-logo-keyline.png').read_bytes(),headers={'Content-Type':'image/png'})
            raise ValueError('External PDF resources disabled')
        return HTML(string=card_html(card),url_fetcher=fetch).write_pdf()
    except (ImportError,OSError):
        from io import BytesIO
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
        stream=BytesIO(); styles=getSampleStyleSheet(); parts=[Image(str(ROOT/'static/brand/hp-logo-keyline.png'),width=32,height=32,hAlign='LEFT'),Spacer(1,12)]
        parts.append(Paragraph(escape(card['account']),styles['Title']))
        parts.append(Paragraph(HYPOTHESIS,styles['BodyText']))
        for text in [card['industry'],card['owner'],card['target_date'],card['prose']['use_case'],card['prose']['buyer'],*card['prose']['questions'],card['prose']['opening_message'],card['lab_request_url']]:
            parts.extend([Spacer(1,12),Paragraph(escape(text),styles['BodyText'])])
        SimpleDocTemplate(stream,pagesize=letter).build(parts)
        return stream.getvalue()
