"""Bind only the web app to loopback; Funnel exposes this port, never inference."""
import os
from pathlib import Path
import uvicorn
from app.config import settings
if __name__=='__main__':
    Path('runtime').mkdir(exist_ok=True)
    Path('runtime/app.pid').write_text(str(os.getpid()))
    uvicorn.run('app.main:create_app',factory=True,host='127.0.0.1',port=settings.app_port,access_log=False,timeout_graceful_shutdown=5)
