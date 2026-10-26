"""Paid operations and durable experiment checkpoints; no assistant orchestration."""
from dataclasses import asdict
import copy
import hashlib
import json
import math
from pathlib import Path
import threading
from continuum.runtime.database import Database
from continuum.runtime.common import canonical, FileLock
from .world import World, WorldConfig, Change, scenario
from .estimator import Kalman
from .policies import Action, LABELS, PolicyInput, Scheduler
from .scoring import score


class PolicyRun:
    def __init__(self, name, config, observation_budget, inference_budget, parameters=None):
        self.name=name
        self.scheduler=Scheduler(name,**(parameters or {}))
        self.estimator=Kalman(config.omega,config.damping)
        self.budget={'observations':0,'observation_limit':observation_budget,'inferences':0,
                     'inference_limit':inference_budget,'actions':0,'action_limit':30}
        self.history=[]
        self.events=[]
        self.alerts=[]
        self.last_alert=-float('inf')
        self.failures=0
        self.metrics=None

    def receipt(self, tick, at, kind, status, detail, refs=()):
        receipt={'id':f'{self.name}:{tick}:{kind}','time':at,'kind':kind,'status':status,'detail':detail,'refs':list(refs)}
        self.events.append(receipt)
        if status not in ('succeeded','sleep'):
            self.failures+=1
        return receipt

    def step(self, world, tick, events, deadlines):
        config=world.config
        at=round(tick*config.dt,9)
        k=self.estimator
        k.propagate(at)
        forecast=k.forecast(1.)
        b=self.budget
        evidence=PolicyInput(at,config.horizon,config.dt,k.x,k.v,k.p,forecast[2],
                             k.last_observation,k.innovation,b['observation_limit']-b['observations'],
                             b['inference_limit']-b['inferences'],b['observation_limit'],tuple(events),tuple(deadlines),config.noise)
        proposed_actions=self.scheduler.decide(evidence)
        # One operation of each kind per simulation tick. Repeated requests are
        # idempotent before charging budgets or sampling the sensor, matching
        # the stable receipt identity used by restart recovery.
        actions=[]
        seen=set()
        duplicates=[]
        for action in proposed_actions:
            if not isinstance(action,Action) or action.kind not in ('wait','observe','think','predict','alert'):
                raise ValueError('unknown policy action')
            if action.kind in seen:
                duplicates.append(action.kind)
                continue
            seen.add(action.kind)
            actions.append(action)
        if duplicates:
            self.receipt(tick,at,'policy','succeeded',{'duplicates_ignored':duplicates})
        observation=None
        activity='sleep'
        for action in actions:
            if action.kind=='observe':
                if b['observations']>=b['observation_limit']:
                    self.receipt(tick,at,'observe','failed',{'error':'observation budget exhausted'})
                    continue
                b['observations']+=1
                observation=world.measure(tick)
                observation['status']='received'
                activity='observe'
                self.receipt(tick,at,'observe','succeeded',dict(observation))
            elif action.kind=='think':
                if b['inferences']>=b['inference_limit'] or observation is None:
                    self.receipt(tick,at,'think','failed',{'error':'inference budget exhausted or no new observation'})
                    continue
                b['inferences']+=1
                status=k.update(observation)
                observation['status']=status
                activity='think'
                self.receipt(tick,at,'think',status,{'method':'classical Kalman update','innovation':k.innovation,
                                                  'belief':k.public()},[f'{self.name}:{tick}:observe'])
                if status != 'stale-rejected' and k.innovation is not None and abs(k.innovation)>2.6 and at-self.last_alert>=10:
                    # Shared detector is independent of scheduling policy.
                    self.execute_alert(Action('alert','normalized innovation exceeds 2.6'),tick,at)
            elif action.kind=='wait':
                self.receipt(tick,at,'wait','sleep',{'reason':action.reason})
            elif action.kind=='alert':
                self.execute_alert(action,tick,at)
            elif action.kind!='predict':
                raise ValueError('unknown policy action')
        forecast=k.forecast(1.)
        self.history.append({'time':at,'x':k.x,'v':k.v,'std':math.sqrt(k.p),'target':round(at+1,9),
                             'prediction':forecast[0],'prediction_std':math.sqrt(forecast[2]),
                             'observation':observation,'activity':activity,'error':None})

    def execute_alert(self, action, tick, at):
        if any(event['id']==f'{self.name}:{tick}:alert' for event in self.events):
            return
        if self.budget['actions']>=self.budget['action_limit']:
            self.receipt(tick,at,'alert','failed',{'error':'action budget exhausted'})
            return
        self.budget['actions']+=1
        self.alerts.append(at)
        self.last_alert=at
        think_id=f'{self.name}:{tick}:think'
        refs=[think_id] if any(event['id']==think_id for event in self.events) else []
        self.receipt(tick,at,'alert','succeeded',{'reason':action.reason},refs)

    def finish(self, world):
        truth=world.truth()
        predictions=[row for row in self.history if row['target']<=world.config.horizon]
        resources={key:self.budget[key] for key in ('observations','inferences','actions')}
        self.metrics=score(truth,predictions,self.alerts,[c.time for c in world.config.changes],{**resources,'failures':self.failures})
        lookup={row['time']:row['x'] for row in truth}
        for row in self.history:
            if row['target'] in lookup:
                row['error']=row['prediction']-lookup[row['target']]

    def public(self):
        return {'id':self.name,'label':LABELS[self.name],'belief':self.estimator.public(),
                'budget':copy.deepcopy(self.budget),'history':copy.deepcopy(self.history),
                'events':copy.deepcopy(self.events),'metrics':self.metrics}

    def checkpoint(self):
        return {'name':self.name,'scheduler':{'next_at':self.scheduler.next_at,'state':self.scheduler.state.to_dict(),
                'period_scale':self.scheduler.period_scale,'threshold':self.scheduler.threshold},
                'estimator':vars(self.estimator),'budget':self.budget,'history':self.history,'events':self.events,
                'alerts':self.alerts,'last_alert':None if not math.isfinite(self.last_alert) else self.last_alert,
                'failures':self.failures,'metrics':self.metrics}

    def restore(self, data):
        from continuum.runtime.dynamics import State
        self.scheduler.next_at=data['scheduler']['next_at']
        self.scheduler.state=State(**data['scheduler']['state'])
        self.scheduler.period_scale=data['scheduler']['period_scale']
        self.scheduler.threshold=data['scheduler']['threshold']
        vars(self.estimator).update(data['estimator'])
        for key in ('budget','history','events','alerts','failures','metrics'):
            setattr(self,key,data[key])
        self.last_alert=-float('inf') if data['last_alert'] is None else data['last_alert']


class Experiment:
    def __init__(self, config=None, *, name='change', observation_budget=24, inference_budget=24,
                 database: Path | None=None, parameters=None):
        self.lock=threading.RLock()
        self.db=None
        self.owner=None
        self._closed=False
        try:
            if database:
                database=Path(database)
                self.owner=FileLock(database.with_suffix(database.suffix+'.lock'))
                self.db=Database(database,policy='laboratory')
            if self.db and self.db.get('lab_checkpoint'):
                data=self.db.get('lab_checkpoint')
                self._initialize(WorldConfig.from_dict(data['world_config']),data['config']['scenario'],
                                 data['config']['observation_budget'],data['config']['inference_budget'],data['parameters'])
                self._restore(data)
                # Restart never silently resumes automated work.
                if self.status=='running':
                    self.status='paused'
                    self._persist([])
            else:
                self._initialize(config or scenario(name),name,observation_budget,inference_budget,parameters or {})
                self._persist([])
        except BaseException:
            self.close()
            raise

    def _initialize(self, config, name, observations, inferences, parameters):
        if abs(1/config.dt-round(1/config.dt))>1e-8:
            raise ValueError('experiment dt must divide the one-second forecast horizon')
        if type(observations) is not int or type(inferences) is not int or not 0<=observations<=500 or not 0<=inferences<=500:
            raise ValueError('integer budgets must be 0..500')
        self.world=World(config)
        self.config={'scenario':name,'seed':config.seed,'horizon':config.horizon,'noise':config.noise,
                     'damping':config.damping,'observation_budget':observations,'inference_budget':inferences}
        self.parameters=parameters
        self.policies=[PolicyRun(p,config,observations,inferences,parameters.get(p)) for p in LABELS]
        self.tick=0
        self.status='paused'
        self.mode='deterministic'
        self.revealed=False
        self.speed=4
        self.public_events=[19.,49.,89.]
        self.deadlines=[config.horizon*f for f in (.25,.5,.75)]
        self.injections=[]
        self.run_id=hashlib.sha256(canonical({'world':config.to_dict(),'budgets':[observations,inferences],'parameters':parameters}).encode()).hexdigest()[:16]

    @property
    def time(self):
        return max(0,round((self.tick-1)*self.world.config.dt,9))

    def step(self, *, return_state=True):
        with self.lock:
            if self.status=='completed':return self.state() if return_state else None
            before=copy.deepcopy(self._checkpoint()) if self.db else None
            receipts=[]
            try:
                at=round(self.tick*self.world.config.dt,9)
                events=['public inspection event'] if at in self.public_events else []
                for run in self.policies:
                    start=len(run.events)
                    run.step(self.world,self.tick,events,self.deadlines)
                    receipts.extend(run.events[start:])
                self.tick+=1
                if at>=self.world.config.horizon:
                    self.status='completed'
                    for run in self.policies:run.finish(self.world)
                self._persist(receipts)
            except BaseException:
                if before:self._restore(before)
                raise
            return self.state() if return_state else None

    def run_all(self):
        while self.status!='completed':self.step(return_state=False)
        return self.state()

    def control(self, action, speed=4):
        with self.lock:
            if action not in ('pause','resume'):raise ValueError('invalid control')
            if type(speed) is not int or not 1<=speed<=16:raise ValueError('speed must be 1..16')
            before=copy.deepcopy(self._checkpoint())
            try:
                self.speed=speed
                if self.status!='completed':self.status='running' if action=='resume' else 'paused'
                self._persist([])
            except BaseException:
                self._restore(before)
                raise
            return self.state()

    def inject(self, kind, omega=1.4, damping=.03):
        with self.lock:
            if self.status=='completed':raise ValueError('start a new run to inject')
            at=round(max(1,self.tick)*self.world.config.dt,9)
            if at>=self.world.config.horizon:raise ValueError('no future simulation interval')
            before=copy.deepcopy(self._checkpoint())
            try:
                if kind=='event':
                    self.public_events=sorted(set(self.public_events+[at]))
                elif kind=='change':
                    c=self.world.config
                    changes=tuple(sorted([x for x in c.changes if x.time!=at]+[Change(at,float(omega),float(damping))],key=lambda x:x.time))
                    self.world=World(WorldConfig.from_dict({**c.to_dict(),'changes':[asdict(x) for x in changes]}))
                else:raise ValueError('invalid injection')
                self.injections.append({'time':at,'kind':kind,'omega':omega if kind=='change' else None,
                                        'damping':damping if kind=='change' else None})
                self._persist([])
            except BaseException:
                self._restore(before)
                raise
            return self.state()

    def reveal(self):
        with self.lock:
            if self.status!='completed':raise ValueError('truth is available only after the run')
            before=copy.deepcopy(self._checkpoint())
            try:
                self.revealed=True
                self._persist([])
            except BaseException:
                self._restore(before)
                raise
            return self.state()

    def _checkpoint(self):
        return {'world_config':self.world.config.to_dict(),'config':self.config,'parameters':self.parameters,
                'policies':[p.checkpoint() for p in self.policies],'tick':self.tick,'status':self.status,
                'mode':self.mode,'revealed':self.revealed,'speed':self.speed,'public_events':self.public_events,
                'deadlines':self.deadlines,'injections':self.injections,'run_id':self.run_id}

    def _restore(self,data):
        self.world=World(WorldConfig.from_dict(data['world_config']))
        for key in ('config','parameters','tick','status','mode','revealed','speed','public_events','deadlines','injections','run_id'):
            setattr(self,key,data[key])
        for run,saved in zip(self.policies,data['policies']):run.restore(saved)

    def _persist(self,receipts):
        if not self.db:return
        with self.db.transaction() as tx:
            for receipt in receipts:
                oid=self.run_id+':'+receipt['id']
                args=canonical(receipt['detail'])
                old=tx.execute('SELECT status,args FROM operations WHERE id=?',(oid,)).fetchone()
                if old:
                    if old['status']!=receipt['status'] or old['args']!=args:raise ValueError('conflicting duplicate operation')
                    continue
                tx.execute('INSERT INTO operations(id,trace_id,kind,args,status,result,attempt,permission_version,created) VALUES (?,?,?,?,?,?,1,0,?)',
                           (oid,self.run_id,receipt['kind'],args,receipt['status'],canonical(receipt),receipt['time']))
                self.db.event('lab.'+receipt['kind'],receipt,trace=self.run_id,status=receipt['status'],refs=receipt['refs'],tx=tx)
            self.db.set('lab_checkpoint',self._checkpoint(),tx)

    def state(self):
        with self.lock:
            return {'status':self.status,'mode':self.mode,'time':self.time,'horizon':self.world.config.horizon,
                    'dt':self.world.config.dt,'run_id':self.run_id,'config':dict(self.config),'revealed':self.revealed,
                    'truth':self.world.truth() if self.revealed and self.status=='completed' else [],
                    'policies':[p.public() for p in self.policies],
                    'injections':copy.deepcopy(self.injections),'world_fingerprint':self.world.fingerprint if self.status=='completed' else None,
                    'live':{'status':'not_run','message':'Explicit opt-in required; no Claude calls made by this dashboard.'}}

    def close(self):
        if self._closed:return
        self._closed=True
        try:
            if self.db:self.db.close()
        finally:
            if self.owner:self.owner.close()
