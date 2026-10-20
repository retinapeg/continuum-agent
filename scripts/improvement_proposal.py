"""Proposal-only configuration experiment on development scenarios; never mutates service."""
import difflib,json,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from continuum.runtime.common import ROOT,SimClock,canonical,digest,utc
from continuum.runtime.engine import Runtime
from continuum.runtime.providers import FixtureProvider
from continuum.research.worlds import generate
from continuum.research.scoring import score
out=ROOT/'experiments/v02/improvement-proposal-v1';out.mkdir(parents=True,exist_ok=True)
base={'reflection_seconds':30,'period_seconds':30,'policy':'D'}
candidate={**base,'reflection_seconds':60}
worlds=[generate(f,200+i) for i,f in enumerate(('delayed_dependencies','document_update','interrupted_work'))]
frozen={'created_at':utc(),'split':'development-improvement','scenario_hashes':{w.id:digest(w.to_dict()) for w in worlds},'baseline':base,'candidate':candidate,'protected':['permissions','scorer','original_evidence'],'promotion':'human approval with fresh evaluation required'}
manifest=out/'manifest.json'
if manifest.exists():raise SystemExit('proposal already evaluated; use its existing receipts')
manifest.write_text(json.dumps(frozen,indent=2)+'\n')
results={}
for label,config in [('baseline',base),('candidate',candidate)]:
 directory=out/label;directory.mkdir(exist_ok=True)
 (directory/'config.json').write_text(json.dumps(config,indent=2)+'\n')
 rows=[]
 for world in worlds:
  work=directory/world.id;docs=work/'public-docs';docs.mkdir(parents=True,exist_ok=True)
  clock=SimClock();r=Runtime(work/'agent',FixtureProvider(),clock=clock,fixtures=docs,reflection=config['reflection_seconds'])
  try:
   r.goal(world.goal,world.deadline,goal_id='goal')
   for at in range(0,121,6):
    clock.advance(at)
    for event in [e for e in world.events if e['at']==at]:
     if event['kind']=='document.available':
      (docs/event['data']['path']).write_text(event['data']['content']);r.observe('document.available',{'path':event['data']['path']},'fixture',event['id'])
     elif event['kind']=='pause':r.control('paused')
     elif event['kind']=='resume':r.control('running')
     else:r.observe(event['kind'],event['data'],'fixture',event['id'])
    r.tick()
   ops=r.db.rows('SELECT * FROM operations');calls=r.db.rows('SELECT * FROM calls')
   for op in ops:op['args']=json.loads(op['args'])
   for call in calls:call['usage']=json.loads(call['usage']) if call['usage'] else None
   rows.append({'scenario':world.id,**score(world,ops,calls,[],r.db.rows('SELECT * FROM outbox'))})
  finally:r.close()
 results[label]=rows
before=json.dumps(base,indent=2).splitlines(True);after=json.dumps(candidate,indent=2).splitlines(True)
(out/'proposed-config.diff').write_text(''.join(difflib.unified_diff(before,after,fromfile='baseline/config.json',tofile='candidate/config.json')))
report={'proposal_only':True,'applied_to_service':False,'rationale':'Reduce unnecessary reflections identified in scheduling friction; test cost without changing authority.',
        'baseline':results['baseline'],'candidate':results['candidate'],'promotion_status':'QUEUED_FOR_REVIEW',
        'held_out_exposure':False,'limitation':'Fixture-only three-scenario development check; no live improvement claim.'}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('Proposal evaluated, diff queued, service unchanged.')
