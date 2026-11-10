"""Start and stop only the isolated test processes owned by this script."""
import os
import atexit
from pathlib import Path
import subprocess
import sys
import time
import httpx
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

class Server:
    def __init__(self,name,port=8091,scale=.06,model_url=None):
        self.data=ROOT/'runtime'/name
        self.data.mkdir(parents=True,exist_ok=True)
        self.port=port
        self.base=f'http://127.0.0.1:{port}'
        env={**os.environ,'SIEGE_PORT':str(port),'SIEGE_DATA':str(self.data),'SIEGE_TIME_SCALE':str(scale)}
        if model_url:env['SIEGE_TEST_MODEL_URL']=model_url
        self.log=(self.data/'server.log').open('ab')
        self.process=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-m','revamp'],cwd=ROOT,env=env,stdout=self.log,stderr=self.log)
        atexit.register(self.close)
        self.client=httpx.Client(base_url=self.base,timeout=15,trust_env=False)
        for _ in range(100):
            if self.process.poll() is not None:raise RuntimeError('Test server exited: '+str(self.data/'server.log'))
            try:
                if self.client.get('/health').is_success:break
            except httpx.HTTPError:pass
            time.sleep(.1)
        else:raise RuntimeError('Test server did not become ready')
        password=(self.data/'first-launch-password.txt').read_text().strip()
        self.client.post('/api/login',json={'password':password}).raise_for_status()
    def close(self):
        if self.log.closed:
            return
        self.client.close()
        if self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)
        self.log.close()
    def create(self,teams=8,industry='healthcare'):
        r=self.client.post('/api/rooms',json={'industry':industry,'teams':teams});r.raise_for_status();return r.json()
