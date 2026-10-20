"""Export static scientific figures from actual frozen result summaries."""
import json,sys,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'continuum-v02'})
offline=json.loads((ROOT/'experiments/v02/offline-final-v2/report.json').read_text())
fig,ax=plt.subplots(figsize=(8,4.8),layout='constrained')
styles={'A':('#64748b','o'),'B':('#f59e0b','s'),'C':('#2563eb','D'),'D':('#059669','^'),'E':('#9333ea','x'),'D_no_memory':('#dc2626','v')}
for condition,(color,marker) in styles.items():
 groups=[offline['means'][f'{condition}/budget-{b}'] for b in (2,4,8)]
 ax.plot([g['provider_calls'] for g in groups],[100*g['goal_completion'] for g in groups],label=condition,color=color,marker=marker,linewidth=1.5,alpha=.85)
ax.set(xlabel='Mean fixture-provider calls per episode (budgets 2 / 4 / 8)',ylabel='Verified goal completion (%)',title='Offline resource curve · 180 scenario instances per condition/budget',ylim=(0,50))
ax.grid(alpha=.15);ax.legend(ncol=3,loc='lower right')
output=ROOT/'evidence/figures';output.mkdir(exist_ok=True)
fig.savefig(output/'offline-resource-curve.svg',metadata={'Date':None});fig.savefig(output/'offline-resource-curve.png',dpi=140);plt.close(fig)
live_path=ROOT/'experiments/v02/live-heldout-v1/report.json'
if live_path.exists():
 live=json.loads(live_path.read_text());fig,ax=plt.subplots(figsize=(8,4.5),layout='constrained')
 pairs=[(key,val) for key,val in live['paired_scenario_bootstrap_95'].items() if key.endswith('budget-6')]
 for i,(name,v) in enumerate(pairs):
  ax.errorbar(100*v['mean'],i,xerr=[[100*(v['mean']-v['low'])],[100*(v['high']-v['mean'])]],fmt='o',color='#059669',capsize=5)
 ax.axvline(0,color='#64748b',linewidth=1,linestyle='--');ax.set_yticks(range(len(pairs)),[p[0].split('/')[0] for p in pairs])
 ax.set(xlabel='Paired completion difference (percentage points)',title='Held-out Claude Haiku · scenario-cluster bootstrap 95% intervals')
 ax.grid(axis='x',alpha=.15)
 fig.savefig(output/'live-paired-differences.svg',metadata={'Date':None});fig.savefig(output/'live-paired-differences.png',dpi=140);plt.close(fig)
print('Exported source-backed scientific SVG figures')
