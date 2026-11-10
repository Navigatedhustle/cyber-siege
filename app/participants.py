"""A person's progress is independent of the room's presentation controls."""
import time
from .phases import DURATIONS,NAMES


def is_individual(person):
    return person.get('mode')=='individual'


def prepare(person):
    if is_individual(person):return
    phase=5 if person.get('card_id') else 4 if person.get('decision') else 3 if person.get('pick') else 2
    person['mode']='individual'
    person['progress']={'phase':phase,'twist':bool(person.get('decision')),'locked':False,'reveal':0,'overdrive':'idle','started':True,'self_paced':True,'paused':True,'remaining':DURATIONS[phase-1]}


def context(room,person):
    if not person or not is_individual(person):return dict(room)
    return {**room,**person['progress'],'participant_id':person['id'],'phase_name':NAMES[person['progress']['phase']-1]}


def advance(person,replay=False):
    progress=person['progress'];phase=progress['phase']
    if phase==2 and not person.get('pick'):raise ValueError('Choose your first alert')
    if phase==3:
        if not person.get('decision'):raise ValueError('Submit your decision first')
        if not replay and not person.get('reviews'):raise ValueError('Your independent reviews are still running')
    if phase==4 and progress['reveal']<6:raise ValueError('Continue through the reveal before creating your card')
    progress['phase']=min(5,phase+1)
    progress['remaining']=DURATIONS[progress['phase']-1]


def introduce_event(person):
    if person['progress']['phase']!=3 or person.get('investigation',{}).get('status')!='done':
        raise ValueError('Finish your investigation before opening the new event')
    person['progress']['twist']=True
    person['progress'].setdefault('twist_at',time.time())


def response_seconds(room,person):
    """Measure from this person's event release, rather than someone else's start."""
    scope=person.get('progress',{}) if is_individual(person) else room
    start=scope.get('twist_at',person['joined_at'])
    return max(0,person.get('decision_at',start)-start)
