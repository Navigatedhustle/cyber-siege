"""Single authoritative, persisted room engine. Player inputs, not AI, decide scores."""
import asyncio
import copy
import hashlib
import json
import re
import secrets
import sqlite3
import time
from collections import deque
from . import settings
from .content import ROBOTS, INDUSTRIES, WAVES
from .story import new_story, apply_step, step_cloud_check, STEP_SECONDS

ORDER = list(ROBOTS)
PHASES = ['lobby', 'briefing', 'wave', 'translate', 'debrief']
BAD = re.compile(r'(fuck|shit|cunt|nigger|nazi|bitch|asshole)', re.I)

def nickname(value):
    value = re.sub(r'[^\w .]', '', str(value), flags=re.UNICODE).strip()[:24]
    if not value or BAD.search(value):
        return 'Friendly seller'
    return value

class GameError(Exception):
    pass

class Engine:
    def __init__(self, data):
        self.data = data
        data.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(data / 'rooms.sqlite3')
        self.db.execute('pragma journal_mode=WAL')
        self.db.execute('create table if not exists rooms(code text primary key, state text not null)')
        self.db.execute('create table if not exists experiences(nonce text primary key, room text unique not null, token text unique not null)')
        self.db.commit()
        self.rooms = {}
        for code, raw in self.db.execute('select code,state from rooms'):
            room = json.loads(raw)
            # Restart pauses active shows, retaining remaining game seconds.
            if room['phase'] not in {'lobby', 'debrief'}:
                room['paused'] = True
            room['last_tick'] = time.time()
            room['generation'] += 1
            room['bubbles'] = {}
            if room.get('story', {}).get('running'):
                room['story']['analysis_interrupted'] = True
            room['power']['active'] = 0
            for player in room['players'].values():
                player['connected'] = False
            self.rooms[code] = room
        self.peers = {}
        self.tasks = set()
        self.agents = None
        self.cpu = 0
        self.rss = 0
        self.pending_saves = {}

    def save(self, room, defer=False):
        if defer:
            self.pending_saves[room['code']] = room
            return
        self.pending_saves.pop(room['code'], None)
        self.db.execute('insert or replace into rooms values(?,?)', (room['code'], json.dumps(room)))
        self.db.commit()

    def flush_pending(self):
        if not self.pending_saves:
            return
        # Snapshot current objects, so an interleaved owner action cannot be overwritten
        # with an older tick. User actions still commit immediately through save().
        rows = [(code, json.dumps(room)) for code, room in self.pending_saves.items()]
        self.db.executemany('insert or replace into rooms values(?,?)', rows)
        self.db.commit()
        self.pending_saves.clear()

    def create(self, industry='healthcare', teams=8, personal=False):
        if industry not in INDUSTRIES or not isinstance(teams, int) or not 1 <= teams <= 8:
            raise GameError('Choose an available industry and 1 to 8 teams.')
        if personal and sum(r.get('personal', False) and r['phase'] != 'debrief' for r in self.rooms.values()) >= 150:
            raise GameError('The experience is busy. Please try again shortly.')
        if not personal and sum(not r.get('personal') for r in self.rooms.values()) >= 40:
            raise GameError('Room limit reached. Restart with an archived data directory.')
        code = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZ23456789') for _ in range(6))
        room = {'code': code, 'industry': industry, 'phase': 'lobby', 'wave': 0, 'remaining': 0,
                'personal': personal,
                'paused': False, 'players': {}, 'teams': {}, 'generation': 0, 'bubbles': {},
                'intensity': 'reduced', 'sound': False, 'last_tick': time.time(), 'created': time.time(),
                'notice': 'Welcome to Northwind. A fictional business. A real team challenge.',
                'history': [], 'autopilot_next': {}, 'wave_elapsed': 0,
                'power': {'active': 0, 'peak': 0, 'tokens': 0, 'evidence': 0, 'cloud_bytes': 0, 'local_bytes': 0, 'rates': []}}
        for i in range(teams):
            room['teams'][str(i + 1)] = self.new_team(i + 1)
        self.rooms[code] = room
        self.save(room)
        return room

    def experience(self, nonce, industry='healthcare', guided=True):
        existing = self.db.execute('select room,token from experiences where nonce=?', (nonce,)).fetchone()
        if existing:
            code, token = existing
            room = self.room(code)
            if guided and room['phase'] == 'lobby' and not room.get('guided'):
                room['guided'] = True
                self.save(room)
            return room, token
        room = self.create(industry, teams=1, personal=True)
        room['teams']['1']['name'] = 'Your result'
        room['guided'] = guided
        token, _ = self.join(room['code'], 'Seller', '1')
        self.db.execute('insert into experiences values(?,?,?)', (nonce, room['code'], token))
        self.save(room)
        return room, token

    def owned_experience(self, token):
        if not token:
            raise GameError('Open the experience again to reconnect.')
        row = self.db.execute('select room from experiences where token=?', (token,)).fetchone()
        if not row:
            raise GameError('Open the experience again to reconnect.')
        return self.room(row[0])

    def experience_control(self, room, command, industry=None):
        if not room.get('personal'):
            raise GameError('This control belongs to your personal experience.')
        if command in {'reset', 'restart'}:
            self.control(room, 'reset')
            room['guided'] = True
            room.pop('story', None)
            room['human_reviews'] = []
            room['teams']['1']['name'] = 'Your result'
            room['card'] = {}
            room['power'] = {'active': 0, 'peak': 0, 'tokens': 0, 'evidence': 0, 'cloud_bytes': 0, 'local_bytes': 0, 'rates': []}
            room['last_tick'] = time.time()
            if command == 'restart':
                self.start_wave(room, 1)
        elif command == 'start':
            if room['phase'] == 'lobby':
                if industry:
                    self.control(room, 'industry', industry)
                if room.get('guided'):
                    self.start_wave(room, 1)
                else:
                    self.advance(room)
        elif command == 'deploy':
            if not room.get('guided') or room['phase'] != 'wave' or room['paused']:
                raise GameError('Start an incident before deploying your squad.')
            story = room['story']
            if story['stage'] == 'cloud_check':
                raise GameError('Wait for the scenario’s cloud request check to finish.')
            if not story['running'] and story['cursor'] == 0:
                story.update(running=True, stage='deploying', analysis_interrupted=False)
                self.run_agents(room, ORDER)
        elif command == 'next':
            if room['phase'] not in {'briefing', 'translate'}:
                raise GameError('Finish the current challenge before continuing.')
            room['paused'] = False
            self.advance(room)
        elif command == 'pause':
            self.control(room, 'pause')
            if not room['paused'] and room.get('story', {}).get('analysis_interrupted'):
                room['story']['analysis_interrupted'] = False
                self.run_agents(room, ORDER)
        else:
            raise GameError('Choose an available experience action.')
        self.save(room)

    def step_guided(self, room, defer=False):
        story = room['story']
        if not story['running'] or room['paused'] or story['cursor'] >= len(ORDER):
            return
        i = story['cursor']
        role = ORDER[i]
        bubble = room['bubbles'].get(role, {})
        analysis_ready = self.agents is None or bubble.get('status') in {'success', 'alert'}
        if story['elapsed'] >= STEP_SECONDS[i] and analysis_ready:
            apply_step(room)
            if story['cursor'] == len(ORDER):
                story['running'] = False
                self.contain(room, defer=defer)
            self.save(room, defer=defer)

    @staticmethod
    def new_team(i):
        return {'id': str(i), 'name': f'Team {i:02}', 'score': 0, 'trust': 100., 'risk': 0., 'records': 0.,
                'progress': [], 'completed': False, 'autopilot': False, 'buildings': ['safe'] * 6,
                'times': {}, 'fast': 0, 'wave_score': 0, 'last_action': '', 'isolated': False, 'robot_uses': {r: 0 for r in ROBOTS}}

    def room(self, code):
        room = self.rooms.get(code.upper())
        if not room:
            raise GameError('Room not found. Check the six character code.')
        return room

    def join(self, code, name, team=None, station=False, token=None):
        room = self.room(code)
        if token and token in room['players']:
            room['players'][token]['connected'] = True
            return token, room['players'][token]
        if len(room['players']) >= 80:
            raise GameError('Room full. Ask the facilitator for a station.')
        if team is None:
            counts = {tid: sum(p['team'] == tid for p in room['players'].values()) for tid in room['teams']}
            team = min(counts, key=counts.get)
        team = str(team)
        if team not in room['teams']:
            raise GameError('Unknown team.')
        token = secrets.token_urlsafe(24)
        player = {'id': secrets.token_hex(5), 'name': nickname(name), 'team': team, 'station': station,
                  'connected': True, 'hidden': False, 'last_seen': time.time()}
        room['players'][token] = player
        self.save(room)
        return token, player

    def spawn(self, coro):
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    def run_agents(self, room, robots):
        if self.agents:
            for robot in robots:
                self.spawn(self.agents.bubble(room, robot, max(1, room['wave']), room['generation']))

    async def greet(self, room):
        generation = room['generation']
        for robot in ORDER:
            if room['generation'] != generation or room['phase'] != 'briefing':
                break
            await self.agents.bubble(room, robot, 1, generation)
            await asyncio.sleep(1.8 * settings.SCALE)

    def start_wave(self, room, wave):
        if wave != room.get('checkpoint_wave'):
            room['wave_checkpoint'] = copy.deepcopy(room['teams'])
            room['checkpoint_wave'] = wave
        room.update(phase='wave', wave=wave, remaining=WAVES[wave]['duration'], wave_elapsed=0,
                    bubbles={}, autopilot_next={}, generation=room['generation'] + 1,
                    notice='ALERT ALERT · ' + WAVES[wave]['name'])
        for team in room['teams'].values():
            team.update(progress=[], completed=False, wave_score=0, last_action='', isolated=False, buildings=['alert'] * 6)
        if room.get('personal') and room.get('guided'):
            room['story'] = new_story(wave)
            for team in room['teams'].values():
                team['risk'] += 6000 * wave
                team['trust'] = max(55, team['trust'] - 3)
                if wave == 3:
                    team['buildings'] = ['frozen'] * 6
        else:
            self.run_agents(room, ['SHERLOCK'] if wave == 1 else ['SCOUT'] if wave == 2 else ORDER)
        self.save(room)

    def advance(self, room):
        if room['phase'] == 'lobby':
            room.update(phase='briefing', remaining=60, wave=0, notice='Meet your local AI squad. You make the decisions.')
            if self.agents:
                self.spawn(self.greet(room))
        elif room['phase'] == 'briefing':
            self.start_wave(room, 1)
        elif room['phase'] == 'wave':
            self.contain(room)
        elif room['phase'] == 'translate':
            if room['wave'] < 3:
                self.start_wave(room, room['wave'] + 1)
            else:
                room.update(phase='debrief', remaining=0, notice='Business restored. Bring the value story to your next customer.')
                self.run_agents(room, ['SCRIBE'])
        self.save(room)

    def contain(self, room, defer=False):
        for team in room['teams'].values():
            # Everyone gets a recovery path. Better choices keep more trust and revenue.
            team['times'].setdefault(str(room['wave']), round(room['wave_elapsed'], 1))
            team['buildings'] = ['restored'] * 6
        # Keep the twelve-minute show budget even when a team finishes early.
        # The saved time becomes discussion time; the facilitator can advance it.
        room.update(phase='translate', remaining=20 + room['remaining'], notice='Contained · Translate it into customer value.')
        room['history'].append({'wave': room['wave'], 'seconds': round(room['wave_elapsed'], 1)})
        self.save(room, defer=defer)

    def action(self, room, team_id, action, building=None):
        if room.get('guided'):
            raise GameError('Deploy the squad and watch the guided response. Your agents handle the demo actions.')
        if room['phase'] != 'wave' or room['paused']:
            raise GameError('Wait for the next live wave.')
        team = room['teams'][team_id]
        if team['completed']:
            raise GameError('Your team contained this wave. Help tell the value story.')
        wave = room['wave']
        progress = team['progress']
        correct = False
        robot = None
        if wave == 1:
            if action not in {'analyze', 'verify', 'pay'}:
                raise GameError('Choose one of the invoice action cards.')
            if action in progress:
                raise GameError('Your team already played this card.')
            progress.append(action)
            if action == 'pay':
                team['risk'] += 48000
                team['trust'] = max(55, team['trust'] - 8)
                team['last_action'] = 'Payment lost. You can still check and verify.'
            elif action == 'analyze':
                correct = True
                robot = 'SHERLOCK'
                team['last_action'] = 'AI check complete. Call the vendor on a trusted number.'
            elif action == 'verify':
                correct = True
                team['last_action'] = 'Human verification complete.'
            team['completed'] = 'analyze' in progress and 'verify' in progress
        elif wave == 2:
            if action != 'SCOUT' or type(building) is not int or building not in range(6):
                raise GameError('Send SCOUT to a building numbered 1 to 6.')
            if building in progress:
                raise GameError('This building is already checked.')
            progress.append(building)
            correct = True
            robot = 'SCOUT'
            team['buildings'][building] = 'restored'
            team['last_action'] = 'Two fake emails quarantined. Check the next building.'
            team['completed'] = len(progress) == 6
        else:
            if action not in ORDER or type(building) is not int or building not in range(6):
                raise GameError('Choose a robot and a building.')
            expected = ORDER[len(progress)]
            if action != expected:
                team['last_action'] = 'Try ' + expected + ' next. Follow spot, explain, isolate, restore, communicate.'
                self.save(room)
                return
            progress.append(action)
            correct = True
            robot = action
            team['buildings'][building] = 'working' if action != 'PATCH' else 'restored'
            if action == 'SHIELD':
                team['isolated'] = True
            if action == 'PATCH':
                team['buildings'] = ['restored'] * 6
            team['last_action'] = action + ' deployed. Your security team stays in charge.'
            team['completed'] = len(progress) == 5
        if correct:
            team['score'] += 100
            team['wave_score'] += 100
            if room['wave_elapsed'] <= 10:
                team['score'] += 25
                team['fast'] += 1
                team['last_action'] += ' ★ Fast Response +25'
            if robot:
                team['robot_uses'][robot] += 1
                # Shared evidence analysis is intentionally deduplicated across teams.
                # One actual live run per role/wave serves the room; choices remain per team.
                if robot not in room['bubbles']:
                    self.run_agents(room, [robot])
        if team['completed']:
            team['times'][str(wave)] = round(room['wave_elapsed'], 1)
            team['buildings'] = ['restored'] * 6
            team['trust'] = min(100, team['trust'] + 4)
            team['last_action'] = '✓ Wave contained. ' + team['last_action']
        self.save(room)
        if all(t['completed'] for t in room['teams'].values()):
            self.contain(room)

    def control(self, room, command, value=None):
        if command in {'start', 'next', 'skip'}:
            if command != 'start' or room['phase'] == 'lobby':
                self.advance(room)
        elif command == 'pause':
            room['paused'] = not room['paused']
        elif command == 'autopilot':
            if not isinstance(value, dict) or str(value.get('team')) not in room['teams'] or type(value.get('enabled')) is not bool:
                raise GameError('Choose a team and autopilot setting.')
            room['teams'][str(value['team'])]['autopilot'] = value['enabled']
        elif command == 'autopilot_all':
            if type(value) is not bool:
                raise GameError('Choose on or off.')
            for team in room['teams'].values():
                team['autopilot'] = value
        elif command == 'hide':
            if not isinstance(value, str):
                raise GameError('Choose a player.')
            for player in room['players'].values():
                if player['id'] == value:
                    player['hidden'] = True
        elif command == 'intensity' and value in {'reduced', 'standard'}:
            room['intensity'] = value
        elif command == 'sound' and type(value) is bool:
            room['sound'] = value
        elif command == 'industry':
            if room['phase'] != 'lobby' or value not in INDUSTRIES:
                raise GameError('Choose an industry before starting.')
            room['industry'] = value
        elif command == 'replay':
            if room['wave'] not in WAVES:
                raise GameError('Start a wave first.')
            # Restore beginning-of-wave team counters rather than farming replay points.
            prior = room.get('wave_checkpoint')
            if prior:
                for tid, team in room['teams'].items():
                    auto = team['autopilot']
                    team.update(copy.deepcopy(prior[tid]))
                    team['autopilot'] = auto
            self.start_wave(room, room['wave'])
        elif command == 'reset':
            room['generation'] += 1
            for tid in room['teams']:
                room['teams'][tid] = self.new_team(int(tid))
            room.update(phase='lobby', wave=0, remaining=0, paused=False, bubbles={}, history=[],
                        notice='Ready for a new group.', wave_elapsed=0, autopilot_next={})
            room.pop('wave_checkpoint', None)
            room.pop('checkpoint_wave', None)
        else:
            raise GameError('Unknown control or invalid value.')
        self.save(room)

    def public(self, room, admin=False, player_token=None):
        teams = list(room['teams'].values())
        power = copy.deepcopy(room['power'])
        rates = power.pop('rates', [])
        recent = [(n, d) for t, n, d in rates if time.time() - t < 10]
        power['tps'] = round(sum(n for n, _ in recent) / max(.001, sum(d for _, d in recent)), 1)
        bubbles = copy.deepcopy(room['bubbles'])
        if not admin:
            for b in bubbles.values():
                b.pop('scripted', None)
        players = [{'id': p['id'], 'name': 'Seller' if p['hidden'] else p['name'], 'team': p['team'],
                    'connected': p['connected'], 'station': p['station']} for p in room['players'].values()]
        me = room['players'].get(player_token)
        return {'code': room['code'], 'industry': room['industry'], 'phase': room['phase'], 'wave': room['wave'],
                'personal': room.get('personal', False),
                'guided': room.get('guided', False), 'story': copy.deepcopy(room.get('story')),
                'human_reviews': copy.deepcopy(room.get('human_reviews', [])),
                'shared_power': self.agents.metrics() if room.get('personal') and self.agents else None,
                'account_card': room.get('card', {}) if room.get('personal') and (admin or player_token in room['players']) else {},
                'remaining': round(room['remaining'], 1), 'elapsed': round(room['wave_elapsed'], 1),
                'paused': room['paused'], 'intensity': room['intensity'], 'sound': room['sound'],
                'notice': room['notice'], 'teams': teams, 'players': players, 'bubbles': bubbles,
                'power': power, 'buildings': INDUSTRIES[room['industry']], 'wave_info': WAVES.get(room['wave']),
                'me': {'team': me['team'], 'name': me['name']} if me else None,
                'rehearsal': settings.SCALE != 1, 'server_time': time.time(),
                'fallback_count': len([r for r in self.agents.fallbacks if r['room'] == room['code']]) if admin and self.agents else None}

    async def emit(self, room, event='state'):
        if event == 'bubble':
            now = time.monotonic()
            if now - getattr(self, '_last_bubble_emit', 0) < .05:
                return
            self._last_bubble_emit = now
        for peer in list(self.peers.get(room['code'], [])):
            packet = {'type': event, 'state': self.public(room, peer['admin'], peer['token'])}
            q = peer['queue']
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            q.put_nowait(packet)

    async def tick(self):
        while True:
            now = time.time()
            for index, room in enumerate(list(self.rooms.values())):
                if index and index % 6 == 0:
                    await asyncio.sleep(0)
                elapsed = max(0, min(1, now - room['last_tick'])) / settings.SCALE
                room['last_tick'] = now
                if room.get('guided') and room['phase'] == 'wave':
                    story = room['story']
                    if step_cloud_check(room, elapsed):
                        self.save(room, defer=True)
                    if story['running'] and not room['paused']:
                        story['elapsed'] += elapsed
                        room['wave_elapsed'] += elapsed
                        room['remaining'] = max(0, room['remaining'] - elapsed)
                        for team in room['teams'].values():
                            unrestored = sum(s != 'restored' for s in team['buildings']) / 6
                            team['risk'] += elapsed * 200 * unrestored
                            team['trust'] = max(55, team['trust'] - elapsed * .018 * unrestored)
                            if room['wave'] > 1 and not team['isolated']:
                                team['records'] = min(250, team['records'] + elapsed * .3 * unrestored)
                        self.step_guided(room, defer=True)
                        self.save(room, defer=True)
                    await self.emit(room)
                    continue
                timed_phase = room['phase'] not in {'lobby', 'debrief'} and (not room.get('personal') or room['phase'] == 'wave')
                if not room['paused'] and timed_phase:
                    room['remaining'] = max(0, room['remaining'] - elapsed)
                    if room['phase'] == 'wave':
                        room['wave_elapsed'] += elapsed
                        for team in room['teams'].values():
                            if team['completed']:
                                continue
                            unrestored = sum(s != 'restored' for s in team['buildings']) / 6
                            team['risk'] += elapsed * 200 * unrestored
                            team['trust'] = max(55, team['trust'] - elapsed * .018 * unrestored)
                            if room['wave'] > 1 and not team.get('isolated'):
                                team['records'] = min(250, team['records'] + elapsed * .3 * unrestored)
                            # Freeze additional buildings during the boss, with labelled state.
                            if room['wave'] == 3:
                                for i in range(min(6, 1 + int(room['wave_elapsed'] / 25))):
                                    if team['buildings'][i] == 'alert':
                                        team['buildings'][i] = 'frozen'
                            if team['autopilot']:
                                due = room['autopilot_next'].get(team['id'], 0)
                                if room['wave_elapsed'] >= due:
                                    # Intentional human-sized pacing: show mechanics and allow other teams to participate.
                                    room['autopilot_next'][team['id']] = room['wave_elapsed'] + (22 if room['wave'] != 2 else 18)
                                    try:
                                        if room['wave'] == 1:
                                            action = 'analyze' if 'analyze' not in team['progress'] else 'verify'
                                            self.action(room, team['id'], action)
                                        elif room['wave'] == 2:
                                            building = next(i for i in range(6) if i not in team['progress'])
                                            self.action(room, team['id'], 'SCOUT', building)
                                        else:
                                            self.action(room, team['id'], ORDER[len(team['progress'])], len(team['progress']) % 6)
                                    except (GameError, StopIteration):
                                        pass
                        if room['phase'] == 'translate':
                            room['autopilot_next'] = {}
                    if room['remaining'] <= 0:
                        self.advance(room)
                    self.save(room)
                await self.emit(room)
            self.flush_pending()
            await asyncio.sleep(.25)

    async def close(self):
        for task in list(self.tasks):
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        for room in self.rooms.values():
            self.save(room)
        self.db.close()
