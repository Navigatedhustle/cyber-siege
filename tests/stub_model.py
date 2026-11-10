"""CI style OpenAI compatible stub. Never used by the event application."""
import json
from fastapi import FastAPI,Request
from fastapi.responses import StreamingResponse

SPECIAL={
 'identity':[('The finance session signs in from a new network without a fresh MFA prompt.',['IDP9001'])],
 'email':[('A lookalike supplier sends the invoice attachment.',['EML9001'])],
 'endpoint':[('The invoice opens before browser token access and a call to the lookalike site.',['EDR9001','EDR9002','NET9001'])],
 'data_access':[('The same session enumerates and downloads confidential finance files.',['FIL9001','FIL9002'])],
}

def make_stub():
    stub=FastAPI()
    @stub.get('/health')
    async def health():return {'status':'ok'}
    @stub.get('/v1/models')
    async def models(): return {'data':[{'id':'nemotron-3-super'},{'id':'openai/gpt-oss-120b'}]}
    @stub.get('/metrics')
    async def metrics(): return {'detail':'No counters in stub'}
    @stub.post('/v1/chat/completions')
    async def complete(request:Request):
        body=await request.json(); value=json.loads(body['messages'][-1]['content']); role=value['role']
        if role in SPECIAL:
            output={'findings':[{'summary':text,'log_ids':ids,'confidence':'high'} for text,ids in SPECIAL[role]],'entities':['m.brooks']}
        elif role=='lead':
            output={'events':[{'explanation':text,'log_ids':ids} for rows in SPECIAL.values() for text,ids in rows],
                    'summary':'The invoice led to stolen session access and finance downloads.','summary_log_ids':['EML9001','NET9001','IDP9001','FIL9002']}
        else:
            output={'verdict':'supports','explanation':'The backup account used the same unusual source outside its window. Containment is supported.','log_ids':['FIL9003','FIL9005'],'uncertainty':'The scope of stolen access still requires investigation.'}
        async def chunks():
            text=json.dumps(output)
            for start in range(0,len(text),30):
                yield 'data: '+json.dumps({'choices':[{'delta':{'content':text[start:start+30]}}]})+'\n\n'
            yield 'data: '+json.dumps({'choices':[],'usage':{'completion_tokens':100,'prompt_tokens':100}})+'\n\n'
            yield 'data: [DONE]\n\n'
        return StreamingResponse(chunks(),media_type='text/event-stream')
    return stub
