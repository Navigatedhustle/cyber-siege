"""Private room hub: fixed upstream only, HTTP and WebSocket, no network reconfiguration."""
import argparse
import asyncio
import contextlib
import ipaddress
from urllib.parse import urlsplit
import httpx
import uvicorn
import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from .private import private_url

def relay_app(upstream):
    private_url(upstream)
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    @app.api_route('/{path:path}',methods=['GET','POST','HEAD'])
    async def http(path,request:Request):
        origin=request.headers.get('origin')
        if origin and urlsplit(origin).netloc!=request.headers.get('host'):
            return Response(status_code=403)
        body=await request.body()
        if len(body)>8192:return Response(status_code=413)
        headers={k:v for k,v in request.headers.items() if k.lower() in {'content-type','cookie','authorization','accept'}}
        suffix=request.url.path+('?' + request.url.query if request.url.query else '')
        try:
            async with httpx.AsyncClient(timeout=10,trust_env=False,follow_redirects=False) as client:
                response=await client.request(request.method,upstream+suffix,headers=headers,content=body)
            out={k:v for k,v in response.headers.items() if k.lower() not in {'content-encoding','transfer-encoding','content-length','connection'}}
            return Response(response.content,status_code=response.status_code,headers=out)
        except httpx.HTTPError:return Response('Private Fury link unavailable. Reconnecting is safe.',status_code=503)
    @app.websocket('/{path:path}')
    async def ws(path,ws:WebSocket):
        origin=ws.headers.get('origin')
        if origin and urlsplit(origin).netloc!=ws.headers.get('host'):
            await ws.close(code=1008);return
        await ws.accept()
        suffix=ws.url.path+('?' + ws.url.query if ws.url.query else '')
        target=upstream.replace('https:','wss:').replace('http:','ws:')+suffix
        try:
            async with websockets.connect(target,origin=upstream,additional_headers={'Cookie':ws.headers.get('cookie','')},
                                          proxy=None,max_size=1024*1024,open_timeout=5) as remote:
                async def to_remote():
                    while True:await remote.send(await ws.receive_text())
                async def to_client():
                    async for message in remote:await ws.send_text(message)
                tasks=[asyncio.create_task(to_remote()),asyncio.create_task(to_client())]
                try:
                    await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for t in tasks:t.cancel()
                    await asyncio.gather(*tasks,return_exceptions=True)
        except (OSError,websockets.WebSocketException,WebSocketDisconnect):pass
        finally:
            with contextlib.suppress(Exception):await ws.close(code=1013)
    return app

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--upstream',required=True)
    parser.add_argument('--listen',default='127.0.0.1')
    parser.add_argument('--port',type=int,default=8095)
    parser.add_argument('--check',action='store_true',help='Check the fixed upstream without opening a listening socket')
    args=parser.parse_args()
    private_url(args.upstream)
    if args.check:
        try:
            with httpx.Client(timeout=5,trust_env=False,follow_redirects=False) as client:
                health=client.get(args.upstream.rstrip('/')+'/health');health.raise_for_status()
                content=client.get(args.upstream.rstrip('/')+'/api/content');content.raise_for_status()
            print('Private Fury link ready:',health.json().get('status'))
            print('Generated QR base:',content.json()['base'])
            print('Check that this base is the address phones can reach on the room LAN.')
        except (httpx.HTTPError,ValueError,KeyError) as exc:
            parser.exit(1,'Private Fury link unavailable: '+type(exc).__name__+'\n')
        raise SystemExit(0)
    listen=ipaddress.ip_address(args.listen)
    if not listen.is_private or listen.is_unspecified or listen.is_multicast:
        parser.error('Bind a specific private LAN or loopback IP; never a public or wildcard address.')
    uvicorn.run(relay_app(args.upstream.rstrip('/')),host=args.listen,port=args.port,access_log=False,
                timeout_graceful_shutdown=2,ws_max_size=4096,ws_max_queue=8,proxy_headers=False)
