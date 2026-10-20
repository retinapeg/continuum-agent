"""Run the frozen held-out campaign after the bounded development calls finish."""
import json,sqlite3,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
started=time.monotonic()
while time.monotonic()-started<1800:
    with sqlite3.connect(ROOT/'experiments/v02/live-pilot-v2/campaign.sqlite') as db:
        pending=db.execute("SELECT COUNT(*) FROM units WHERE status NOT IN ('succeeded','failed')").fetchone()[0]
    if pending==0 and (ROOT/'experiments/v02/routing-development-v1/report.json').exists():break
    time.sleep(5)
else:raise SystemExit('Development campaign gate exceeded 30 minutes; held-out remains queued, not silently started.')
subprocess.run([sys.executable,'-m','continuum.research.campaign','run','--directory','experiments/v02/live-heldout-v1'],cwd=ROOT,check=True)
