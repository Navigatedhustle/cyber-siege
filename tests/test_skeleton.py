from app.db import Database
from app.phases import new_session, control, remaining

def test_session_survives_restart(tmp_path):
    db=Database(tmp_path/'test.db')
    session=new_session()
    db.put('session',session['id'],session)
    assert Database(tmp_path/'test.db').get('session',session['id'])==session

def test_clock_and_transitions():
    s=new_session()
    assert s['phase']==1
    control(s,'start')
    control(s,'pause')
    before=remaining(s)
    control(s,'extend')
    assert remaining(s)==before+60
    control(s,'pause')
    for _ in range(10): control(s,'next')
    assert s['phase']==5
    control(s,'previous')
    assert s['phase']==4

def test_import_has_no_database_side_effects(tmp_path):
    import os,subprocess,sys
    path=tmp_path/'must-not-exist.sqlite3'
    result=subprocess.run([sys.executable,'-c','import app.main'],env={**os.environ,'DATABASE_PATH':str(path)},capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert not path.exists()

def test_record_updates_preserve_team_order(tmp_path):
    db=Database(tmp_path/'order.db')
    db.put('team','first',{'id':'first','status':'idle'})
    db.put('team','second',{'id':'second','status':'idle'})
    db.put('team','first',{'id':'first','status':'done'})
    assert [row['id'] for row in db.all('team')]==['first','second']

def test_extending_expired_timer_gives_full_minute():
    import time
    s=new_session();control(s,'start');s['deadline']=time.time()-500
    control(s,'extend')
    assert 59<=remaining(s)<=60

def test_explicit_start_is_idempotent_and_phases_open_with_a_running_timer():
    s=new_session()
    assert s['paused'] and not s['started']
    assert remaining(s)==120
    control(s,'start');deadline=s['deadline']
    assert s['started'] and not s['paused'] and s['phase']==1
    control(s,'start')
    assert s['deadline']==deadline
    control(s,'pause');control(s,'next')
    assert s['phase']==2 and not s['paused'] and not s['open']
    assert 239<=remaining(s)<=240

async def test_restart_marks_inflight_work_interrupted(tmp_path):
    from app.main import create_app
    db=Database(tmp_path/'restart.db');session=new_session();session['overdrive']='running'
    db.put('session',session['id'],session);db.put('meta','active',{'id':session['id']})
    db.put('team','t',{'id':'t','session_id':session['id'],'investigation':{'status':'running'}})
    app=create_app(db)
    assert db.get('session',session['id'])['overdrive']=='interrupted'
    assert db.get('team','t')['investigation']['status']=='interrupted'
    await app.state.router.close()

def test_session_index_does_not_mix_rehearsals(tmp_path):
    db=Database(tmp_path/'sessions.db')
    db.put('team','old',{'session_id':'old','id':'old'})
    db.put('team','new',{'session_id':'new','id':'new'})
    assert [row['id'] for row in db.for_session('team','new')]==['new']
