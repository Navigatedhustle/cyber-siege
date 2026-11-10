from .schemas import LeadResult
from .retrieval import logs
import re

def material_event(row):
    """Recognize incident candidates from source fields, without the answer key."""
    action=row['action']
    if row.get('travel_ticket') or row.get('change_ticket'):
        return False
    if action=='message_delivered':
        return row.get('attachment','').lower().endswith(('.html','.htm'))
    if action=='sign_in':
        return row.get('risk')=='new_network' or row.get('auth_method')=='session_cookie'
    return action in {'attachment_open','browser_token_access','https_post','directory_enumeration','bulk_download'}

def validate_timeline(value, material_ids):
    """Keep comparisons attached to the incident and require a chronological summary."""
    if not material_ids:
        return
    dataset=logs()
    origin=min(material_ids,key=lambda key:dataset[key]['timestamp'])
    # Legitimate context is useful in specialist findings, not as a separate breach step.
    value['events'][:]=[event for event in value['events'] if event['log_ids'][0] in material_ids]
    if not value['events']:
        raise ValueError('The timeline contains no material incident events.')
    if origin in value['summary_log_ids']:
        value['summary_log_ids'].sort(key=lambda key:(key not in material_ids,dataset[key]['timestamp']))
    opening_cited=any(dataset[key]['action']=='attachment_open' for event in value['events'] for key in event['log_ids'])
    if value['events'][0]['log_ids'][0]!=origin or value['summary_log_ids'][0]!=origin:
        raise ValueError(f'Start timeline and summary citations with earliest material event {origin}; comparisons belong after a material primary event.')
    for event in value['events']:
        text=event['explanation'].casefold()
        if re.search(r'\bopen(?:s|ed|ing)?\b.*\b(?:attachment|invoice)\b|\b(?:attachment|invoice)\b.*\bopen(?:s|ed|ing)?\b',text):
            local_opening=any(dataset[key]['action']=='attachment_open' for key in event['log_ids'])
            if not local_opening and (dataset[event['log_ids'][0]]['source']=='email' or not opening_cited):
                raise ValueError(f'Unsupported opening claim in {event["log_ids"]}: {event["explanation"]} Email delivery proves arrival, not opening. Describe delivery here, or cite the endpoint attachment_open event in this item.')
    if dataset[origin]['source']=='email':
        text=value['summary'].casefold()
        first=re.search(r'\b(?:email|invoice|phishing|attachment)\b',text)
        later=re.search(r'\b(?:sign[ -]?in|login|token|download|exfiltration)\b',text)
        if not first or later and later.start()<first.start():
            raise ValueError('Summary reverses evidence chronology. Begin with the email or invoice, then token access, replayed sign in and file activity.')

async def lead(router,findings,session):
    ids={x for result in findings for finding in result['data']['findings'] for x in finding['log_ids']}
    material_ids={key for key in ids if material_event(logs()[key])}
    sources={}
    for key in sorted(material_ids):
        source=logs()[key]['source']
        group='endpoint_and_network' if source in ('endpoint','proxy_dns') else source
        sources.setdefault(group,[]).append(key)
    times=[{'log_id':key,'timestamp':logs()[key]['timestamp'],'action':logs()[key]['action'],'comparison_only':key not in material_ids} for key in sorted(ids,key=lambda key:logs()[key]['timestamp'])]
    return await router.call('lead',{'specialist_findings':[x['data'] for x in findings],'cited_event_times':times,'source_evidence':sources,
                             'material_event_ids':sorted(material_ids,key=lambda key:logs()[key]['timestamp']),
                             'instructions':'Connect the material attack findings into four to seven chronological events. Start the timeline and summary_log_ids with the first material_event_ids entry. Cover every specialist source in source_evidence, including its material finding. Exclude standalone routine or legitimate comparisons. Each explanation must use at most 12 words and describe one main action. Use plain terms such as finance account instead of addresses, session strings or host names. Put the primary material event ID first, and any comparison IDs after it. Email delivery does not prove attachment opening: cite the endpoint attachment_open event for that claim. Cite every event and summary. The summary must describe the earliest material action before later actions; begin with the email or invoice when it is the origin. Do not invent an earlier cause. Comparison baseline events may be earlier than the incident but are not its beginning. Do not add a second account unless findings contain it.'},
                             LeadResult,ids,rehearsal=session['label']=='REHEARSAL',scope=session)
