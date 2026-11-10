import asyncio
from scenario.answer_key import EVIDENCE
from .retrieval import evidence_rows
from .schemas import ReviewResult

async def review(router,team,session,preferred):
    ids={x for key in team['evidence'] for x in EVIDENCE[key]['log_ids']}|{'FIL9003','FIL9005','FIL9002','IDP9001','NET9001','EML9001','EDR9001','EDR9002'}
    rows=evidence_rows(ids,True)
    return await router.call('twist_check',{'decision':team['decision'],'selected_evidence':team['evidence'],'new_event_log_id':'FIL9003','normal_backup_log_id':'FIL9005','logs':rows,
                             'instructions':'Independently review the new service account event FIL9003 against the normal backup FIL9005 and connect it to the earlier case. Cite both FIL9003 and FIL9005. Assess whether the team decision is supported; the source network and backup window matter. Use at most 50 words for explanation and 20 for uncertainty. Finish every sentence. Do not score the team.'},
                             ReviewResult,{x['id'] for x in rows},preferred,session['label']=='REHEARSAL',session)

async def two_model_check(router,team,session):
    models=router.lineup(session['label']=='REHEARSAL')
    selected=[x for x in ('hero','challenger') if x in models]
    results=await asyncio.gather(*(review(router,team,session,k) for k in selected),return_exceptions=True)
    output=[]
    seen=set()
    for result in results:
        if isinstance(result,Exception):
            output.append({'error':'Review unavailable. Evidence and deterministic score are preserved.'})
        elif result['model'] not in seen:
            seen.add(result['model']); output.append(result)
    return output
