"""Chaos fixture only. Owned loopback gateway to the unchanged live model service."""
import asyncio
import httpx
import uvicorn
from fastapi import FastAPI,Request
from fastapi.responses import StreamingResponse
app=FastAPI()
@app.post('/v1/chat/completions')
async def complete(request:Request):
    body=await request.body()
    async def stream():
        # Fault-injection window before forwarding; no production-model process is stopped.
        await asyncio.sleep(1)
        async with httpx.AsyncClient(timeout=7,trust_env=False) as client:
            async with client.stream('POST','http://127.0.0.1:8000/v1/chat/completions',content=body,headers={'Content-Type':'application/json'}) as r:
                async for chunk in r.aiter_bytes():yield chunk
    return StreamingResponse(stream(),media_type='text/event-stream')
if __name__=='__main__':uvicorn.run(app,host='127.0.0.1',port=8094,access_log=False,timeout_graceful_shutdown=0)
