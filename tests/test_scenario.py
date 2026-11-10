import hashlib
import itertools
import json
import pytest
from scripts.generate_dataset import generate
from scenario.answer_key import KEY_IDS, DECOY_IDS, EVIDENCE, DECISIONS
from app.scoring import score

def test_dataset_deterministic_and_checked_in():
    a=json.dumps(generate(),indent=2)+'\n'
    assert hashlib.sha256(a.encode()).hexdigest()==hashlib.sha256((__import__('pathlib').Path('data/events.json')).read_bytes()).hexdigest()
    assert 5000<=len(generate())<=8000
    assert set(e['id'] for e in generate()) >= KEY_IDS | DECOY_IDS

def test_chain_is_joinable():
    logs={e['id']:e for e in generate()}
    assert logs['EML9001']['attachment']==logs['EDR9001']['attachment']
    assert logs['NET9001']['session_id']==logs['IDP9001']['session_id']==logs['FIL9002']['session_id']
    assert logs['FIL9003']['src_ip']==logs['FIL9002']['src_ip']
    assert logs['FIL9003']['src_ip']!=logs['FIL9005']['src_ip']

def test_entire_scoring_table():
    for decision in DECISIONS:
        for n in range(4):
            for evidence in itertools.combinations(EVIDENCE,n):
                result=score(decision,list(evidence))
                expected=0 if decision=='close' else DECISIONS[decision]+10*sum(EVIDENCE[x]['key'] for x in evidence)
                assert result['total']==expected
    with pytest.raises(ValueError): score('escalate',['twist']*2)
