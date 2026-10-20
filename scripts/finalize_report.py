"""Generate the closeout report only after the declared held-out matrix finishes."""
import collections,hashlib,json,sqlite3,sys,tarfile
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
work=ROOT/'experiments/v02/live-heldout-v1'
protocol=json.loads((work/'protocol.json').read_text());live=json.loads((work/'report.json').read_text())
if live['attempted_episodes']!=len(protocol['units']):raise SystemExit('Held-out matrix incomplete: do not generate a completion report.')
rows=[json.loads(x) for x in (work/'results.jsonl').read_text().splitlines()]
fail=json.loads((work/'failure-analysis.json').read_text())
offline=json.loads((ROOT/'experiments/v02/offline-final-v2/report.json').read_text())
soak=json.loads((ROOT/'.runtime/soak-final/soak.json').read_text())
tests=json.loads((ROOT/'evidence/build/test-summary.json').read_text())
(ROOT/'evidence/build/soak-final.json').write_text(json.dumps(soak,indent=2)+'\n')
base=json.loads((ROOT/'preserved/v0.1/manifest.json').read_text())
originals={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in base['files'].items() if p.startswith(('continuum/','tests/','results/')) or p=='OVERNIGHT_REPORT.md'}
with tarfile.open(ROOT/'preserved/v0.1/tree.tar.gz') as tar:
 readable=all(hashlib.sha256(tar.extractfile(name).read()).hexdigest()==h for name,h in base['files'].items())
archive_matches=hashlib.sha256((ROOT/'preserved/v0.1/tree.tar.gz').read_bytes()).hexdigest()==base['archive_sha256']
assert all(originals.values()) and archive_matches and readable
integrity={'original_source_tests_results_unchanged':originals,'archive_hash_matches':archive_matches,'archive_members_readable_and_match':readable,'original_git_head':None,'changes_left_uncommitted':True}
(ROOT/'evidence/build/final-integrity.json').write_text(json.dumps(integrity,indent=2)+'\n')
with sqlite3.connect(work/'campaign.sqlite') as db:first=db.execute('SELECT MIN(started) FROM calls').fetchone()[0]
last=max(p.stat().st_mtime for p in work.glob('units/*/result.json'))
window=last-datetime.fromisoformat(first.replace('Z','+00:00')).timestamp()
receipt={'kind':'experimental-agent-campaign','first_provider_attempt_utc':first,'last_unit_result_utc':datetime.fromtimestamp(last,timezone.utc).isoformat(),'observed_call_to_result_window_seconds':window,'timing_scope':'UTC first provider attempt to final unit result file; excludes setup/report generation, not a monotonic whole-build timer','attempted_episodes':len(rows),'provider_attempts':sum(x.get('provider_calls',0) for x in rows),'protocol_sha256':(work/'protocol.sha256').read_text().strip(),'actual_subscription_charge':None,'charge_reason':'not observed; API-equivalent estimates are not invoices'}
(work/'campaign-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
labels={'A':'Reactive + memory','B':'Periodic + memory','C':'Event/deadline baseline','D':'Hybrid continuous state','E':'D schedule, state withheld'}
hybrid_stats=live['means']['D/budget-6'];event_stats=live['means']['C/budget-6']
dc=live['paired_scenario_bootstrap_95']['D-minus-C/budget-6'];de=live['paired_scenario_bootstrap_95']['D-minus-E/budget-6']
preflight=json.loads((ROOT/'evidence/build/post-campaign-preflight.json').read_text())
schedule_pairs=fail['realized_D_E_schedules']
def pct(value):return 'unknown' if value is None else f'{100*value:.2f}%'
def num(value):return 'unknown' if value is None else f'{value:.3f}'
lines=['# MORNING REPORT — CONTINUUM v0.2','',
'Built on the existing v0.1 simulator, with source/results preserved and no Git commit. The deliverable is a restartable local runtime with real Claude-backed chat/document work, explicit memory and owner controls, plus a frozen synthetic experimental platform. It is not production-ready or a demonstration of consciousness or general long-horizon intelligence.','',
'## Delivery and evidence','',
'- **Baseline preserved:** readable 21-file snapshot includes untracked files; hashes and restore instructions are in `preserved/v0.1/`. Original simulator source/tests/results and OVERNIGHT_REPORT are unchanged. The empty Git history was not a blocker.',
f"- **Tests:** {tests['runtime']['passed']} runtime/security/scorer/integration tests and {tests['legacy']['passed']} archived simulator tests passed: {tests['runtime']['passed']+tests['legacy']['passed']} total. Real Chromium verified desktop/mobile chat, artifact reading, fact correction and pause/resume.",
'- **Live path:** the three-call, 40.215-second wall-clock demo used exact model `claude-haiku-4-5-20251001`, noticed a new fictional review without a second user message, produced a cited brief and initiated a local clarification.',
'- **Runtime:** SQLite goals, observations, beliefs, action leases, pending proposals, outbox and recovery checkpoints; monotonic wall-clock execution and separate simulated clocks; analytical/discrete dynamics and explicit activation controls.',
'- **Control/security:** tool-less structured proposals, narrow local capabilities, strict schema/evidence/permission checks, path confinement, private memory exclusions, conservative forgetting and authenticated loopback controls. Unknown effects are not blindly replayed.',
'- **Integrations:** project-local envelope/HTTP stub and read-only APIs are implemented. There is no actual Leo OS or Agent Exchange integration, no A2A/MCP implementation and no external messaging/payment/executable-code capability.','',
'## Held-out live result','',
f"Completed **{len(rows)}/180** declared episodes: 18 scenario instances across six templates, two stochastic repetitions and five policies, six-call ceiling per episode. Fixed primary model: `{protocol['requested_model']}`. The observed first-call-to-last-result window was **{window/60:.1f} minutes**; model service time did not advance virtual world deadlines.",'',
'| Policy | Episodes | Completion, all attempted | Valid-only completion | Pooled intervention precision | Pooled recall | Mean calls |',
'|---|---:|---:|---:|---:|---:|---:|']
for c,label in labels.items():
 g=live['means'][f'{c}/budget-6'];lines.append(f"| {c} · {label} | {g['episodes']} | {pct(g['goal_completion'])} | {pct(g['conditional_valid_completion'])} | {pct(g['pooled_intervention_precision'])} | {pct(g['pooled_intervention_recall'])} | {g['provider_calls']:.2f} |")
lines+=['','| Paired difference | Mean | 95% scenario-cluster bootstrap interval |','|---|---:|---:|']
for control in ('A','B','C','E'):
 d=live['paired_scenario_bootstrap_95'][f'D-minus-{control}/budget-6'];lines.append(f"| D minus {control} | {100*d['mean']:+.2f} pp | [{100*d['low']:+.2f}, {100*d['high']:+.2f}] pp |")
lines+=['','These comparisons apply to the declared six handcrafted templates. Scenario clusters, not individual model calls, define the uncertainty calculation. Repetitions are averaged within each scenario. A tie or interval spanning zero is not evidence of equivalence. Wider real-world claims are unsupported.','',
f"**Central finding:** D completed {round(hybrid_stats['goal_completion']*hybrid_stats['episodes'])}/{hybrid_stats['episodes']} episodes ({pct(hybrid_stats['goal_completion'])}); C completed {round(event_stats['goal_completion']*event_stats['episodes'])}/{event_stats['episodes']} ({pct(event_stats['goal_completion'])}). D used {hybrid_stats['provider_calls']:.2f} invocations per episode versus C's {event_stats['provider_calls']:.2f}. D minus C was {100*dc['mean']:+.2f} percentage points with a 95% interval of [{100*dc['low']:+.2f}, {100*dc['high']:+.2f}]. D minus the state-withheld E control was {100*de['mean']:+.2f} points [{100*de['low']:+.2f}, {100*de['high']:+.2f}]. These results do not establish an added benefit from the continuous-state mechanism.",'',
'Losses remain visible: D completed 33.33% of memory-revision episodes versus C\'s 50%; E outperformed D on delayed dependencies and deadline/follow-up tasks. D performed better than C on document updates. Each family has only six live episodes per policy, so these are descriptive failure-analysis signals.','',
'[Full family results, latency, interruptions, supported-field accuracy and failure analysis](experiments/v02/live-heldout-v1/ANALYSIS.md). [Raw per-unit results](experiments/v02/live-heldout-v1/results.jsonl). [Frozen protocol/source](experiments/v02/live-heldout-v1/protocol.json).','',
'![Paired live differences](evidence/figures/live-paired-differences.svg)','',
'## Failures, costs and interpretation','',
'Observed provider failure categories: `'+json.dumps(fail['taxonomy'],sort_keys=True)+f"`. All attempted episodes remain in the primary denominator. Conditional-on-valid-execution results are labelled separately. **{sum(pair['equal'] for pair in schedule_pairs)}/{len(schedule_pairs)}** realized D/E call schedules matched in this campaign; exact paired call times are retained in `failure-analysis.json`.",'',
'Precision/recall opportunities were fixed before inference. The scorer requires timely local effects, current source references, exact supported Status/Risk fields and a real Markdown table where requested. It does not certify every natural-language assertion. Clarification uses a narrow predefined rubric. Human-review packets contain both successes and failures and remain **AWAITING INDEPENDENT HUMAN REVIEW**.','',
'| Policy | Aggregate known API-equivalent USD subtotal | Complete total USD estimate | USD / verified outcome, all attempts | Token telemetry complete? |',
'|---|---:|---:|---:|---|']
for c in labels:
 g=live['means'][f'{c}/budget-6'];lines.append(f"| {c} | {num(g['known_api_estimate_usd_subtotal'])} | {num(g['total_api_equivalent_usd'])} | {num(g['cost_per_verified_outcome_all_attempts'])} | {'yes' if g['token_totals'] is not None else 'no'} |")
lines+=['','Known subtotals exclude episodes with incomplete telemetry and are not total spend. The frozen adapter discarded terminal-error usage and usage from responses discarded after a control change. Some missing telemetry is therefore an instrumentation defect, not necessarily missing provider telemetry. These records cannot be reliably reconstructed; no failed trial was rerun to backfill them. The post-campaign repair retains available error/cancellation usage and was regression-tested; the frozen source and outcomes remain unchanged.','',
'Missing usage, rate dates and actual subscription charges remain null. CLI-reported API-equivalent estimates are not invoices. Per-model token rows, including auxiliary CLI work, are aggregated once; primary usage is retained separately. A recorded call is one CLI invocation, which may contain multiple internal inference requests or retries. The parent coding session was not metered here. Build receipts are separate from agent-run receipts.','',
f"The repaired adapter passed a fresh exact-model live preflight in **{preflight['elapsed']:.3f} seconds**, with no cleanup warnings. The completed-campaign resume check made **zero new calls** and preserved the raw-results SHA256. [Repair receipt](evidence/build/accounting-repair-applied.json) · [Live preflight](evidence/build/post-campaign-preflight.json) · [Resume check](evidence/build/completed-resume.json).",'',
'## Offline resource and ablation result','',
'The final fixture matrix completed and replayed **3,240/3,240** episodes: 30 seeds × six families × six conditions × budgets 2/4/8. At budget 4, completion was A 22.22%, B 28.89%, C/D/E 38.89%, and D with lexical retrieval removed 22.22%. Observation history remains in that memory ablation. Equal ingestion across policies does not demonstrate a scheduler memory advantage.','',
'At budget 8, C and D again tied at 38.89%, while mean calls were 5.111 and 7.311. D and E matched every final offline call schedule. The fixture policy does not use state features to choose action content, so this state-ablation tie is an expected control, not proof that state features cannot help an LLM.','',
'![Offline resource curve](evidence/figures/offline-resource-curve.svg)','',
'The preserved v0.1 results reproduce: adaptive 94.21%, reactive 82.93%, periodic 73.58% across 450 runs. An independent exploratory idle-activation ablation preserved all 150 adaptive action outcomes while reducing decisions 7,969→7,402 and synthetic cost 2,494.2→2,437.5. That weakens a causal interpretation of its decaying-state mechanism. v0.1 and v0.2 use different workloads and metrics; their completion percentages are not a direct progress comparison.','',
'## Pilot findings, reliability and routing','',
'- Pilot-v1 exposed a tool-receipt wake-up defect; a waiting goal could fail to continue after a read. It was repaired and regression-tested. Its original source and 30 outcomes remain intact.',
'- Pilot-v2 retained a 180,000-byte stream cap and produced three output-bound failures, one model-slot failure and one rejected unexpected tool request. The final one-million-byte bound addresses framing overhead while retaining a real hard limit. No failed pilot was relabelled as a successful repaired run.',
'- Independent review repaired model-dependent skip gates in the exact-schedule ablation, false-positive table scoring, stale-field accounting and failed-episode pooled denominators before held-out execution.',
'- The routing development check had six trials: valid responses 1/2 fixed Haiku, 2/2 fixed Sonnet and 2/2 router; the narrow exact-colon-field artifact check passed 0/2, 0/2 and 1/2 respectively. This small operational check cannot establish router superiority or broad model quality.',
'- The proposal-only improvement copy changed reflection 30→60 seconds on three development fixture scenarios. Completion stayed 2/3 and calls 22→19. The diff is queued, **not applied**; promotion requires fresh evaluation and human review.','',
f"The final wall-clock fixture soak lasted **{soak['actual_elapsed_seconds']:.3f} seconds**, with {soak['inferences']} fixture deliberations, {soak['artifact_count']} artifact(s) and {soak['interruptions']} locally available notification(s). Pause, resume, joined shutdown and restart-retained stop were observed. This is a ten-minute local fixture test, not a multi-day live-model run. The earlier 120.035-second soak is also retained.",'',
'## Boundaries and outstanding work','',
'All implementation/source changes are in this repository and left uncommitted on the existing main branch. No branch, worktree, commit, push, deployment, sibling import/edit, real third-party message, payment or separately billed API was used. Repository-local environments and caches were used. One coordinator wrote source; independent readers wrote isolated review receipts; model concurrency was bounded to two.','',
'**Outstanding permissions: none for the delivered local scope.** Codex inference is disabled because complete ambient-tool isolation is NOT VERIFIED; ChatGPT authentication alone is insufficient. The exact failed isolation preflight is in `evidence/build/codex-preflight.json`. No weaker isolation or API billing fallback was used. External integrations/payments, production deployment and automatic improvement promotion remain unimplemented/unauthorized.','',
'Known limits include narrow synthetic templates, virtual deadlines, short real soak, lexical-only retrieval, unconfirmed model-proposed beliefs, partial prose scoring, optional/null distributed-tracing fields, best-effort secret redaction, no database encryption and no forensic/provider-side deletion guarantee. No physical power-loss or actual disk-exhaustion test was performed. The baseline source retains its original out-of-horizon feasibility edge and test connection ResourceWarning; stock benchmark results are unaffected.','',
'## Start, verify and inspect','',
'```sh',
'.venv/bin/python -m continuum.runtime start --directory .runtime/live --provider claude --model claude-haiku-4-5-20251001',
'.venv/bin/python -m continuum.runtime status --directory .runtime/live',
'.venv/bin/python -m continuum.runtime pause --directory .runtime/live',
'.venv/bin/python -m continuum.runtime resume --directory .runtime/live',
'.venv/bin/python -m continuum.runtime stop --directory .runtime/live',
'.venv/bin/python -m unittest discover -s tests_runtime -v',
'.venv/bin/python scripts/reproduce.py v01',
'.venv/bin/python scripts/reproduce.py experiments/v02/offline-final-v2',
'.venv/bin/python -m continuum.research.campaign resume --directory experiments/v02/live-heldout-v1',
'.venv/bin/python scripts/analyze.py --directory experiments/v02/live-heldout-v1',
'.venv/bin/python scripts/plot_results.py',
'```','',
'Start is a foreground server; use a second terminal for controls. Stop persists and exits it; explicitly use `start ... --resume` to resume after restart. A completed campaign resume makes no new model calls, including after the telemetry repair. Source drift remains rejected if unfinished experimental units would execute. See README for initial dependency setup and browser checks.','',
'**Next step:** open the local dashboard and review the example brief, memory correction history and failed-trial evidence. The build stops here; no further scope expansion or automatic promotion is queued.']
(ROOT/'MORNING_REPORT.md').write_text('\n'.join(lines)+'\n')
print('Generated MORNING_REPORT.md, final integrity and campaign timing receipts')
