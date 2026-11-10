#!/usr/bin/env python3
"""Start the open-access individual experience and print its links."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from app.config import ROOT,settings


def health():
    try:
        response=httpx.get(f'http://127.0.0.1:{settings.app_port}/health',timeout=2,trust_env=False)
        if response.is_success:
            value=response.json()
            if value.get('inference')=='local only' and 'session_label' in value:return value
    except (httpx.HTTPError,ValueError):pass
    return None


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--quiet',action='store_true',help='Compatibility option; no access code is used');args=parser.parse_args()
    status=health()
    if not status:
        pid_path=ROOT/'runtime/app.pid'
        if pid_path.exists():
            pid=int(pid_path.read_text())
            process=Path(f'/proc/{pid}')
            if process.exists() and process.joinpath('cwd').resolve()==ROOT and b'app.serve' in process.joinpath('cmdline').read_bytes():
                raise SystemExit('The existing app is still starting or unhealthy. See runtime/app.log; no second worker was launched.')
        (ROOT/'runtime').mkdir(exist_ok=True)
        with (ROOT/'runtime/app.log').open('ab',buffering=0) as output:
            child=subprocess.Popen([str(ROOT/'.venv/bin/python'),'-m','app.serve'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        for _ in range(60):
            status=health()
            if status:break
            if child.poll() is not None:raise SystemExit('The app could not start. Read runtime/app.log; check whether its port is already used.')
            time.sleep(.25)
        else:raise SystemExit('The app is not ready. Read runtime/app.log.')
    base=settings.public_base_url.rstrip('/')
    print('\nCyber Siege is ready.\n')
    print(f'Start here:          {base}/')
    print(f'Presenter controls:    {base}/facilitator')
    print(f'Room screen:         {base}/screen')
    print(f'Individual play:         {base}/play')
    print('\n1. Open the homepage on your own device.')
    print('2. Press Start experience. No sign-in or room code is needed.')
    print('3. Follow the evidence and continue at your own pace.')
    print(f'\nQualified live models: {len(status["qualified_models"])}. '+('Replay is enabled.' if status['replay'] else 'Live mode.'))
    print('Everyone participates individually. Presenter controls are optional.\n')

if __name__=='__main__':main()
