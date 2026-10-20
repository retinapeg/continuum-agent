"""Separate bounded development routing comparison; never changes held-out routing."""
import json,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from continuum.runtime.common import ROOT,SimClock,utc,digest
from continuum.runtime.engine import Runtime
from continuum.runtime.providers import CLIProvider
from continuum.runtime.routing import RoutedProvider
from continuum.runtime.contracts import PROPOSAL,validate
from continuum.research.campaign import source_manifest
out=ROOT/'experiments/v02/routing-development-v1'
if out.exists():raise SystemExit('Existing evidence is immutable; do not rerun as replay.')
out.mkdir(parents=True)
config=json.loads((ROOT/'config/routing.example.json').read_text())
units=[{'id':f'{seed}-{condition}','seed':seed,'condition':condition} for seed in (301,302) for condition in ('fixed-haiku','router','fixed-sonnet')]
(out/'manifest.json').write_text(json.dumps({'split':'development-routing','created_at':utc(),'units':units,'source_manifest':source_manifest(),'config':config,'maximum_calls':6,'concurrency':1,'score':'validated proposal plus source-backed artifact containing exact Status and Risk fields; not overall prose quality','promotion':False},indent=2)+'\n')
results=[]
for unit in units:
 work=out/unit['id'];docs=work/'public-documents';docs.mkdir(parents=True)
 model='claude-sonnet-4-6' if unit['condition']=='fixed-sonnet' else 'claude-haiku-4-5-20251001'
 provider=RoutedProvider(config,work/'provider') if unit['condition']=='router' else CLIProvider('claude',model,work/'provider')
 r=Runtime(work/'agent',provider,fixtures=docs,clock=SimClock(100))
 try:
  r.goal('Create a concise Markdown readiness brief now using the available review, exact Status and Risk fields, source references and an evidence-limited recommendation.',goal_id='goal')
  text=f'# Fictional routing project {unit["seed"]}\nStatus: calibration ready\nRisk: field evidence missing\nLaboratory tests passed; field reliability remains unknown.\n'
  (docs/'review.md').write_text(text);r.observe('document.available',{'path':'review.md'},event_id='review')
  context=r.context(100);oid=r.capabilities.queue({'capability':'read_document','args':{'path':'review.md'}},'preload',100);r.capabilities.execute(oid,100,r.evidence(context))
  r.tick()
  calls=r.db.rows('SELECT * FROM calls');artifacts=r.db.rows('SELECT * FROM artifacts')
  bodies=[(work/'agent/artifacts'/a['path']).read_text() for a in artifacts]
  valid=bool(calls) and all(c['status']=='succeeded' for c in calls)
  success=valid and any('Status: calibration ready' in b.replace('**','') and 'Risk: field evidence missing' in b.replace('**','') for b in bodies)
  row={**unit,'valid':valid,'verified_artifact':success,'calls':calls,'routes':[json.loads(e['data'])['payload'] for e in r.db.rows("SELECT data FROM events WHERE kind='provider.progress'") if json.loads(e['data'])['payload'].get('type')=='routing.selected']}
  results.append(row);(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
  print(unit['id'],valid,success,flush=True)
 finally:r.close()
(out/'report.json').write_text(json.dumps({'development_only':True,'episodes':len(results),'results':{c:{'valid':sum(x['valid'] for x in results if x['condition']==c),'verified_artifacts':sum(x['verified_artifact'] for x in results if x['condition']==c),'episodes':2} for c in ('fixed-haiku','fixed-sonnet','router')},'conclusion':'Small operational check; no model-quality or router superiority inference.'},indent=2)+'\n')
