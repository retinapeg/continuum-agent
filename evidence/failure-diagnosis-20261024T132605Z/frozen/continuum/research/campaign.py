from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import random
import sqlite3
import statistics
import threading
import time
from continuum.runtime.common import ROOT,SimClock,canonical,digest,utc,FileLock
from continuum.runtime.engine import Runtime
from continuum.runtime.providers import CLIProvider,FixtureProvider,ProviderError
from .worlds import FAMILIES,generate,schedule
from .scoring import score


def source_manifest():
    paths=sorted((ROOT/'continuum/runtime').rglob('*.py'))+sorted((ROOT/'continuum/research').glob('*.py'))
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def freeze(directory, *, live=False, pilot=False, model='claude-haiku-4-5-20251001', call_budget=6):
    directory.mkdir(parents=True,exist_ok=True)
    if (directory/'protocol.json').exists():raise ValueError('protocol already frozen; use resume')
    seeds=[101] if pilot else ([1001,1002,1003] if live else list(range(30)))
    repetitions=1 if pilot or not live else 2
    conditions=list('ABCDE') if live else list('ABCDE')+['D_no_memory']
    budgets=[call_budget] if live else [2,4,8]
    units=[]
    for seed in seeds:
        for family in FAMILIES:
            for rep in range(repetitions):
                for budget in budgets:
                    # Rotate/interleave policy order; E schedule is a priori public-prefix D schedule.
                    order=conditions.copy();random.Random(seed+rep+budget).shuffle(order)
                    for condition in order:
                        units.append({'id':f'{family}-{seed}-r{rep}-{condition}-b{budget}',
                                      'family':family,'seed':seed,'repetition':rep,'condition':condition,'budget':budget})
    protocol={'version':'continuum.protocol.v2.1','created_at':utc(),'live':live,'split':'pilot' if pilot else 'held-out' if live else 'offline-development',
              'provider':'claude' if live else 'fixture','requested_model':model if live else 'rules-v2',
              'conditions':conditions,'seeds':seeds,'repetitions':repetitions,'budgets':budgets,'units':units,
              'source_manifest':source_manifest(),'world_hashes':{f'{f}-{s}':digest(generate(f,s).to_dict()) for s in seeds for f in FAMILIES},
              'limits':{'provider_calls':2000,'concurrency':2 if live else 1,'output_tokens':3000,'output_bytes':1000000,'deadline_seconds':90,'campaign_seconds':7200,'retries':0},
              'scoring':'opportunity temporal matching v1; all attempted units included; structured Status/Risk claims only',
              'environment':{'python':__import__('sys').version,'jsonschema':__import__('importlib.metadata',fromlist=['version']).version('jsonschema'),
                  'cli_version':__import__('subprocess').check_output(['claude','--version'],text=True).strip() if live else None},
              'context_budget':18000,'schedule':'public-prefix schedule v1, E identical to D; memory ablation separate',
              'bootstrap':{'cluster':'family-seed scenario, repetitions averaged first','draws':2000,'seed':719}}
    (directory/'protocol.json').write_text(json.dumps(protocol,indent=2,sort_keys=True)+'\n')
    (directory/'protocol.sha256').write_text(hashlib.sha256((directory/'protocol.json').read_bytes()).hexdigest()+'\n')
    import tarfile
    with tarfile.open(directory/'frozen-source.tar.gz','w:gz') as archive:
        for source in protocol['source_manifest']:
            archive.add(ROOT/source,arcname=source)
    return protocol


class Budget:
    def __init__(self,directory,maximum):
        self.path=directory/'campaign.sqlite';self.maximum=maximum;self.lock=threading.Lock()
        with self.connect() as db:
            db.executescript('CREATE TABLE IF NOT EXISTS calls(id INTEGER PRIMARY KEY, unit TEXT, started TEXT); CREATE TABLE IF NOT EXISTS units(id TEXT PRIMARY KEY,status TEXT NOT NULL,result TEXT,error TEXT);')
    def connect(self):return sqlite3.connect(self.path,timeout=10)
    def take(self,unit):
        with self.lock,self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute('SELECT COUNT(*) FROM calls').fetchone()[0]>=self.maximum:raise ProviderError('campaign call ceiling reached',known_unsent=True)
            db.execute('INSERT INTO calls(unit,started) VALUES (?,?)',(unit,utc()))


class LimitedProvider:
    def __init__(self,inner,budget,unit):self.inner,self.budget,self.unit=inner,budget,unit;self.name,self.model=inner.name,inner.model
    def propose(self,*args):self.budget.take(self.unit);return self.inner.propose(*args)


def execute(directory,protocol,unit,budget):
    work=directory/'units'/unit['id'];work.mkdir(parents=True,exist_ok=True)
    world=generate(unit['family'],unit['seed'])
    fixtures=work/'public-documents';fixtures.mkdir(exist_ok=True)
    provider=CLIProvider(protocol['provider'],protocol['requested_model'],work/'provider-work') if protocol['live'] else FixtureProvider()
    if protocol['live']:provider=LimitedProvider(provider,budget,unit['id'])
    condition=unit['condition'];policy=condition[0]
    clock=SimClock(0)
    runtime=Runtime(work/'agent',provider,clock=clock,fixtures=fixtures,policy=policy,
                    memory_enabled=condition!='D_no_memory',schedule=schedule(world,policy),context_budget=protocol['context_budget'])
    started=time.monotonic()
    try:
        if not runtime.db.rows('SELECT * FROM goals'):
            runtime.goal(world.goal,world.deadline,goal_id='goal')
        first=runtime.db.get('evaluation_step',0)
        recovered_unknown=bool(runtime.db.rows("SELECT id FROM calls WHERE status='outcome-unknown'"))
        for index,at in enumerate(range(0,world.horizon+1,6)):
            if recovered_unknown:break
            if index<first:continue
            clock.advance(at)
            for event in [e for e in world.events if e['at']==at]:
                data=event['data'];kind=event['kind']
                # World facts are copied into an observation only when their public time arrives.
                if kind=='document.available':
                    (fixtures/data['path']).write_text(data['content'])
                    runtime.observe(kind,{'path':data['path']},event['source'],event['id'])
                elif kind in ('fact','correction'):
                    runtime.observe('fact.corrected',data,event['source'],event['id'])
                    if not runtime.db.rows('SELECT id FROM memories WHERE provenance=?',(canonical([event['id']]),)):
                        previous=runtime.db.rows("SELECT id FROM memories WHERE subject=? AND status IN ('confirmed','conflicted') ORDER BY observed DESC",(data['subject'],))
                        runtime.memory.add(data['kind'],data['subject'],data['content'],at,[event['id']],confirmed=True,
                                           supersedes=previous[0]['id'] if kind=='correction' and previous else None)
                elif kind=='pause':runtime.control('paused')
                elif kind=='resume':runtime.control('running')
                elif kind=='confirmation':runtime.cancel_goal('goal');runtime.observe('confirmation',data,event['source'],event['id'])
                else:runtime.observe(kind,data,event['source'],event['id'])
            calls=runtime.db.rows('SELECT id FROM calls')
            if len(calls)<unit['budget']:runtime.tick()
            runtime.db.set('evaluation_step',index+1)
            if world.family=='interrupted_work' and at==24:
                runtime.close()
                runtime=Runtime(work/'agent',provider,clock=clock,fixtures=fixtures,policy=policy,memory_enabled=condition!='D_no_memory',schedule=schedule(world,policy))
            if runtime.db.get('control')=='paused' and runtime.db.rows("SELECT id FROM calls WHERE status='outcome-unknown'"):
                break
        operations=runtime.db.rows('SELECT * FROM operations ORDER BY created,id')
        calls=runtime.db.rows('SELECT * FROM calls ORDER BY created,id')
        for op in operations:op['args']=json.loads(op['args'])
        for call in calls:call['usage']=json.loads(call['usage']) if call['usage'] else None
        result={**unit,'scenario':world.id,'provider':protocol['provider'],'requested_model':protocol['requested_model'],
                'call_times':[c['created'] for c in calls], 'elapsed_seconds':time.monotonic()-started,**score(world,operations,calls,runtime.db.rows('SELECT * FROM memories'),runtime.db.rows('SELECT * FROM outbox'))}
        (work/'result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        # Compact review artifact contains public actions and deterministic verification, no hidden reasoning.
        (work/'review.json').write_text(json.dumps({'scenario':world.id,'operations':operations,'score':result},indent=2)+'\n')
        return result
    finally:runtime.close()


def run_campaign(directory,resume=False):
    with FileLock(directory/'campaign.lock'):
        return _run_campaign(directory,resume)

def _run_campaign(directory,resume=False):
    protocol=json.loads((directory/'protocol.json').read_text())
    if hashlib.sha256((directory/'protocol.json').read_bytes()).hexdigest()!=(directory/'protocol.sha256').read_text().strip():raise ValueError('protocol tampered')
    if protocol['source_manifest']!=source_manifest():raise ValueError('source changed since freeze; use a new versioned campaign')
    budget=Budget(directory,protocol['limits']['provider_calls']);started=time.monotonic()
    with budget.connect() as db:
        for unit in protocol['units']:db.execute("INSERT OR IGNORE INTO units VALUES (?,'queued',NULL,NULL)",(unit['id'],))
        completed={r[0] for r in db.execute("SELECT id FROM units WHERE status IN ('succeeded','failed')")}
    pending=[u for u in protocol['units'] if u['id'] not in completed]
    def worker(unit):
        if time.monotonic()-started>protocol['limits']['campaign_seconds']:return
        with budget.connect() as db:db.execute("UPDATE units SET status='running' WHERE id=?",(unit['id'],))
        try:
            result=execute(directory,protocol,unit,budget)
            with budget.connect() as db:db.execute("UPDATE units SET status='succeeded',result=? WHERE id=?",(canonical(result),unit['id']))
        except Exception as exc:
            result={**unit,'scenario':f"{unit['family']}-{unit['seed']}",'goal_completion':0,'valid_execution':0,'provider_failures':1,'episode_error':str(exc),'eligible_opportunities':len(generate(unit['family'],unit['seed']).opportunities),'true_positive':0,'false_negative':len(generate(unit['family'],unit['seed']).opportunities),'interventions':None,'false_positive':None}
            with budget.connect() as db:db.execute("UPDATE units SET status='failed',result=?,error=? WHERE id=?",(canonical(result),str(exc),unit['id']))
        return unit['id']
    # At most two owned model calls; no nested executor or detached workers.
    with ThreadPoolExecutor(max_workers=protocol['limits']['concurrency']) as pool:
        futures={pool.submit(worker,u):u for u in pending}
        for count,future in enumerate(as_completed(futures),1):
            name=future.result()
            if count%10==0 or count==len(pending):print(f'{count}/{len(pending)} completed: {name}',flush=True)
    return report(directory)


def report(directory):
    with sqlite3.connect(directory/'campaign.sqlite') as db:
        rows=[json.loads(r[0]) for r in db.execute('SELECT result FROM units WHERE result IS NOT NULL ORDER BY id')]
        statuses=dict(db.execute('SELECT status,COUNT(*) FROM units GROUP BY status'))
    (directory/'results.jsonl').write_text(''.join(canonical(row)+'\n' for row in rows))
    groups={}
    metrics=('goal_completion','intervention_precision','intervention_recall','appropriate_inaction','supported_fact_accuracy','stale_fact_uses',
             'contradiction_handled','appropriate_clarification','interruptions','latency','recovery_success','duplicate_effects','provider_calls','provider_failures','api_equivalent_usd')
    for condition in sorted({r['condition'] for r in rows}):
        for budget in sorted({r['budget'] for r in rows}):
            selected=[r for r in rows if r['condition']==condition and r['budget']==budget]
            groups[f'{condition}/budget-{budget}']={'episodes':len(selected),'valid_executions':sum(r.get('valid_execution',0) for r in selected)}
            for metric in metrics:
                values=[r.get(metric) for r in selected if r.get(metric) is not None]
                groups[f'{condition}/budget-{budget}'][metric]=statistics.mean(values) if values else None
                groups[f'{condition}/budget-{budget}'][metric+'_n']=len(values)
            group=groups[f'{condition}/budget-{budget}']
            total_tp=sum(r.get('true_positive',0) for r in selected);total_actions=sum(r.get('interventions') or 0 for r in selected);total_opportunities=sum(r.get('eligible_opportunities',0) for r in selected)
            group['pooled_intervention_precision']=total_tp/total_actions if total_actions and all(r.get('interventions') is not None for r in selected) else None
            group['pooled_intervention_recall']=total_tp/total_opportunities if total_opportunities else None
            known=[r['api_equivalent_usd'] for r in selected if r.get('api_equivalent_usd') is not None]
            group['known_api_estimate_usd_subtotal']=sum(known) if known else None
            group['total_api_equivalent_usd']=sum(known) if len(known)==len(selected) and selected else None
            completed=sum(r['goal_completion'] for r in selected)
            group['cost_per_verified_outcome_all_attempts']=group['total_api_equivalent_usd']/completed if group['total_api_equivalent_usd'] is not None and completed else None
            group['cost_unknown_reason']=None if len(known)==len(selected) else 'one or more attempted episodes lack complete cost telemetry; subtotal is not total cost'
            group['token_totals']={k:sum(r['tokens'][k] for r in selected) for k in ('uncached_input','cached_read','cache_creation','output')} if selected and all(r.get('tokens') is not None for r in selected) else None
            group['interruptions_per_simulated_hour']=30*sum(r.get('interruptions',0) for r in selected)/len(selected) if selected else None
            valid=[r['goal_completion'] for r in selected if r.get('valid_execution')]
            groups[f'{condition}/budget-{budget}']['conditional_valid_completion']=statistics.mean(valid) if valid else None
    intervals={}
    for budget in sorted({r['budget'] for r in rows}):
        for baseline in ('A','B','C','E'):
            diffs=[]
            for scenario in sorted({r['scenario'] for r in rows}):
                a={r['repetition']:r['goal_completion'] for r in rows if r['scenario']==scenario and r['condition']=='D' and r['budget']==budget}
                b={r['repetition']:r['goal_completion'] for r in rows if r['scenario']==scenario and r['condition']==baseline and r['budget']==budget}
                common=set(a)&set(b)
                if common:diffs.append(statistics.mean(a[k]-b[k] for k in common))
            if diffs:
                rng=random.Random(719);samples=sorted(statistics.mean(rng.choices(diffs,k=len(diffs))) for _ in range(2000))
                intervals[f'D-minus-{baseline}/budget-{budget}']={'scenarios':len(diffs),'mean':statistics.mean(diffs),'low':samples[49],'high':samples[1949]}
    family_results={}
    for family in sorted({r['family'] for r in rows}):
        family_results[family]={}
        for condition in sorted({r['condition'] for r in rows}):
            selected=[r for r in rows if r['family']==family and r['condition']==condition]
            family_results[family][condition]={'episodes':len(selected),'completion':statistics.mean(r['goal_completion'] for r in selected) if selected else None}
    result={'by_family':family_results,'attempted_episodes':len(rows),'statuses':statuses,'means':groups,'paired_scenario_bootstrap_95':intervals,
            'subscription_charge':None,'charge_reason':'not observed; CLI API-equivalent estimates are not invoices'}
    (directory/'report.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['freeze','run','resume','report']);p.add_argument('--directory',type=Path,required=True);p.add_argument('--live',action='store_true');p.add_argument('--pilot',action='store_true');p.add_argument('--model',default='claude-haiku-4-5-20251001');p.add_argument('--call-budget',type=int,default=6)
    a=p.parse_args();directory=a.directory.resolve()
    if not directory.is_relative_to(ROOT/'experiments/v02'):p.error('versioned experiment directory required')
    if a.command=='freeze':r=freeze(directory,live=a.live,pilot=a.pilot,model=a.model,call_budget=a.call_budget);print('Frozen',len(r['units']),'units')
    elif a.command=='report':print(json.dumps(report(directory),indent=2))
    else:print(json.dumps(run_campaign(directory,resume=a.command=='resume'),indent=2))

if __name__=='__main__':main()
