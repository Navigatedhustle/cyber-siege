"""Bounded SSE queues; slow phones recover using a full authenticated snapshot."""
import asyncio
import json
import time

class EventBus:
    def __init__(self):
        self.clients = {}
        self.sequence = 0

    def publish(self, event, data, audience=None):
        self.sequence += 1
        message={'id':self.sequence,'event':event,'data':data}
        for queue,(target,_) in list(self.clients.items()):
            if audience is None or target in (audience,'admin'):
                if queue.full():
                    queue.get_nowait()
                queue.put_nowait(message)

    async def stream(self, target):
        queue=asyncio.Queue(maxsize=128)
        self.clients[queue]=(target,time.time())
        try:
            yield 'retry: 2000\nevent: ready\ndata: {}\n\n'
            while True:
                try:
                    item=await asyncio.wait_for(queue.get(),15)
                    yield f"id: {item['id']}\nevent: {item['event']}\ndata: {json.dumps(item['data'])}\n\n"
                except asyncio.TimeoutError:
                    yield ': heartbeat\n\n'
        finally:
            self.clients.pop(queue,None)

    @property
    def phones(self):
        return len({target for target,_ in self.clients.values() if target not in ('screen','admin')})
