from scenario.answer_key import DECISIONS, EVIDENCE

def score(decision, evidence):
    if decision not in DECISIONS or len(evidence)>3 or len(set(evidence))!=len(evidence) or any(x not in EVIDENCE for x in evidence):
        raise ValueError('Choose a valid decision and up to three different evidence cards')
    points=DECISIONS[decision]
    # Closing gets zero even when selected evidence happens to be relevant.
    evidence_points=sum(10 for x in evidence if EVIDENCE[x]['key']) if decision!='close' else 0
    return {'decision_points':points,'evidence_points':evidence_points,'total':points+evidence_points}
