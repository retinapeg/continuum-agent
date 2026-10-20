# Experiment protocol v2.1

Defined before scored runs. v0.1 raw evidence remains in `results/` and the verified snapshot `preserved/v0.1/`. New evidence lives in versioned `experiments/v02/` directories. Each campaign freezes a JSON protocol, SHA-256 checksum, Python source manifest, scenario hashes, policy order, model, prompt/schema implementation, budgets and scoring rules. Unfinished execution rejects source drift; every resume rejects manifest tampering.

## Units and splits

Six synthetic multi-event families: delayed dependencies, changed instructions, deadline/follow-up management, evidence-grounded document revision, interrupted work, and distractor-heavy conflicting preferences. Each has a 120-second virtual horizon and observations at six-second resolution. Documents are fictional substantive project reports. Dependencies, revised formats and source versions matter; not every outcome is a document. Clarification and inaction can be correct.

Development uses seeds 0–29. Live pilot uses seed 101 in each family. Held-out live seeds are 1001–1003, with two stochastic repetitions per scenario/condition. Repetitions are not independent scenarios. Live inference consumes real time but world time is simulated; this does not demonstrate days of uninterrupted operation.

## Conditions

- A: reactive, persistent memory, acts at initial owner goal and subsequent owner observations.
- B: same memory/policy, fixed 30-second schedule.
- C: strong event/deadline arithmetic control: relevant events, explicit follow-up/deadline, and six-second follow-up after document availability to use read receipts.
- D: C plus analytical state-dependent reflection. Public event impulses and normalized staleness/pressure/uncertainty determine extra wakes.
- E: D's exact precomputed public-prefix activation schedule, with state features withheld from model context and discrete hold dynamics internally.
- D_no_memory: separate offline ablation, D schedule with lexical memory retrieval omitted. Public observation history remains, so this is retrieval ablation, not total amnesia.

All schedules are derived by iterating public observation prefixes. They do not inspect private eligible windows or future readiness. Schedule generation is fixed before calls. The real owner runtime also supports model-proposed next consideration times; experimental schedules override those times and model-dependent waiting/completion skip gates to isolate timing. Thus D/E consume identical eligible wake times up to the same call budget, except documented provider failures, owner pauses or outcome-unknown safety stops. Earlier offline-v1/v2 and pilot-v1/v2 froze the former skip-gate behavior and only had equal eligible wake schedules; they are development evidence, not the final exact-schedule ablation. The same exact main model and proposal schema are used for every live condition. State differs only where declared. All conditions use the same observation ingestion, capability validator, permission checks and verification.

## Finite matrices

Offline: 30 seeds × 6 families × 6 conditions × call budgets {2,4,8} = **3,240 episodes**. Fixture rule provider is explicitly not an LLM. This yields resource-constrained comparisons and performance-versus-call-budget curves.

Pilot v1: 30 episodes with Sonnet and budget 4, retained as development evidence. It exposed a tool-receipt wake-up defect and insufficient read/write call budgets. Pilot v2 freezes the repaired source, uses exact model `claude-haiku-4-5-20251001` throughout and budget 6: **30 episodes**. The smaller model was selected after successful subscription preflight to bound campaign latency, before held-out outcomes. Pilot outcomes do not estimate held-out performance.

Live held-out: 3 seeds × 6 families × 5 conditions × 2 repetitions × budget 6 = **180 episodes**, maximum **1,080 adapter calls**. Exact matrix is frozen after preflight/pilot and before held-out outcomes. Two model processes maximum, 90-second call deadline, 3,000 requested output tokens, actual 1,000,000-byte stdout+stderr bound (pilot v2 exposed JSON-stream framing overhead at the former 180,000-byte limit), no automatic request retry, 2,000 project invocation ceiling and two-hour campaign admission limit (already-running bounded episodes may finish after it). Queued units remain resumable at the admission limit. CLI-internal attempts may not be independently exposed; external deadlines remain enforced.

Order is deterministically shuffled within scenario/repetition/budget blocks. No model fallback in the main comparison. CLI auxiliary models are recorded separately from main assistant identity; aggregate token estimates count per-model usage once.

## Protected verification

Private world/scorer data are held by `continuum.research`. Only due observations are copied into runtime storage. Future documents do not exist in approved document roots before availability. Providers are tool-less; no scorer files, private labels or future events enter prompts. Capability paths require announcement plus canonicalized containment, and private memories are excluded. Tests attempt answer-key reads and forged evidence.

Each private opportunity is frozen as an action kind, inclusive eligible window within the horizon, required source IDs and deterministic content constraints. Each opportunity matches at most one successful effect. Duplicate or early/late attempts are false positives. Precision = matched successful interventions / all create-artifact or clarification attempts, including failed effects; recall = matched / eligible opportunities. Empty denominators remain null. For no-op tasks, completion requires no intervention.

Document success requires required facts, current source IDs and absence of explicitly stale assertions. It is not based on model self-grades or the runtime's goal status. Supported-fact accuracy measures only exact extracted `Status:`/`Risk:` claims; absent claims yield null. This limited parser does not certify every natural-language sentence. Human-review JSON artifacts retain actions for sampled review; no human review is claimed unless recorded. Interruption counts use actually available local notifications, not proposed/suppressed messages. Latency is conditional on matched opportunities; compare beside recall/completion.

## Analysis and failure handling

Report all attempted episodes including provider/schema/capability failures. Conditional-on-valid-execution completion is separate: valid means no call-level provider/schema/application exception; blocked or failed capability effects remain task outcomes within that subset. Missing usage and charges stay null. Primary and auxiliary reported token categories are retained; CLI API-equivalent USD estimates are not subscription invoices and do not have independently verified rate tables.

Paired completion differences compare D with A/B/C/E. Average repetitions within each family/seed scenario, then bootstrap scenarios 2,000 times using seed 719. Budgets are stratified. Report losses/ties and null/adverse families, not only an aggregate. Zero-width ceiling intervals do not establish equivalence.

Persist unit states in campaign SQLite and per-unit runtime databases. Finished units are never rerun on resume. Runtime step checkpoints permit safe continuation. A missing provider receipt becomes outcome-unknown; no blind resend. A repeated authorised future trial gets a new unit/repetition ID. Changes after pilot require a new protocol/source freeze; exposed held-out scenarios may not be reused for tuning under the held-out label.

## Exact commands and frozen versions

```sh
# Already frozen held-out matrix; a finished campaign only regenerates its report.
.venv/bin/python -m continuum.research.campaign resume --directory experiments/v02/live-heldout-v1
.venv/bin/python -m continuum.research.campaign report --directory experiments/v02/live-heldout-v1

# A NEW independently labelled trial matrix consumes new subscription calls.
# Do not reuse exposed seeds for tuning while describing them as untouched held-out data.
.venv/bin/python -m continuum.research.campaign freeze --directory experiments/v02/new-live-trial \
  --live --model claude-haiku-4-5-20251001 --call-budget 6
.venv/bin/python -m continuum.research.campaign run --directory experiments/v02/new-live-trial
```

The final offline matrix is `offline-final-v2`; the frozen held-out matrix is `live-heldout-v1`. Earlier `offline-v1`, `offline-v2`, `live-pilot-v1` and `live-pilot-v2` retain their own sources and findings. Partial `offline-final` was stopped after scorer review and is excluded from final comparative tables, with an explicit aborted receipt. This is development history, not silently removed held-out data.

Main source is frozen after independent schedule/scorer review. The one-million-byte adapter bound was exercised by the successful real wall-clock demo. Pilot-v2 retains the earlier tighter bound and resulting failures. Model prompts/scoring are not tuned after main outcomes. Per-unit call timestamps permit checking realized D/E schedule equality; provider failures and owner control interruptions remain visible exceptions.

Each aggregate metric reports contributing episode count. Precision/accuracy/latency means are conditional on defined denominators; pooled intervention precision/recall are separate. Infrastructure failures retain predefined opportunity denominators; unavailable action counts make pooled precision null. Aggregate cost per verified outcome includes ALL attempted episode costs and is null if any required cost is missing. Known subtotals are labelled as incomplete. Interruptions per simulated hour are scaled from the 120-second worlds, not real human interruption rates.

The six templates do not include a broad naturalistic corpus. Misleading preliminary reports, distractors, conflicting preferences, generous deadlines and cancelled follow-ups are adversarial/null cases. Delayed-tool and context-compression stress are covered by runtime tests, not a separately powered held-out family. Workload recovery uses clean reopening; crash checkpoint behavior is tested separately.

## Post-campaign implementation repair

The declared held-out matrix finished all 180 episodes with 844 attempted CLI invocations. Only afterward, the coordinator applied a reviewed accounting repair: retain available terminal-error/discarded-response usage, close campaign SQLite connections, and permit report-only resume for completed campaigns after source drift. Prompts, policies, scenario definitions and scorers were unchanged. The original frozen archive, unit results and their incomplete telemetry remain intact. A completed resume made zero new calls and preserved the raw-results checksum. Current source therefore differs from the archived experimental source; the archive remains authoritative for reproducing its implementation.

The post-campaign usage-coverage table is a descriptive accounting audit. It exposes observed call-level subtotals and missing records without changing any scored outcome or reconstructing lost telemetry. Complete totals and cost per verified outcome remain unknown wherever coverage is incomplete. No held-out results were used to tune agent behavior.
