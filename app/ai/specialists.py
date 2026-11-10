"""Four specialists use different sources, with progress tied to real work."""
from .retrieval import search_logs
from .schemas import SpecialistResult

async def investigate_specialist(router,role,alert,session,emit):
    selection=search_logs(role,alert,False)
    await emit({'agent':role,'status':'started','query':selection['query'],'events_scanned':selection['events_scanned']})
    payload={'starting_alert':alert,'logs':selection['rows'],'instructions':'Identify connections and anomalies. Cite IDs. At most three findings, each summary at most 35 words, with at most four log IDs each. Look for the suspicious supplier domain, stolen session or unusual network in your own source. Explain any benign comparison separately. Do not discuss events not present.'}
    allowed={row['id'] for row in selection['rows']}
    result=await router.call(role,payload,SpecialistResult,allowed,rehearsal=session['label']=='REHEARSAL',scope=session)
    for finding in result['data']['findings']:
        await emit({'agent':role,'status':'finding','finding':finding,'model':result['model']})
    await emit({'agent':role,'status':'done','model':result['model'],'tokens_used':(result.get('usage') or {}).get('completion_tokens')})
    return result
