#!/usr/bin/env python3
"""Fresh Fury entry point; delegates model and app ownership to existing launchers."""
import argparse
import ctypes.util
import hashlib
import json
import os
from pathlib import Path
import platform
import select
import shutil
import signal
import socket
import subprocess
import sys
import time
from urllib.request import ProxyHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
MODEL_CACHE = ROOT / 'runtime/huggingface/hub'
MODELS = {
    'hp-nemotron-serve': ('8000', 'nemotron-3-super'),
    'cyber-siege-challenger': ('8001', 'openai/gpt-oss-120b'),
}
HTTP = build_opener(ProxyHandler({}))


def run(args, **kwargs):
    return subprocess.run(args, cwd=ROOT, check=True, **kwargs)


def docker(args, capture=True):
    # Pass arguments as shell-quoted code only when changing supplementary group.
    import shlex
    direct = subprocess.run(['/usr/bin/docker', 'info'], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode == 0
    command = ['/usr/bin/docker', *args]
    if not direct:
        command = ['sg', 'docker', '-c', shlex.join(command)]
    result = run(command, text=True, stdout=subprocess.PIPE if capture else None,
                 stderr=subprocess.PIPE if capture else None)
    return result.stdout if capture else ''


def inspect(name):
    try:
        return json.loads(docker(['inspect', name]))[0]
    except subprocess.CalledProcessError as e:
        detail=((e.stderr or '') + (e.stdout or '')).casefold()
        if 'no such object' in detail or 'no such container' in detail:
            return None
        raise


def owned_container(info):
    """Check the actual read-only model mount, not just a reusable container name."""
    if not info:
        return False
    mounts = {Path(m['Source']).resolve() for m in info.get('Mounts', []) if m['Type'] == 'bind'}
    name = info['Name'].lstrip('/')
    if name == 'hp-nemotron-serve':
        return (MODEL_CACHE / 'models--nvidia--NVIDIA-Nemotron-3-Super-120B-A12B-NVFP4').resolve() in mounts
    if name == 'cyber-siege-challenger':
        return (info['Config'].get('Labels', {}).get('cyber-siege.repo') == str(ROOT)
                and MODEL_CACHE.resolve() in mounts)
    return False


def json_get(port, path):
    with HTTP.open(f'http://127.0.0.1:{port}{path}', timeout=5) as response:
        return json.load(response)


def listening(port):
    with socket.socket() as probe:
        return probe.connect_ex(('127.0.0.1', int(port))) == 0


def preflight():
    errors = []
    if platform.system() != 'Linux' or platform.machine() != 'aarch64':
        errors.append('Use the tested Ubuntu 24.04 ARM64 HP ZGX Fury / GB300.')
    if sys.version_info[:2] != (3, 12):
        errors.append('Python 3.12 is required.')
    for name in ['bash', 'curl', 'tar', 'nvidia-smi', 'docker', 'sg']:
        if not shutil.which(name):
            errors.append('Missing prerequisite: ' + name)
    for name in ['pango-1.0', 'pangoft2-1.0', 'harfbuzz']:
        if not ctypes.util.find_library(name):
            errors.append('Missing PDF runtime library: ' + name)
    if errors:
        raise RuntimeError('\n'.join(errors) + '\nSee docs/FRESH_FURY_GUIDE.md.')
    gpu = run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader,nounits'],
              capture_output=True, text=True).stdout.strip()
    if len(gpu.splitlines()) != 1 or 'GB300' not in gpu or int(gpu.split(',')[-1]) < 256000:
        raise RuntimeError('This release is qualified for one GB300 with approximately 256703 MiB HBM.')
    docker(['info'])
    print('Prerequisites available:', gpu, flush=True)


def setup():
    preflight()
    run(['bash', 'scripts/setup.sh'])
    fingerprint = hashlib.sha256((ROOT / 'requirements.lock').read_bytes()).hexdigest()
    (ROOT / 'runtime/fresh-setup.json').write_text(json.dumps({'requirements_sha256': fingerprint}))


def ensure_setup():
    try:
        stamp = json.loads((ROOT / 'runtime/fresh-setup.json').read_text())
        current = hashlib.sha256((ROOT / 'requirements.lock').read_bytes()).hexdigest()
        if stamp['requirements_sha256'] == current and (ROOT / '.venv/bin/python').exists():
            return
    except (OSError, ValueError, KeyError):
        pass
    setup()


def validate_ownership():
    for name, (port, _) in MODELS.items():
        info = inspect(name)
        if info and not owned_container(info):
            raise RuntimeError(f'{name} belongs to another installation; left untouched.')
        if listening(port) and not (info and info['State']['Running']):
            raise RuntimeError(f'Port {port} is owned by another service; left untouched.')


def start_models():
    preflight()
    validate_ownership()
    allowed = set()
    for name in MODELS:
        info = inspect(name)
        if info and info['State']['Running']:
            for line in docker(['top', name, '-eo', 'pid']).splitlines()[1:]:
                if line.strip().isdigit():
                    allowed.add(int(line.strip()))
    gpu_pids = run(['nvidia-smi', '--query-compute-apps=pid', '--format=csv,noheader,nounits'],
                   capture_output=True, text=True).stdout.splitlines()
    unknown = [p.strip() for p in gpu_pids if p.strip().isdigit() and int(p.strip()) not in allowed]
    if unknown:
        raise RuntimeError('Another GPU workload is active; stop it with its own launcher first. PIDs: ' + ', '.join(unknown))
    run(['bash', 'scripts/models_up.sh'])
    for _, (port, model) in MODELS.items():
        ids = {item['id'] for item in json_get(port, '/v1/models')['data']}
        if model not in ids:
            raise RuntimeError(f'Unexpected model on {port}; expected {model}, got {sorted(ids)}')
    print('Both pinned local models are ready.', flush=True)


def stop_legacy():
    path = ROOT / 'runtime/app.pid'
    if not path.exists():
        return
    pid = int(path.read_text())
    proc = Path(f'/proc/{pid}')
    if not proc.exists():
        return
    args = proc.joinpath('cmdline').read_bytes().split(b'\0')
    if proc.joinpath('cwd').resolve() != ROOT or b'app.serve' not in args:
        raise RuntimeError('Legacy app PID identity does not match; left untouched.')
    # Pin identity across the subsequent signal to prevent PID reuse.
    fd = os.pidfd_open(pid)
    try:
        if proc.joinpath('cwd').resolve() != ROOT or proc.joinpath('cmdline').read_bytes().split(b'\0') != args:
            raise RuntimeError('Legacy process identity changed; left untouched.')
        signal.pidfd_send_signal(fd, signal.SIGTERM)
        if select.select([fd], [], [], 10)[0]:
            print('Stopped legacy app PID', pid)
            return
        raise RuntimeError('Legacy process has not stopped; no force signal sent.')
    finally:
        os.close(fd)


def stop():
    # Verify ownership before any container mutation, then delegate existing lifecycles.
    validate_ownership()
    run([sys.executable, 'siege', 'stop'])
    stop_legacy()
    run(['bash', 'scripts/models_down.sh'])
    for name in MODELS:
        info = inspect(name)
        if info and info['State']['Running']:
            raise RuntimeError(name + ' is still running.')
    print('Cyber Siege app and models stopped. Source, weights, caches and saved progress retained.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', nargs='?', default='start',
                        choices=['start', 'setup', 'download', 'models', 'status', 'stop', 'doctor'])
    args = parser.parse_args()
    if args.command == 'doctor':
        preflight()
    elif args.command == 'setup':
        setup()
    elif args.command == 'download':
        ensure_setup()
        run(['bash', 'scripts/download_models.sh'])
    elif args.command == 'models':
        ensure_setup()
        start_models()
    elif args.command == 'start':
        preflight()
        ensure_setup()
        validate_ownership()
        # hf download resumes/verifies the pinned snapshot and Docker reuses pinned images.
        run(['bash', 'scripts/download_models.sh'])
        start_models()
        run([sys.executable, 'siege', 'start'])
        print('\nOPEN: http://127.0.0.1:8090/\nPress Start the story. Remote access: docs/ROOM_SETUP.md.', flush=True)
        if os.getenv('DISPLAY') or os.getenv('WAYLAND_DISPLAY'):
            subprocess.Popen(['xdg-open', 'http://127.0.0.1:8090/'], stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    elif args.command == 'stop':
        stop()
    elif args.command == 'status':
        run([sys.executable, 'siege', 'status'])
        run(['bash', 'scripts/models_status.sh'])


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, OSError, subprocess.CalledProcessError) as exc:
        print('Cyber Siege: ' + str(exc), file=sys.stderr)
        sys.exit(1)
