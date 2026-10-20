"""A real elapsed-time soak with bounded local events and explicit shutdown."""
import argparse,json,sys,threading,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from continuum.runtime.common import ROOT,utc
from continuum.runtime.engine import Runtime
from continuum.runtime.providers import FixtureProvider
p=argparse.ArgumentParser();p.add_argument('--seconds',type=float,default=120);p.add_argument('--directory',type=Path,default=ROOT/'.runtime'/('soak-'+str(time.time_ns())));a=p.parse_args()
if not 30<=a.seconds<=7200:p.error('30–7200 seconds required')
if not a.directory.resolve().is_relative_to(ROOT):p.error('soak directory must stay inside repository')
if a.directory.exists():p.error('use a fresh directory to preserve earlier soak evidence')
fixtures=a.directory/'fixtures';fixtures.mkdir(parents=True,exist_ok=True)
r=Runtime(a.directory/'agent',FixtureProvider(),fixtures=fixtures,reflection=20)
r.goal('Monitor fictional project; create a source-backed readiness brief',goal_id='soak-goal')
start=time.monotonic();thread=threading.Thread(target=r.serve);thread.start();timeline=[]
try:
 for fraction,action in [(0.15,'new_document'),(.45,'pause'),(.6,'resume'),(.8,'status'),(1.0,'stop')]:
  remaining=start+a.seconds*fraction-time.monotonic()
  if remaining>0:threading.Event().wait(remaining)
  if action=='new_document':(fixtures/'review.md').write_text('# Fictional review\nStatus: calibration ready\nRisk: field evidence missing\nOnly laboratory evidence is available.')
  elif action=='pause':r.control('paused')
  elif action=='resume':r.control('running')
  elif action=='stop':r.control('stopped')
  timeline.append({'event':action,'elapsed':time.monotonic()-start,'control':r.db.get('control')})
 thread.join(5)
 status=r.status();assert not thread.is_alive();assert status['control']=='stopped'
 result={'utc':utc(),'requested_seconds':a.seconds,'actual_elapsed_seconds':time.monotonic()-start,
         'provider':'fixture','real_wall_clock':True,'inferences':len(status['calls']),
         'artifact_count':len(status['artifacts']),'interruptions':len([n for n in status['notifications'] if n['status']=='available-locally']),
         'control_timeline':timeline,'shutdown_joined':not thread.is_alive(),'limitations':'Local fixture provider; not a multi-day live-model soak.'}
finally:
 if thread.is_alive():r.control('stopped');thread.join(5)
 r.close()
second=Runtime(a.directory/'agent',FixtureProvider(),fixtures=fixtures)
try:
 result['restart_retains_stop']=second.db.get('control')=='stopped'
 result['restart_artifacts']=len(second.db.rows('SELECT * FROM artifacts'))
finally:second.close()
(a.directory/'soak.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
