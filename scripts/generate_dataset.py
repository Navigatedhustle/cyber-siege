#!/usr/bin/env python3
"""Reproducible fictional exercise. Reserved 9000 IDs identify curated evidence."""
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

END=datetime(2026,11,16,2,17,tzinfo=timezone.utc)
SOURCES={'idp':'IDP','email':'EML','endpoint':'EDR','file':'FIL','proxy_dns':'NET'}

def generate(seed=217):
    rng=random.Random(seed)
    events=[]
    for source,prefix in SOURCES.items():
        for index in range(1,1201):
            when=END-timedelta(seconds=rng.randrange(36*3600))
            user=rng.choice(['a.patel','j.chen','m.brooks','s.owens','t.reed','svc_backup','analytics_job']+[f'employee{i:04}' for i in range(1,97)])
            user_number=sum(ord(char) for char in user)
            host='CRD-FIN-023' if user=='m.brooks' else f'CRD-WS-{user_number%180+1:03}'
            source_ip='10.24.3.23' if user=='m.brooks' else f'10.24.{user_number%11+1}.{user_number%230+2}'
            event=dict(id=f'{prefix}{index:04}',source=source,timestamp=when.isoformat(),user=user,
                       host=host,src_ip=source_ip,
                       action={'idp':'sign_in','email':'message_delivered','endpoint':'process_start','file':'file_read','proxy_dns':'dns_query'}[source],
                       result='success')
            if source=='idp': event.update(country='GB',mfa='satisfied',session_id=f'normal-{index}')
            if source=='email': event.update(sender='billing@'+rng.choice(['harborparts.example','summitcomponents.example','northforge.example','relaylogistics.example']),subject='Monthly parts invoice',attachment=f'invoice_{index:04}.pdf',spf='pass',dkim='pass')
            if source=='endpoint': event.update(process='explorer.exe',parent='userinit.exe')
            if source=='file': event.update(path=f'/shared/operations/dispatch_{rng.randrange(1,500)}.csv',bytes=rng.randrange(400,24000))
            if source=='proxy_dns': event.update(domain=rng.choice(['updates.example','portal.cobaltridge.example','harborparts.example']),bytes=rng.randrange(100,4000))
            events.append(event)
    def add(id,source,clock,**fields):
        events.append(dict(id=id,source=source,timestamp=f'2026-11-16T{clock}:00+00:00',**fields))
    add('EML9001','email','00:43',user='m.brooks',host='CRD-FIN-023',src_ip='192.0.2.44',action='message_delivered',sender='billing@harb0rparts.example',subject='Revised supplier invoice',attachment='Invoice_4317.html',message_id='crd-msg-4317',domain='harb0rparts.example',result='delivered')
    add('EDR9001','endpoint','00:46',user='m.brooks',host='CRD-FIN-023',src_ip='10.24.3.23',action='attachment_open',attachment='Invoice_4317.html',process='msedge.exe',parent='outlook.exe',message_id='crd-msg-4317',result='opened')
    add('NET9001','proxy_dns','00:47',user='m.brooks',host='CRD-FIN-023',src_ip='10.24.3.23',action='https_post',domain='login.harb0rparts.example',dst_ip='192.0.2.44',path='/session/collect',bytes=8341,session_id='sess-fin-823',result='allowed')
    add('EDR9002','endpoint','00:47',user='m.brooks',host='CRD-FIN-023',src_ip='10.24.3.23',action='browser_token_access',process='msedge.exe',artifact='session cookie store read after invoice opened',session_id='sess-fin-823',result='detected')
    add('IDP9001','idp','01:08',user='m.brooks',host='unmanaged',src_ip='198.51.100.77',country='NL',action='sign_in',session_id='sess-fin-823',mfa='not_prompted',auth_method='session_cookie',risk='new_network',result='success')
    add('FIL9001','file','01:12',user='m.brooks',host='CRD-FS-01',src_ip='198.51.100.77',action='directory_enumeration',session_id='sess-fin-823',path='/finance/confidential',files=428,result='success')
    add('FIL9002','file','01:29',user='m.brooks',host='CRD-FS-01',src_ip='198.51.100.77',action='bulk_download',session_id='sess-fin-823',path='/finance/confidential',files=428,bytes=2748779069,result='success')
    add('FIL9003','file','02:16',user='svc_backup',host='unmanaged',src_ip='198.51.100.77',action='bulk_download',path='/finance/confidential',files=428,bytes=2748779069,scheduled_window='03:00 to 03:30 UTC',expected_src_ip='10.24.9.10',injected=True,result='success')
    add('IDP9002','idp','00:59',user='a.patel',host='CRD-EXEC-001',src_ip='203.0.113.25',country='SG',action='sign_in',mfa='interactive_pass',travel_ticket='approved CRD-778',device_compliance='managed',result='success')
    add('FIL9004','file','01:20',user='analytics_job',host='CRD-ETL-02',src_ip='10.24.8.12',action='bulk_export',path='/analytics/approved',files=2100,bytes=6442450944,change_ticket='approved CRD-804',result='success')
    # Normal backup earlier in the 36 hour window, contrasted with the injected event.
    events.append(dict(id='FIL9005',source='file',timestamp='2026-11-15T03:10:00+00:00',user='svc_backup',host='CRD-BACKUP-01',src_ip='10.24.9.10',action='scheduled_backup',path='/finance/confidential',files=428,scheduled_window='03:00 to 03:30 UTC',result='success'))
    add('EML9002','email','00:35',user='j.chen',host='CRD-FIN-024',src_ip='192.0.2.12',action='message_delivered',sender='billing@harborparts.example',subject='Supplier invoice',attachment='invoice.pdf',spf='pass',dkim='pass',result='delivered')
    return sorted(events,key=lambda e:(e['timestamp'],e['id']))

if __name__=='__main__':
    target=Path(__file__).resolve().parents[1]/'data/events.json'
    target.write_text(json.dumps(generate(),indent=2)+'\n')
    print(f'{len(generate())} fictional events written to {target}')
