"""Guided plan boundary, ownership, AI readiness and safe simulation/human handoff invariants."""
import asyncio
import json
import pytest
from revamp.engine import Engine,GameError
from revamp.story import ORDER,STEP_SECONDS,INCIDENTS,CLOUD,CLOUD_CHECK_SECONDS,step_cloud_check

@pytest.fixture
def game(tmp_path):
    engine=Engine(tmp_path)
    yield engine
    engine.db.close()

def test_attack_policy_gate_before_deployment_and_idempotent_deploy(game):
    room,_=game.experience('guided-one-person-0001')
    calls=[];game.run_agents=lambda r,roles:calls.append(tuple(roles))
    game.experience_control(room,'start')
    assert room['phase']=='wave' and room['story']['stage']=='cloud_check'
    assert not room['story']['running'] and calls==[]
    assert room['story']['cloud']['actual_api_request'] is False
    assert room['story']['cloud']['blocked_by']=='fictional_customer_policy'
    assert room['teams']['1']['risk']>0
    with pytest.raises(GameError):game.action(room,'1','analyze')
    with pytest.raises(GameError):game.experience_control(room,'next')
    with pytest.raises(GameError):game.experience_control(room,'deploy')
    assert room['story']['log_preview'] and calls==[]
    step_cloud_check(room,CLOUD_CHECK_SECONDS)
    assert room['story']['stage']=='blocked'
    game.experience_control(room,'deploy');game.experience_control(room,'deploy')
    assert calls==[tuple(ORDER)] and room['story']['running']

def test_three_incidents_auto_roles_recovery_and_human_approval(game):
    room,_=game.experience('guided-one-person-0002');game.experience_control(room,'start')
    for wave in range(1,4):
        assert room['wave']==wave
        step_cloud_check(room,CLOUD_CHECK_SECONDS);game.experience_control(room,'deploy')
        for i,role in enumerate(ORDER):
            room['story']['elapsed']=STEP_SECONDS[i];room['wave_elapsed']=STEP_SECONDS[i]
            game.step_guided(room)
            assert room['teams']['1']['progress']==ORDER[:i+1]
            if role=='SHIELD':assert room['teams']['1']['isolated']
            if role=='PATCH':assert set(room['teams']['1']['buildings'])=={'restored'}
        assert room['phase']=='translate' and room['story']['cursor']==5
        assert room['story']['human_review']['status']=='human_review_required'
        assert all(e['scope']=='simulation_only' for e in room['story']['events'])
        assert room['story']['human_review']['delivery']=='in_app_demo_queue'
        game.experience_control(room,'next')
    assert room['phase']=='debrief'
    assert len(room['human_reviews'])==3 and room['teams']['1']['score']==1500
    assert 'approve' in room['human_reviews'][-1]['text'].lower()

def test_role_actions_wait_for_real_analysis_or_fallback(game):
    room,_=game.experience('guided-one-person-0003');game.experience_control(room,'start')
    step_cloud_check(room,CLOUD_CHECK_SECONDS);game.experience_control(room,'deploy')
    game.agents=object()
    room['story']['elapsed']=100
    room['bubbles']['SCOUT']={'status':'working'}
    game.step_guided(room);assert room['story']['cursor']==0
    room['bubbles']['SCOUT']={'status':'alert','scripted':True}
    game.step_guided(room);assert room['story']['cursor']==1
    room['bubbles']['SHERLOCK']={'status':'success'}
    game.step_guided(room);assert room['story']['cursor']==2
    game.agents=None

def test_pause_reset_and_restart_do_not_advance_someone_else(game):
    a,_=game.experience('guided-one-person-0004');b,_=game.experience('guided-one-person-0005')
    for r in [a,b]:game.experience_control(r,'start');step_cloud_check(r,CLOUD_CHECK_SECONDS);game.experience_control(r,'deploy')
    a['story']['elapsed']=100;game.experience_control(a,'pause');game.step_guided(a)
    assert a['story']['cursor']==0
    game.experience_control(a,'restart')
    assert a['phase']=='wave' and a['story']['stage']=='cloud_check' and a['teams']['1']['score']==0
    assert b['story']['running'] and b['phase']=='wave'
    game.experience_control(a,'reset');assert a['phase']=='lobby' and a.get('human_reviews')==[]

@pytest.mark.asyncio
async def test_paused_guided_scene_preserves_elapsed_and_persistence(game,tmp_path):
    r,_=game.experience('guided-one-person-0006');game.experience_control(r,'start');step_cloud_check(r,CLOUD_CHECK_SECONDS);game.experience_control(r,'deploy')
    game.experience_control(r,'pause');before=r['story']['elapsed']
    tick=asyncio.create_task(game.tick())
    try:
        await asyncio.sleep(.35)
        assert r['story']['elapsed']==before
        restored=Engine(tmp_path)
        try:
            rr=restored.room(r['code']);assert rr['paused']
            assert rr['story']['analysis_interrupted'] and rr['story']['running']
        finally:restored.db.close()
    finally:tick.cancel();await asyncio.gather(tick,return_exceptions=True)

def test_in_progress_legacy_save_is_retained_until_owner_restart(game):
    room,token=game.experience('guided-old-participant-01',guided=False)
    game.experience_control(room,'start');game.experience_control(room,'next')
    game.action(room,'1','analyze');score=room['teams']['1']['score']
    again,same=game.experience('guided-old-participant-01')
    assert same==token and not again['guided'] and again['teams']['1']['score']==score
    game.experience_control(again,'restart')
    assert again['guided'] and again['story']['stage']=='cloud_check'

def test_deferred_tick_cannot_overwrite_a_newer_owner_reset(game,tmp_path):
    room,_=game.experience('guided-tick-reset-consistency')
    game.experience_control(room,'start');step_cloud_check(room,CLOUD_CHECK_SECONDS);game.experience_control(room,'deploy')
    room['story']['elapsed']=STEP_SECONDS[0]
    game.step_guided(room,defer=True)
    game.experience_control(room,'reset')
    game.flush_pending()
    restored=Engine(tmp_path)
    try:
        saved=restored.room(room['code'])
        assert saved['phase']=='lobby' and saved['teams']['1']['score']==0
        assert not saved.get('story')
    finally:restored.db.close()

@pytest.mark.asyncio
async def test_cloud_preflight_pause_and_tick_do_not_run_local_models(game):
    room,_=game.experience('guided-cloud-preflight-001')
    calls=[];game.run_agents=lambda r,roles:calls.append(tuple(roles))
    game.experience_control(room,'start')
    game.experience_control(room,'pause')
    assert not step_cloud_check(room,100)
    assert room['story']['cloud_elapsed']==0
    game.experience_control(room,'pause')
    room['story']['cloud_elapsed']=CLOUD_CHECK_SECONDS-.01
    tick=asyncio.create_task(game.tick())
    try:
        await asyncio.sleep(.35)
        assert room['story']['stage']=='blocked' and calls==[]
        assert room['teams']['1']['score']==0 and room['story']['events']==[]
        assert room['story']['cloud']['actual_api_request'] is False
    finally:
        tick.cancel();await asyncio.gather(tick,return_exceptions=True)

def test_log_preview_is_from_supplied_fictional_evidence():
    from revamp.story import new_story
    from revamp.content import evidence_for
    for wave in [1,2,3]:
        preview=new_story(wave)['log_preview']
        assert preview and all(json.loads(line) in evidence_for(wave) for line in preview)
