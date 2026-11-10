"""Private FastAPI HTTP/WebSocket surfaces; one process owns all room rules."""
import asyncio
import contextlib
import hashlib
import hmac
import io
import json
import os
import secrets
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from urllib.parse import urlencode, urlsplit
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, ValidationError
import qrcode
from . import settings
from .ai import LocalAgents
from .content import ROBOTS, VILLAINS, INDUSTRIES, INDUSTRY_ICONS
from .playbook import render_pdf
from typing import Literal
from .engine import Engine, GameError

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Login(StrictModel):
    password: str = Field(min_length=1, max_length=200)

class Create(StrictModel):
    industry: str = 'healthcare'
    teams: int = Field(default=8, ge=1, le=8)

class Join(StrictModel):
    code: str = Field(min_length=6, max_length=6, pattern='^[A-Za-z0-9]+$')
    name: str = Field(default='Seller', max_length=80)
    team: str | None = Field(default=None, max_length=2)
    token: str | None = Field(default=None, max_length=100)
    station: str | None = Field(default=None, max_length=100)

class Control(StrictModel):
    command: str = Field(max_length=32)
    value: str | bool | dict | None = None

class Message(StrictModel):
    type: str = Field(max_length=20)
    action: str | None = Field(default=None, max_length=20)
    building: int | None = Field(default=None, ge=0, le=5, strict=True)
    nonce: str | None = Field(default=None, max_length=64)

class Experience(StrictModel):
    nonce: str = Field(min_length=16, max_length=80, pattern='^[A-Za-z0-9_-]+$')
    industry: str = Field(default='healthcare', max_length=32)

class ExperienceControl(StrictModel):
    command: Literal['start', 'next', 'pause', 'reset', 'restart', 'deploy']
    industry: str | None = Field(default=None, max_length=32)

class AccountCard(StrictModel):
    account: str = Field(default='', max_length=80)
    next_step: str = Field(default='', max_length=200)

class Security:
    def __init__(self, data):
        self.path = data / 'auth.json'
        if not self.path.exists():
            password = os.getenv('SIEGE_INITIAL_PASSWORD') or secrets.token_urlsafe(18)
            salt = secrets.token_hex(16)
            value = {'salt': salt, 'hash': self.digest(password, salt), 'secret': secrets.token_hex(32)}
            self.path.write_text(json.dumps(value))
            self.path.chmod(0o600)
            credentials = data / 'first-launch-password.txt'
            credentials.write_text(password + '\n')
            credentials.chmod(0o600)
        self.auth = json.loads(self.path.read_text())
        self.sessions = {}
        self.buckets = defaultdict(deque)

    @staticmethod
    def digest(password, salt):
        return hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1).hex()

    def check(self, password):
        return hmac.compare_digest(self.auth['hash'], self.digest(password, self.auth['salt']))

    def admin(self, token):
        return self.sessions.get(token or '', 0) > time.time()

    def limit(self, key, count, window):
        bucket = self.buckets[key]
        now = time.monotonic()
        while bucket and now - bucket[0] > window:
            bucket.popleft()
        if len(bucket) >= count:
            raise GameError('Too many requests. Wait a moment and retry.')
        bucket.append(now)
        # Bound memory used by expired per-client buckets.
        if len(self.buckets) > 5000:
            for old in list(self.buckets)[:1000]:
                if not self.buckets[old] or now - self.buckets[old][-1] > 120:
                    del self.buckets[old]

    def station(self, room, team):
        return hmac.new(self.auth['secret'].encode(), f'{room}:{team}'.encode(), 'sha256').hexdigest()


def create_app():
    engine = Engine(settings.DATA)
    security = Security(settings.DATA)
    agents = LocalAgents(engine.emit, settings.DATA)
    engine.agents = agents
    pdf_semaphore = asyncio.Semaphore(2)
    pdf_cache = {}

    @asynccontextmanager
    async def lifespan(app):
        task = asyncio.create_task(engine.tick())
        yield
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        await engine.close()
        await agents.close()

    app = FastAPI(title='Cyber Siege · Northwind', lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
    app.state.engine = engine
    app.state.security = security
    app.state.agents = agents

    @app.exception_handler(GameError)
    async def game_error(request, exc):
        return JSONResponse({'error': str(exc)}, status_code=400)

    @app.exception_handler(Exception)
    async def safe_error(request, exc):
        # Full diagnostics go only to process stderr; no traceback/request payload goes to clients.
        import logging
        logging.getLogger('siege').exception('Server error')
        return JSONResponse({'error': 'The game is recovering. Retry shortly.'}, status_code=500)

    @app.middleware('http')
    async def boundaries(request, call_next):
        origin = request.headers.get('origin')
        if request.method not in {'GET', 'HEAD'} and origin and urlsplit(origin).netloc != request.headers.get('host'):
            return JSONResponse({'error': 'Use the game’s own page.'}, status_code=403)
        try:
            security.limit(('http', request.client.host), 600, 10)
        except GameError as exc:
            return JSONResponse({'error': str(exc)}, status_code=429)
        if int(request.headers.get('content-length', '0') or 0) > 8192:
            return JSONResponse({'error': 'Request too large.'}, status_code=413)
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; media-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
        if request.url.path.startswith('/api'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    def require_admin(request):
        if not security.admin(request.cookies.get('siege_admin')):
            raise GameError('Sign in to facilitator controls.')

    def token_from(request):
        auth = request.headers.get('authorization', '')
        return auth[7:] if auth.startswith('Bearer ') else None

    @app.get('/health')
    async def health():
        return {'status': 'ok', 'game': 'revamp', 'rooms': len(engine.rooms), 'rehearsal': settings.SCALE != 1,
                'model': settings.MODEL, 'bind': '127.0.0.1', 'active_agents': agents.active}

    @app.get('/api/content')
    async def content():
        return {'robots': ROBOTS, 'villains': VILLAINS, 'industries': INDUSTRIES, 'industry_icons': INDUSTRY_ICONS, 'base': settings.BASE, 'hp_resources': json.loads((settings.ROOT / 'config/hp_resources.json').read_text())['resources'], 'story_sources': json.loads((settings.ROOT / 'config/local_ai_story_sources.json').read_text())['sources']}

    @app.post('/api/experience')
    async def experience(body: Experience, request: Request):
        security.limit(('experience', request.client.host), 240, 60)
        room, token = engine.experience(body.nonce, body.industry)
        return {'token': token, 'state': engine.public(room, player_token=token)}

    @app.get('/api/experience/share.png')
    async def share_qr(url: str):
        try:
            if len(url) > 300 or urlsplit(url).path not in {'', '/'}:
                raise ValueError('Only the experience root can be shared')
            target = settings.private_url(url) + '/'
        except ValueError:
            raise GameError('Share the private experience link from this page.')
        buffer = io.BytesIO()
        qrcode.make(target).save(buffer, format='PNG')
        return Response(buffer.getvalue(), media_type='image/png')

    @app.post('/api/experience/control')
    async def experience_control(body: ExperienceControl, request: Request):
        token = token_from(request)
        room = engine.owned_experience(token)
        security.limit(('experience_control', token), 30, 10)
        engine.experience_control(room, body.command, body.industry)
        await engine.emit(room)
        return engine.public(room, player_token=token)

    @app.post('/api/experience/card')
    async def account_card(body: AccountCard, request: Request):
        token = token_from(request)
        room = engine.owned_experience(token)
        if room['phase'] != 'debrief':
            raise GameError('Your Account Action Card is available after the challenges.')
        def clean(value):
            return ''.join(c for c in value.strip() if c.isprintable())
        room['card'] = {'account': clean(body.account), 'next_step': clean(body.next_step)}
        engine.save(room)
        return engine.public(room, player_token=token)

    @app.get('/api/experience/card.pdf')
    async def account_card_pdf(request: Request):
        token = token_from(request)
        room = engine.owned_experience(token)
        if room['phase'] != 'debrief':
            raise GameError('Finish the experience to download your Account Action Card.')
        from .action_card import render_action_card
        import copy
        snapshot = copy.deepcopy(room)
        async with pdf_semaphore:
            data = await asyncio.to_thread(render_action_card, snapshot)
        return Response(data, media_type='application/pdf', headers={
            'Content-Disposition': 'attachment; filename="HP-Account-Action-Card.pdf"', 'Cache-Control':'no-store'})

    @app.post('/api/login')
    async def login(body: Login, request: Request):
        security.limit(('login', request.client.host), 8, 60)
        if not security.check(body.password):
            return JSONResponse({'error': 'Password not recognized.'}, status_code=401)
        token = secrets.token_urlsafe(32)
        security.sessions[token] = time.time() + 18 * 3600
        response = JSONResponse({'ok': True})
        response.set_cookie('siege_admin', token, httponly=True, samesite='strict',
                            secure=settings.BASE.startswith('https:'), max_age=18 * 3600)
        return response

    @app.post('/api/logout')
    async def logout(request: Request):
        security.sessions.pop(request.cookies.get('siege_admin', ''), None)
        response = JSONResponse({'ok': True})
        response.delete_cookie('siege_admin')
        return response

    @app.get('/api/admin')
    async def admin(request: Request):
        require_admin(request)
        return {'rooms': [{'code': r['code'], 'phase': r['phase']} for r in engine.rooms.values()],
                'base': settings.BASE}

    @app.post('/api/rooms')
    async def create(body: Create, request: Request):
        require_admin(request)
        room = engine.create(body.industry, body.teams)
        return engine.public(room, admin=True)

    @app.post('/api/join')
    async def join(body: Join, request: Request):
        # A room hub presents one IP for all devices. Capacity accommodates 64 clients;
        # unique new records and per-connection messages remain bounded separately.
        security.limit(('join', request.client.host), 120, 60)
        station = False
        if body.station:
            expected = security.station(body.code.upper(), body.team)
            if not hmac.compare_digest(body.station, expected):
                raise GameError('Station link is invalid. Ask the facilitator for a fresh link.')
            station = True
        token, player = engine.join(body.code, body.name, body.team, station, body.token)
        await engine.emit(engine.room(body.code))
        return {'token': token, 'state': engine.public(engine.room(body.code), player_token=token)}

    @app.get('/api/rooms/{code}')
    async def state(code: str, request: Request):
        room = engine.room(code)
        return engine.public(room, security.admin(request.cookies.get('siege_admin')), token_from(request))

    @app.post('/api/rooms/{code}/control')
    async def control(code: str, body: Control, request: Request):
        require_admin(request)
        room = engine.room(code)
        engine.control(room, body.command, body.value)
        await engine.emit(room)
        return engine.public(room, admin=True)

    @app.get('/api/rooms/{code}/stations')
    async def stations(code: str, request: Request):
        require_admin(request)
        room = engine.room(code)
        return [{'team': tid, 'url': settings.BASE + '/station?' + urlencode({'room': code, 'team': tid,
                  'station': security.station(code, tid)}),
                 'qr': '/qr?' + urlencode({'room': code, 'team': tid, 'station': security.station(code, tid)})}
                for tid in room['teams']]

    @app.get('/qr')
    async def qr(room: str, team: str | None = None, station: str | None = None, kind: Literal['play', 'playbook'] = 'play'):
        engine.room(room)
        if station and (not team or not hmac.compare_digest(station, security.station(room, team))):
            raise GameError('Unknown station.')
        args = {'room': room}
        path = '/playbook' if kind == 'playbook' else '/play'
        if station:
            args.update(team=team, station=station)
            path = '/station'
        out = io.BytesIO()
        qrcode.make(settings.BASE + path + '?' + urlencode(args)).save(out, format='PNG')
        return Response(out.getvalue(), media_type='image/png', headers={'Cache-Control': 'no-store'})

    @app.get('/playbook')
    async def legacy_playbook():
        return RedirectResponse('/', status_code=307)

    @app.get('/api/rooms/{code}/playbook.pdf')
    async def pdf(code: str, team: str):
        r = engine.room(code)
        if r['phase'] != 'debrief' or team not in r['teams']:
            raise GameError('Choose your team’s playbook during the debrief.')
        # Snapshot before entering a thread: renderer sees a consistent completed result.
        import copy
        snapshot = copy.deepcopy(r)
        from .playbook import STORY_PATH
        stamp = STORY_PATH.stat().st_mtime_ns if STORY_PATH.exists() else 0
        key = hashlib.sha256(json.dumps([code, snapshot['industry'], snapshot['teams'][team],
                                        snapshot['power']['tokens'], snapshot['power']['peak'],
                                        snapshot['power']['evidence'], snapshot['power']['cloud_bytes'], stamp]).encode()).hexdigest()
        async with pdf_semaphore:
            if key not in pdf_cache:
                if len(pdf_cache) > 256:
                    pdf_cache.clear()
                pdf_cache[key] = await asyncio.to_thread(render_pdf, snapshot, snapshot['teams'][team])
            data = pdf_cache[key]
        return Response(data, media_type='application/pdf', headers={'Content-Disposition': f'attachment; filename="Seller-Playbook-Team-{team}.pdf"'})

    @app.websocket('/ws/{code}')
    async def websocket(ws: WebSocket, code: str):
        origin = ws.headers.get('origin')
        if origin and urlsplit(origin).netloc != ws.headers.get('host'):
            await ws.close(code=1008)
            return
        try:
            security.limit(('ws', ws.client.host), 150, 60)
            room = engine.room(code)
        except GameError:
            await ws.close(code=1008)
            return
        await ws.accept()
        # Credentials travel in the first frame, never URL/logs/public snapshots.
        peer = None
        sender = None
        try:
            raw = await asyncio.wait_for(ws.receive_text(), 5)
            if len(raw) > 1024:
                raise GameError('Invalid connection.')
            hello = json.loads(raw)
            if not isinstance(hello, dict) or set(hello) - {'type', 'token'} or hello.get('type') != 'hello':
                raise GameError('Invalid handshake.')
            token = hello.get('token')
            admin = security.admin(ws.cookies.get('siege_admin'))
            if token is not None and (not isinstance(token, str) or token not in room['players']):
                raise GameError('Reconnect from the join page.')
            if token:
                room['players'][token]['connected'] = True
            peer = {'queue': asyncio.Queue(maxsize=2), 'admin': admin, 'token': token}
            engine.peers.setdefault(code, []).append(peer)
            async def send():
                while True:
                    await ws.send_json(await peer['queue'].get())
            sender = asyncio.create_task(send())
            await engine.emit(room)
            messages = deque()
            while True:
                raw = await ws.receive_text()
                if len(raw) > 2048:
                    raise GameError('Message too large.')
                now = time.monotonic()
                while messages and now - messages[0] > 1:
                    messages.popleft()
                if len(messages) >= 15:
                    raise GameError('Slow down. Your team’s last action is saved.')
                messages.append(now)
                message = Message.model_validate_json(raw)
                if message.type == 'ping':
                    packet = {'type': 'pong', 'nonce': message.nonce}
                    if peer['queue'].full():
                        peer['queue'].get_nowait()
                    peer['queue'].put_nowait(packet)
                elif message.type == 'action' and token:
                    try:
                        engine.action(room, room['players'][token]['team'], message.action, message.building)
                        await engine.emit(room)
                    except GameError as exc:
                        packet = {'type': 'notice', 'text': str(exc)}
                        if peer['queue'].full():
                            peer['queue'].get_nowait()
                        peer['queue'].put_nowait(packet)
                else:
                    raise GameError('Invalid game message.')
        except (WebSocketDisconnect, asyncio.TimeoutError):
            pass
        except (GameError, ValidationError, ValueError, TypeError):
            with contextlib.suppress(Exception):
                await ws.close(code=1008, reason='Reconnect using the game page.')
        finally:
            if sender:
                sender.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await sender
            if peer:
                engine.peers.get(code, []).remove(peer)
                if peer['token'] and not any(p['token'] == peer['token'] for p in engine.peers.get(code, [])):
                    room['players'][peer['token']]['connected'] = False
                    room['players'][peer['token']]['last_seen'] = time.time()
                    engine.save(room)

    app.mount('/assets', StaticFiles(directory=settings.ROOT / 'web'), name='assets')
    @app.get('/')
    async def experience_page():
        return FileResponse(settings.ROOT / 'web/experience.html', headers={'Cache-Control':'no-cache'})

    for path in ['/screen', '/play', '/station', '/stations', '/facilitator']:
        app.add_api_route(path, lambda: RedirectResponse('/', status_code=307), methods=['GET'], include_in_schema=False)
    return app
