import uvicorn
from .settings import PORT
if __name__ == '__main__':
    uvicorn.run('revamp.server:create_app', factory=True, host='127.0.0.1', port=PORT,
                access_log=False, timeout_graceful_shutdown=3, ws_max_size=4096, ws_max_queue=8,
                proxy_headers=False)
