"""Facilitator controlled clock. Wall clock deadlines survive a process restart."""
import secrets
import time
from datetime import datetime, timezone

DURATIONS = [120, 240, 360, 240, 240]
NAMES = ['Join the mission', 'Make your first call', 'Investigate with AI and decide', 'Reveal the customer and the compute', 'Turn the experience into an account action']

def new_session(label='LIVE'):
    return dict(id=secrets.token_hex(8), label=label, mode='individual', phase=1, join_code=secrets.token_hex(3).upper(),
                created=datetime.now(timezone.utc).isoformat(), deadline=time.time()+120,
                paused=True, started=False, remaining=120, twist=False, locked=False, reveal=0,
                replay=False, leaderboard=False, overdrive='idle', sound=False, open=True)

def remaining(session, now=None):
    return max(0, session['remaining'] if session['paused'] else session['deadline']-(now or time.time()))

def control(session, action):
    now=time.time()
    if action=='start':
        if not session.get('started'):
            if session['phase']!=1:raise ValueError('Start the workshop from the lobby')
            session.update(started=True,paused=False,remaining=DURATIONS[0],deadline=now+DURATIONS[0])
    elif action in ('next','previous'):
        session['phase']=min(5,max(1,session['phase']+(1 if action=='next' else -1)))
        session['remaining']=DURATIONS[session['phase']-1]
        session['deadline']=now+session['remaining']
        session.update(started=True,paused=False,open=session['phase']==1)
    elif action=='pause':
        session['remaining']=remaining(session,now)
        session['paused']=not session['paused']
        session['deadline']=now+session['remaining']
    elif action=='extend':
        session['remaining']=remaining(session,now)+60
        session['deadline']=now+session['remaining']
    elif action=='twist':
        session['twist']=True
        session.setdefault('twist_at',now)
    elif action=='lock':
        session['locked']=True
    elif action=='reveal':
        session['reveal']=min(7,session['reveal']+1)
    elif action in ('replay','leaderboard','sound'):
        session[action]=not session[action]
    elif action=='open':
        session['open']=True
    else:
        raise ValueError('Unknown control')
    return session
