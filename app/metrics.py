"""Per session measured token windows. Rehearsal and live samples never merge."""
import logging
import re
import time
from collections import defaultdict, deque

log=logging.getLogger(__name__)
COUNTERS=('vllm:generation_tokens_total','trtllm:output_tokens_total','infinity_generation_tokens_total')

def parse_counter(text):
    for name in COUNTERS:
        values=[]
        for line in text.splitlines():
            if re.match(re.escape(name)+r'(?:\{|\s)',line):
                try: values.append(float(line.split()[-1]))
                except ValueError: pass
        if values: return name,sum(values)
    return None,None

class TokenWindow:
    def __init__(self):
        self.events=deque()
        self.total=0
        self.peak=0.0
        self.peak_at=None

    def add(self,at,count):
        self.events.append((at,count)); self.total+=count

    def rates(self,now):
        while self.events and self.events[0][0]<=now-5: self.events.popleft()
        one=sum(n for t,n in self.events if t>now-1)
        five=sum(n for t,n in self.events)/5
        if five>self.peak: self.peak=five; self.peak_at=now
        return {'tps_1s':one,'tps_5s':five,'total_tokens':self.total,'peak_5s':self.peak,'peak_at':self.peak_at}

class Telemetry:
    def __init__(self,db):
        self.db=db
        self.windows=defaultdict(TokenWindow)
        self.latest={}
        self.server_previous={}
        self.server_baseline={}
        self.server_windows=defaultdict(TokenWindow)
        self.external=set()
        self.missing_usage=defaultdict(int)
        self.calls=defaultdict(int)
        self.sample_counter=0
        self.source_changed=set()

    def record(self,model,count,scope,raw):
        if not scope: return
        sid=scope['id']
        key=(sid,model)
        self.calls[key]+=1
        if count is None:
            self.missing_usage[key]+=1
            log.warning('Model %s omitted stream usage',model)
        else:
            self.windows[key].add(time.time(),count)
        self.db.event(sid,time.time(),{'type':'usage','model':model,'completion_tokens':count,'label':scope['label']})

    def restore(self,sid):
        if sid in self.latest: return
        for event in self.db.events(sid):
            if event.get('type')=='usage' and event.get('completion_tokens') is not None:
                key=(sid,event['model'])
                self.windows[key].add(event['at'],event['completion_tokens'])
        samples=self.db.samples(sid)
        if samples:
            self.latest[sid]=samples[-1]
            for key,value in samples[-1].get('models',{}).items():
                if value.get('other_traffic_or_divergence'):self.external.add((sid,key))

    async def sample(self,session,router,gpu):
        sid=session['id']; now=time.time(); per={}; aggregate=TokenWindow()
        for key,config in router.config.items():
            k=(sid,key); app=self.windows[k].rates(now)
            name=None; count=None
            if router.status[key]['healthy'] and config.get('metrics_source')!='app_usage':
                try:
                    response=await router.clients[key].http.get(config['metrics_url'],timeout=0.5)
                    if response.is_success: name,count=parse_counter(response.text)
                except Exception: pass
            if count is not None:
                previous=self.server_previous.get(k)
                if previous and count>=previous[1]: self.server_windows[k].add(now,count-previous[1])
                self.server_previous[k]=(now,count)
                self.server_baseline.setdefault(k,count)
            server=self.server_windows[k].rates(now)
            server_total=(count-self.server_baseline.get(k,count)) if count is not None else None
            app_total=app['total_tokens']
            # Compare completed usage after requests settle, avoiding a false external traffic alarm mid stream.
            mismatch=bool(server_total is not None and router.status[key]['active']==0 and max(app_total,server_total)>100 and abs(server_total-app_total)/max(app_total,server_total)>0.10)
            if mismatch:
                if k not in self.external:self.source_changed.add(sid)
                self.external.add(k)
                if k not in getattr(self,'warned',set()):
                    log.warning('Token counter divergence >10%% for %s; projector uses app usage',key)
                    self.warned=getattr(self,'warned',set())|{k}
            source='server counter' if name and k not in self.external else 'app streamed usage'
            chosen=server if source=='server counter' else app
            if source=='server counter' and app_total>0 and self.server_baseline[k]==count:
                chosen=app; source='app streamed usage'
            per[key]={**chosen,'source':source,'counter_name':name,'app':app,'server':server if name else None,
                      'other_traffic_or_divergence':k in self.external,'missing_usage_calls':self.missing_usage[k],
                      'healthy':router.status[key]['healthy'],'health_probe_failures':router.status[key].get('consecutive_probe_failures',0),'last_healthy_at':router.status[key].get('last_healthy_at'),'active_streams':router.status[key]['active'],'name':config['name'],'stack':config['serving_stack']}
        total={'tps_1s':sum(x['tps_1s'] for x in per.values()),'tps_5s':sum(x['tps_5s'] for x in per.values()),
               'total_tokens':sum(x['app']['total_tokens'] for x in per.values()),'active_streams':sum(x['active_streams'] for x in per.values())}
        old=self.latest.get(sid,{})
        prior_peak=old.get('peak_5s',0)
        prior_peak_at=old.get('peak_at')
        if sid in self.source_changed:
            # A counter later found to include other traffic must not retain a flattering peak.
            prior_peak=0;prior_peak_at=None
            for sample in self.db.samples(sid):
                corrected=0
                for model,value in sample.get('models',{}).items():
                    rate=value['app']['tps_5s'] if (sid,model) in self.external else value['tps_5s']
                    corrected+=rate
                if corrected>prior_peak:prior_peak=corrected;prior_peak_at=sample['timestamp']
            self.source_changed.discard(sid)
        peak=max(prior_peak,total['tps_5s'])
        value={'models':per,'total':total,'peak_5s':peak,'peak_at':now if total['tps_5s']>prior_peak else prior_peak_at,
               'gpu':gpu.sample(),'label':session['label'],'phase':session['phase'],'overdrive':session['overdrive']}
        self.latest[sid]=value
        self.db.sample(sid,now,value)
        return value
