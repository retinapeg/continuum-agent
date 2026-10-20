"""Replay immutable offline sources without overwriting original experiment evidence."""
import argparse,hashlib,json,os,subprocess,sys,tarfile,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('target',help='v01 or path to an offline v02 campaign');a=p.parse_args()
with tempfile.TemporaryDirectory(prefix='replay-',dir=ROOT/'.cache/tmp') as tmp:
 directory=Path(tmp)
 if a.target=='v01':
  archive=ROOT/'preserved/v0.1/tree.tar.gz'
  expected=json.loads((archive.parent/'manifest.json').read_text())['archive_sha256']
  assert hashlib.sha256(archive.read_bytes()).hexdigest()==expected
  with tarfile.open(archive) as tar:tar.extractall(directory,filter='data')
  env={**os.environ,'TMPDIR':str(ROOT/'.cache/tmp')}
  subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=directory,env=env,check=True)
  subprocess.run([sys.executable,'-m','continuum','benchmark','--seeds','30','--output','regenerated'],cwd=directory,env=env,check=True,stdout=subprocess.DEVNULL)
  for name in ('runs.csv','summary.json','manifest.json'):assert (directory/'results'/name).read_bytes()==(directory/'regenerated'/name).read_bytes(),name
  print('PASS: archived v0.1 tests and all benchmark artifacts reproduce byte-identically')
 else:
  campaign=(ROOT/a.target).resolve();protocol=json.loads((campaign/'protocol.json').read_text())
  if protocol['live']:raise SystemExit('Live calls are new trials, not deterministic replay. Use resume for unfinished units.')
  with tarfile.open(campaign/'frozen-source.tar.gz') as tar:tar.extractall(directory,filter='data')
  for path,h in protocol['source_manifest'].items():assert hashlib.sha256((directory/path).read_bytes()).hexdigest()==h
  (directory/'.cache/tmp').mkdir(parents=True)
  # Use original immutable manifest but a fresh output directory inside the recovered tree.
  output=directory/'experiments/v02/replayed';output.mkdir(parents=True)
  for name in ('protocol.json','protocol.sha256'):(output/name).write_bytes((campaign/name).read_bytes())
  subprocess.run([sys.executable,'-m','continuum.research.campaign','run','--directory',str(output)],cwd=directory,check=True,stdout=subprocess.DEVNULL)
  def normalized(path):
   return [{k:v for k,v in json.loads(line).items() if k!='elapsed_seconds'} for line in path.read_text().splitlines()]
  assert normalized(output/'results.jsonl')==normalized(campaign/'results.jsonl')
  print('PASS: offline per-unit metrics reproduce (elapsed wall time excluded)')
