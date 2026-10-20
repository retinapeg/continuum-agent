"""Bounded real wall-clock initiative demo; fictional sources, subscription CLI only."""
import json,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from continuum.runtime.common import ROOT,utc
from continuum.runtime.engine import Runtime
from continuum.runtime.providers import CLIProvider
work=ROOT/'experiments/v02/live-runtime-demo-v1'
if work.exists():raise SystemExit('Use existing evidence; this demo never reruns completed calls.')
work.mkdir(parents=True);docs=work/'public-documents';docs.mkdir()
p=CLIProvider('claude','claude-haiku-4-5-20251001',work/'provider-work')
r=Runtime(work/'agent',p,fixtures=docs,reflection=60)
r.goal('Monitor the fictional Juniper project. When a review arrives, create a concise Markdown readiness brief with exact Status and Risk fields, source references and an evidence-limited recommendation. Notify me locally about the artifact. If the review leaves an owner decision unresolved, ask one necessary clarification. Do not claim field readiness from lab-only results.',goal_id='juniper')
r.observe('user.message',{'text':'Please monitor this fictional project and continue the authorised brief work when evidence arrives.'})
start=time.monotonic();thread=threading.Thread(target=r.serve,kwargs={'seconds':180});thread.start()
announced=False
try:
 while time.monotonic()-start<180 and thread.is_alive():
  elapsed=time.monotonic()-start
  if not announced and elapsed>=12:
   (docs/'review.md').write_text('# Juniper review\nStatus: calibration ready\nRisk: accessibility review pending\nThe laboratory calibration suite passed. Field performance has not been tested.\nAn owner must decide whether to schedule the accessibility review this week or next week.\n')
   announced=True
  calls=r.db.rows('SELECT status FROM calls')
  artifacts=r.db.rows('SELECT * FROM artifacts')
  messages=r.db.rows("SELECT * FROM outbox WHERE status='available-locally'")
  if artifacts and messages and all(c['status']!='running' for c in calls):break
  if len(calls)>=6 and all(c['status']!='running' for c in calls):break
  if r.db.get('control')=='paused':break
  time.sleep(.25)
finally:
 r.control('stopped');thread.join(5)
 receipt={'kind':'development-live-wall-clock-demo','utc':utc(),'elapsed_seconds':time.monotonic()-start,'provider':p.name,'requested_model':p.model,'thread_joined':not thread.is_alive(),'announced_without_second_user_message':announced,'status':r.status(),'limits':{'seconds':180,'calls':6,'output_bytes':p.max_bytes},'charges':None}
 (work/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');r.close()
print(json.dumps({'elapsed':receipt['elapsed_seconds'],'artifacts':len(receipt['status']['artifacts']),'calls':len(receipt['status']['calls']),'notifications':len(receipt['status']['notifications'])}))
