"""Template backed cards. Account text remains data, never a source of claims."""
from functools import lru_cache
import re
import secrets
import unicodedata
from datetime import date, timedelta
import yaml
from app.config import ROOT, settings

HYPOTHESIS='Opportunity hypothesis to validate in discovery. Not based on research of this account.'
PROSE_FIELDS=('use_case','buyer','questions','opening_message')

def has_dash(text):
    return any(unicodedata.category(char)=='Pd' or char in '\u2212\u00ad' for char in text)

def templates():
    # File stamps keep Carlos's edits visible without parsing ten YAML files per phone update.
    signature=tuple((str(path),path.stat().st_mtime_ns,path.stat().st_size) for path in sorted((ROOT/'content/industry_templates').glob('*.yaml')))
    return load_templates(signature)

@lru_cache(maxsize=4)
def load_templates(signature):
    from pathlib import Path
    return {Path(name).stem:yaml.safe_load(Path(name).read_text()) for name,_,_ in signature}

def clean_text(value,limit):
    value=value.strip()
    if not value or len(value)>limit or any(unicodedata.category(c).startswith('C') for c in value):
        raise ValueError(f'Enter 1 to {limit} printable characters')
    return value

def build_card(team,account,industry,owner,target_date):
    source=templates().get(industry)
    if not source: raise ValueError('Choose an industry')
    account=clean_text(account,80); owner=clean_text(owner,80)
    target=date.fromisoformat(target_date)
    if target<date.today() or target>date.today()+timedelta(days=730): raise ValueError('Choose a date within the next two years')
    prose={key:source[key] for key in PROSE_FIELDS}
    for value in prose.values():
        for text in value if isinstance(value,list) else [value]:
            if has_dash(text): raise ValueError('Template prose contains a dash')
    # User entered account and owner text is preserved as data, outside prose fields.
    return {'id':secrets.token_urlsafe(24),'session':team['session_id'],'team':team['name'],'team_id':team['id'],
            'account':account,'industry_key':industry,'industry':source['industry'],'owner':owner,
            'target_date':target.isoformat(),'hypothesis':HYPOTHESIS,'lab_request_url':settings.lab_request_url,
            'template_status':source['status'],'polish':'template','prose':prose}
