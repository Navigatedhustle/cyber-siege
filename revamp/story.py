"""Guided fictional incident runbooks. Model analysis is live; city actions are a safe simulation."""
from .content import ROBOTS, evidence_for
import json

ORDER = list(ROBOTS)
STEP_SECONDS = [3, 7, 12, 18, 24]
CLOUD_CHECK_SECONDS = 4.8

CLOUD = {
    'actual_api_request': False, 'blocked_by': 'fictional_customer_policy',
    'title': 'Request denied by the scenario’s policy.',
    'label': 'Customer data policy · scripted illustration',
    'bubble': 'Request denied in this scenario. This external AI route is not approved for sensitive incident logs or automated remediation.',
    'reason': 'Northwind has not approved uploading this incident’s sensitive records to an external AI service.',
    'scope': 'No cloud model was called. This is a customer-policy example, not a measured model refusal.',
    'clarification': 'Frontier models can support authorized cybersecurity. Service safeguards may flag some requests, and providers offer enterprise data controls. This customer’s chosen policy still keeps this evidence local. Local AI also needs safeguards and authorized tools.',
}

VALUE = [
    {'title':'Bring AI to the evidence.', 'body':'Sensitive evidence stays on the approved local inference path. The team can work with the context it is allowed to use.', 'seller':'“Which information is your team unable to send to an external AI service?”'},
    {'title':'Turn clues into understanding.', 'body':'Specialized roles explain the evidence in plain language. People get a clearer next step, rather than another pile of logs.', 'seller':'“Where does slow analysis delay a business decision today?”'},
    {'title':'Plan capacity for critical work.', 'body':'Dedicated local compute lets you plan capacity for priority workflows. Evaluate it against cloud quotas and connectivity needs, with power, support and resilience included.', 'seller':'“Which critical AI workflow needs capacity your team can plan and operate?”'},
    {'title':'Give agents a defined action scope.', 'body':'In this demo the agents change only fictional city state. In a real deployment, tools, permissions, testing and approvals define what an agent may do.', 'seller':'“What could be automated safely, and what should always need approval?”'},
    {'title':'Own the workflow. Keep people in control.', 'body':'Bring evidence, an approved model and scoped tools together on local infrastructure. Your team still owns validation, security and recovery planning.', 'seller':'“Who owns this AI workflow, its capacity and the approval to act?”'},
]

INCIDENTS = {
    1: {
        'title':'An urgent payment. A hidden trap.', 'villain':'invoice',
        'attack':'A fake invoice asks finance to send $48,000 to changed bank details. Game value.',
        'evidence':'A fictional invoice, sender/reply addresses and a payment-change request.',
        'steps':[
            'Spotted urgency, changed bank details and a mismatched reply address in the fictional invoice.',
            'Explained the payment warning signs using the live local analysis.',
            'Placed the disputed payment route on hold in the simulation.',
            'Restored the normal finance workflow while keeping the disputed invoice held in the simulation.',
            'Queued a human vendor-verification task with the evidence and recommended next step.',
        ],
        'human':'Finance owner: call the vendor on a trusted number before releasing the disputed payment.',
        'translate':[
            'A fake urgent payment put $48,000 at risk. Game value.',
            'Local AI analyzed the invoice; the demo held the payment and queued human verification.',
            '“Local AI can help your people investigate sensitive requests without moving the analysis outside their chosen boundary.”',
        ],
    },
    2: {
        'title':'An inbox storm. Too much to sort.', 'villain':'phisher',
        'attack':'200 fictional emails include 12 credential-stealing messages across six business buildings.',
        'evidence':'200 fictional email records, including 12 known fakes in this training dataset.',
        'steps':[
            'Submitted 200 fictional emails to the local analysis and highlighted the dataset’s 12 known fakes.',
            'Explained the suspicious login demands and sender patterns.',
            'Quarantined the known fake messages across the six simulated buildings.',
            'Reopened the simulated inbox workflows and prepared a credential-review recommendation.',
            'Queued an identity-team review rather than silently changing real user accounts.',
        ],
        'human':'Identity team: review affected accounts and approve any credential reset through the normal process.',
        'translate':[
            'A noisy inbox put business access and customer trust under pressure.',
            'The local squad analyzed fictional mail, demonstrated quarantine and queued identity review.',
            '“A shared local AI platform can help teams sort sensitive evidence and focus human attention where it matters.”',
        ],
    },
    3: {
        'title':'Frozen systems. A recovery race.', 'villain':'lockjaw',
        'attack':'Unexpected encryption freezes the fictional business. LEAKY is trying to take records out.',
        'evidence':'Fictional file activity, unusual login events and a verified-backup recovery option.',
        'steps':[
            'Spotted unexpected encryption and suspicious login activity in the fictional logs.',
            'Correlated the clues and explained the likely impact in plain language.',
            'Isolated the affected simulated systems, stopping further fictional records exposure.',
            'Applied the verified-backup recovery plan to the fictional city. No production system was patched.',
            'Queued the incident summary and a production patch/restore approval task for a human owner.',
        ],
        'human':'Security and service owners: validate the findings and approve any production patch or restore before execution.',
        'translate':[
            'Frozen systems put uptime and trust at risk. All monetary figures are game values.',
            'Five local roles investigated the evidence, demonstrated isolation/recovery and prepared a human handoff.',
            '“Fury can host local AI agents close to your sensitive workloads, with the permissions and approvals your team defines.”',
        ],
    },
}


def new_story(wave):
    info=INCIDENTS[wave]
    evidence=evidence_for(wave)
    preview=evidence[:2]+evidence[-1:] if len(evidence)>2 else evidence
    return {'stage':'cloud_check','cloud_elapsed':0.,'cloud_check_seconds':CLOUD_CHECK_SECONDS,
            'log_preview':[json.dumps(x,ensure_ascii=False) for x in preview],
            'running':False,'elapsed':0.,'cursor':0,'events':[],
            'title':info['title'],'attack':info['attack'],'evidence':info['evidence'],
            'cloud':dict(CLOUD),'value':dict(VALUE[0]),'translate':info['translate'],
            'simulation_only':True,'actual_model_endpoint':'local','human_review':None,
            'analysis_interrupted':False}


def step_cloud_check(room, elapsed):
    """Presentation preflight only: never sends logs to or calls a cloud model."""
    story=room['story']
    if room['paused'] or story['stage']!='cloud_check':
        return False
    story['cloud_elapsed']=min(CLOUD_CHECK_SECONDS,story['cloud_elapsed']+elapsed)
    if story['cloud_elapsed']>=CLOUD_CHECK_SECONDS:
        story['stage']='blocked'
    return True


def apply_step(room):
    story=room['story'];i=story['cursor'];role=ORDER[i];team=room['teams']['1']
    info=INCIDENTS[room['wave']]
    if role in team['progress']:
        return
    team['progress'].append(role);team['robot_uses'][role]+=1;team['score']+=100
    story['events'].append({'role':role,'title':info['steps'][i],'at_s':round(story['elapsed'],2),
                            'source':'fictional_runbook','scope':'simulation_only'})
    story['value']=dict(VALUE[i])
    if role=='SHIELD':
        team['isolated']=True;team['buildings']=['working']*6
    elif role=='PATCH':
        team['buildings']=['restored']*6
    elif role=='SCRIBE':
        task={'wave':room['wave'],'owner':'Customer security/business team','text':info['human'],
              'status':'human_review_required','delivery':'in_app_demo_queue'}
        story['human_review']=task
        room.setdefault('human_reviews',[]).append(task)
        team['completed']=True;team['trust']=min(100,team['trust']+4)
        team['times'][str(room['wave'])]=round(room['wave_elapsed'],1)
    story['cursor']+=1
    story['stage']='handoff' if role=='SCRIBE' else role.lower()
    team['last_action']=info['steps'][i]
