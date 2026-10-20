"""Regenerate human-readable tables and portable failure/review artifacts from frozen runs."""
import argparse,collections,hashlib,json,sqlite3,statistics,sys
from contextlib import closing
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from continuum.runtime.common import ROOT
from continuum.research.campaign import report
p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();directory=a.directory.resolve()
if not directory.is_relative_to(ROOT/'experiments/v02'):p.error('versioned repository-local campaign required')
protocol=json.loads((directory/'protocol.json').read_text())
if hashlib.sha256((directory/'protocol.json').read_bytes()).hexdigest()!=(directory/'protocol.sha256').read_text().strip():raise SystemExit('Manifest checksum mismatch')
r=report(directory)
rows=[json.loads(line) for line in (directory/'results.jsonl').read_text().splitlines()]
def fmt(x,percent=False):return '—' if x is None else (f'{100*x:.2f}%' if percent else f'{x:.3f}')
lines=[f'# {directory.name}: regenerated analysis','',f"Split: **{protocol['split']}**. Provider: `{protocol['provider']}` / `{protocol['requested_model']}`.",f"Attempted: **{r['attempted_episodes']} / {len(protocol['units'])}** declared episodes. Statuses: `{r['statuses']}`.",'',
       'Unit persistence status records whether the runner saved an episode result; it is not the goal-completion verdict.','',
       '| Condition / call budget | Episodes | Completion | Valid-only completion | Pooled precision | Pooled recall | Mean calls | Mean interruptions | Conditional virtual latency (s) | All-attempt USD estimate / outcome |',
       '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for name,g in r['means'].items():
 lines.append('| '+name+' | '+str(g['episodes'])+' | '+' | '.join(fmt(g.get(k),k in ('goal_completion','conditional_valid_completion','pooled_intervention_precision','pooled_intervention_recall')) for k in ('goal_completion','conditional_valid_completion','pooled_intervention_precision','pooled_intervention_recall','provider_calls','interruptions','latency','cost_per_verified_outcome_all_attempts'))+' |')
lines+=['','Null values are unavailable or have no denominator. Precision/recall above are pooled; JSON also retains conditional episode means and contributing counts. Valid-only means no call-level failure; a failed or denied tool action still counts as a valid protocol execution with an unsuccessful task outcome. A recorded model call is one CLI invocation, which may contain internal retries and auxiliary inference requests. USD values are CLI API-equivalent estimates, never subscription invoices. Missing cost in any attempted episode makes total cost/outcome unknown.','',
        '## Factuality, clarification and reliability','',
        '| Condition / budget | Supported fields | Stale fields, mean | Contradiction handled | Appropriate clarification | Appropriate inaction | Recovery | Duplicate effects, mean |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
quality=('supported_fact_accuracy','stale_fact_uses','contradiction_handled','appropriate_clarification','appropriate_inaction','recovery_success','duplicate_effects')
for name,g in r['means'].items():
 lines.append('| '+name+' | '+' | '.join(fmt(g.get(k),k not in ('stale_fact_uses','duplicate_effects'))+f" (n={g[k+'_n']})" for k in quality)+' |')
lines+=['','Counts are contributing episodes for each metric; task-specific metrics have fewer eligible episodes. These are descriptive means, not additional confirmatory significance tests. Parsed supported fields do not certify unrestricted prose.','',
        '## Resource accounting','',
        '| Condition / budget | Episode wall time, mean seconds | Interruptions / simulated hour | Known USD subtotal | Complete USD total | Uncached input | Cached reads | Cache creation | Output tokens |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for name,g in r['means'].items():
 condition,budget_text=name.split('/budget-');elapsed=[x['elapsed_seconds'] for x in rows if x['condition']==condition and x['budget']==int(budget_text) and 'elapsed_seconds' in x]
 tokens=g.get('token_totals') or {}
 lines.append('| '+name+' | '+' | '.join(fmt(x) for x in [statistics.mean(elapsed) if elapsed else None,g['interruptions_per_simulated_hour'],g['known_api_estimate_usd_subtotal'],g['total_api_equivalent_usd']]+[tokens.get(k) for k in ('uncached_input','cached_read','cache_creation','output')])+' |')
lines+=['','Known subtotals include only episodes with complete recorded cost telemetry; they are lower bounds, not total cost. Wall time includes local processing/provider waits for an episode. Interruption rates use the 120-second simulated horizon and must not be read as observed real-world hourly contact rates. Missing usage remains unknown. Actual subscription charges and rate dates are unobserved.','',
        '## Paired differences','', '| D minus control / budget | Scenario clusters | Completion difference | 95% bootstrap interval |','|---|---:|---:|---:|']
for key,v in r['paired_scenario_bootstrap_95'].items():lines.append(f"| {key} | {v['scenarios']} | {100*v['mean']:+.2f} pp | [{100*v['low']:+.2f}, {100*v['high']:+.2f}] pp |")
conditions=protocol['conditions'];lines+=['','## Family completion','', '| Family | '+' | '.join(conditions)+' |','|---|'+'---:|'*len(conditions)]
for family,groups in r['by_family'].items():lines.append('| '+family+' | '+' | '.join(fmt(groups.get(c,{}).get('completion'),True) for c in conditions)+' |')
lines+=['','Offline family values pool call budgets; use per-budget tables for resource comparisons. There are six handcrafted templates, not broad task generalization. Zero differences or narrow intervals do not establish equivalence.','', '## Execution failures and schedule checks','']
failures=[];review=[];accounting={}
for unit in protocol['units']:
 dbpath=directory/'units'/unit['id']/'agent/agent.sqlite'
 if not dbpath.exists():continue
 with closing(sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)) as db:
  db.row_factory=sqlite3.Row
  accounting.setdefault(unit['condition'],[]).extend(dict(row) for row in db.execute('SELECT status,usage FROM calls'))
  for row in db.execute("SELECT created,status,error FROM calls WHERE status!='succeeded'"):failures.append({'unit':unit['id'],**dict(row)})
  if unit['seed']==protocol['seeds'][0] and unit['repetition']==0 and unit['condition'] in ('C','D') and unit['budget']==max(protocol['budgets']):
   ops=[dict(x) for x in db.execute("SELECT kind,args,status,result FROM operations WHERE kind IN ('create_artifact','request_clarification')")]
   sources=[{'path':f.name,'content':f.read_text()} for f in (dbpath.parent.parent/'public-documents').glob('*.md')]
   review.append({'unit':unit['id'],'selection':'predeclared first seed, repetition0, C/D, maximum budget; includes failures','operations':ops,'revealed_sources':sources,'human_review_status':'NOT_REVIEWED'})
counts=dict(collections.Counter(f['error'] or f['status'] for f in failures))
lines.append('Call failures: `'+json.dumps(counts,sort_keys=True)+'`. All remain in attempted-episode results.')
comparisons=[]
for d in [x for x in rows if x['condition']=='D']:
 es=[x for x in rows if x['condition']=='E' and (x['scenario'],x['repetition'],x['budget'])==(d['scenario'],d['repetition'],d['budget'])]
 if es and 'call_times' in d and 'call_times' in es[0]:comparisons.append({'scenario':d['scenario'],'repetition':d['repetition'],'budget':d['budget'],'equal':d['call_times']==es[0]['call_times'],'D':d['call_times'],'E':es[0]['call_times']})
if comparisons:lines.append(f"Realized D/E call schedules match in {sum(c['equal'] for c in comparisons)}/{len(comparisons)} comparable pairs. Mismatches are retained below in machine-readable analysis, including safety stops.")
coverage={}
lines+=['','## Observed usage coverage','',
        '| Condition | Recorded usage / attempted calls | Known uncached input | Known cached reads | Known cache creation | Known output | Known call-level USD subtotal |',
        '|---|---:|---:|---:|---:|---:|---:|']
for condition,calls in sorted(accounting.items()):
 usages=[json.loads(call['usage']) for call in calls if call['usage'] and json.loads(call['usage']) is not None]
 categories={}
 for key in ('uncached_input','cached_read','cache_creation','output','other','api_equivalent_usd'):
  values=[u[key] for u in usages if type(u.get(key)) in (int,float)]
  categories[key]={'known_subtotal':sum(values) if values else None,'calls_with_category':len(values),'complete_total':sum(values) if len(values)==len(calls) and calls else None}
 coverage[condition]={'attempted_calls':len(calls),'calls_with_usage':len(usages),'calls_without_usage':len(calls)-len(usages),'categories':categories}
 token_text=[str(categories[k]['known_subtotal']) if categories[k]['known_subtotal'] is not None else '—' for k in ('uncached_input','cached_read','cache_creation','output')]
 lines.append(f"| {condition} | {len(usages)} / {len(calls)} | "+' | '.join(token_text)+f" | {fmt(categories['api_equivalent_usd']['known_subtotal'])} |")
lines+=['','These call-level subtotals include observed calls inside incomplete episodes, so they differ from the more conservative complete-episode subtotals above. Neither is total spend. Missing categories and complete totals remain null in `usage-coverage.json`. The frozen live adapter discarded some terminal-error usage; a post-campaign repair preserves future receipts but does not backfill these trials.','']
lines+=['','## Interpretation limits','', 'Supported-fact accuracy covers parsed Status/Risk fields only. Stale-field counts are not a complete semantic contradiction detector. Clarification checks use a predefined narrow rubric. Latency is conditional on a matched opportunity and uses virtual world time. Provider tokens are aggregate telemetry; auxiliary CLI models are included once. Workload recovery denotes a clean reopen; crash recovery has separate tests.','', 'Review packets are prepared for independent human review; no completed human review is claimed. Model self-grades do not determine scores.']
(directory/'ANALYSIS.md').write_text('\n'.join(lines)+'\n')
(directory/'failure-analysis.json').write_text(json.dumps({'call_failures':failures,'taxonomy':counts,'realized_D_E_schedules':comparisons},indent=2)+'\n')
(directory/'usage-coverage.json').write_text(json.dumps(coverage,indent=2,sort_keys=True)+'\n')
(directory/'human-review-packet.json').write_text(json.dumps({'rubric':['Are all substantive prose assertions supported by revealed sources?','Are uncertainty and source references accurate?','Is clarification necessary and specific?','Was intervention timely and useful?'],'status':'AWAITING_INDEPENDENT_HUMAN_REVIEW','samples':review},indent=2)+'\n')
print(directory/'ANALYSIS.md')
