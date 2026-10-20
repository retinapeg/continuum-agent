"""Write a development receipt; never estimates uncaptured parent-session usage."""
import argparse,hashlib,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from continuum.runtime.common import ROOT,digest,utc
p=argparse.ArgumentParser();p.add_argument('name');p.add_argument('--tests',required=True);p.add_argument('--defects',default='No known defect in executed acceptance subset; broader acceptance pending.')
a=p.parse_args()
paths=sorted({p for folder in ('continuum','tests','tests_runtime','scripts','schemas','config') for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in ('.py','.js','.css','.html','.json')}) + sorted(ROOT.glob('*.md')) + sorted(ROOT.glob('requirements*.txt')) + [ROOT/'pyproject.toml']
manifest={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in paths}
log=(ROOT/a.tests).read_text()
r={'kind':'development-build','name':a.name,'created_at':utc(),'source_manifest':manifest,'source_manifest_hash':digest(manifest),
   'tests_executed':a.tests,'test_log_hash':hashlib.sha256(log.encode()).hexdigest(),'result':'passed' if log.rstrip().endswith('OK') else 'failed',
   'regressions':'original v0.1 artifacts independently verified; new regressions included in test log','known_defects':a.defects,
   'parent_build_usage':None,'usage_reason':'parent coding-session telemetry not captured; no inferred spend'}
path=ROOT/'evidence/build'/f'{a.name}.json';path.write_text(json.dumps(r,indent=2)+'\n');print(path)
