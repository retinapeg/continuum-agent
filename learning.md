# CONTINUUM — resume context

Last checked: **2026-10-24, Europe/London**. Scope: this repository only.

## Current checkpoint

- Root: `/Users/leo/Projects/continuum-agent`; branch: `main`.
- Audited HEAD: `a0ecdd5606ccb8d9629a7c4c85285f071088684f` (20 October).
- At continuation startup, tracked files were clean; `AGENTS.md`, `learning.md`
  and `decisions.md` were pre-existing untracked work. Their originals are preserved
  in `.cache/continuation-20261024-original/`. This continuation is **uncommitted**.
- The earlier build's no-commit statements are historical: v0.2 already exists at
  the HEAD above. No new branch, commit or push was made in this continuation.
- Latest scope: **offline failure diagnosis completed; no fix implemented**.
  The earlier telemetry changes remain uncommitted. Existing runtime data was not
  resumed. Live inference and integrations remain gated.

## Latest diagnosis — 24 October 2026

Fresh read-only checks reproduce C/D **20/36 each**, calls **184/216**, and the
**−11.11 to +11.11 pp** difference interval. Of 32 unsuccessful C/D episodes,
**23 fail field serialization**, **five ask through an unscored message path**,
and **four have suppressed clarification notifications despite successful operation
receipts**; 29 have no recorded call error. These exclusive proximate causes do
not certify semantic correctness: unsupported prose and repeated questions also occur.
The campaign's 180 `succeeded` rows mean saved episodes, not correct tasks.

[Diagnosis and reproduction commands](evidence/failure-diagnosis-20261024T132605Z/DIAGNOSIS.md)
· [32 episode records](evidence/failure-diagnosis-20261024T132605Z/FAILED_EPISODES.md)
· [five family timelines](evidence/failure-diagnosis-20261024T132605Z/TIMELINES.md).
The 124 software tests below are **saved receipts from the earlier continuation**,
not rerun in this diagnosis. Hashes and re-scoring check preservation/consistency,
not rubric validity. Human semantic review and live telemetry remain unverified.

## Purpose and demonstrated capabilities

Continuum separates persistent work from individual model calls. SQLite stores
goals, observations, memory revisions, operations and local notifications; bounded
capabilities execute validated proposals. Fixture tests demonstrate persistence,
correction/forgetting, owner controls, restart reconciliation and local effects.
Historical Claude/UI/demo/soak receipts exist; current live availability and browser
behavior have **not** been reverified. This is a research runtime, not production-ready.

## Earlier continuation verification (saved receipts)

Existing `.venv` used: Python 3.13.15, jsonschema 4.26.0; documented minimum Python
3.11. No dependencies installed or updated. From the repository root, set
`export TMPDIR="$PWD/.cache/tmp"`; keep that directory available. All commands below
are offline, with transient local HTTP/subprocess fixtures in the runtime tests.
Stored-data re-scoring requires the preserved, ignored campaign/unit SQLite files;
the verifier fails if they are absent or have an uncheckpointed WAL. Frozen offline
replay uses tracked archives and fresh disposable copies instead.

| Command, from this root | Result on 24 October | Local log |
|---|---|---|
| `.venv/bin/python -m unittest discover -s tests_runtime -v` | 96 passed (78 baseline + 18 new) | [runtime log](evidence/continuation-20261024/final-runtime.txt) |
| `.venv/bin/python -m unittest discover -s tests -v` | 28 passed | [legacy log](evidence/continuation-20261024/final-legacy.txt) |
| `.venv/bin/python scripts/verify_stored_evidence.py` | 3,420 re-scored; two reports reconstructed exactly; 3,422 DB integrity checks | [receipt](evidence/continuation-20261024/stored-evidence.json) |
| `.venv/bin/python scripts/reproduce.py v01` | 28 archived tests; 450 runs byte-identical | [replay](evidence/continuation-20261024/v01-reproduction.txt) |
| `.venv/bin/python scripts/reproduce.py experiments/v02/offline-final-v2` | 3,240 frozen episodes replayed; metrics identical except wall timing | [replay](evidence/continuation-20261024/offline-reproduction.txt) |
| `.venv/bin/python -m compileall -q continuum scripts tests tests_runtime`; `git diff --check` | Passed; no configured formatter/type checker | [validation](evidence/continuation-20261024/validation.json) |

The earlier notes-only audit remains recorded in `.cache/resume-audit-20261024/`:
78 runtime tests (2.115s), 28 legacy tests (0.359s). Current baseline logs also show
78 + 28 passed before edits. No pre-existing test failures were observed.

## Experiment register

“Verified” below means recomputed from stored data or replayed offline in this
continuation. “Historical receipt” means supporting files were located/read, with
no fresh execution. No new live trials were made; missing costs remain unknown.

| Experiment ID | Hypothesis | Configuration / N | Baseline | Outcome | Cost / calls | Evidence | Limits |
|---|---|---|---|---|---|---|---|
| v0.1 stock | Adaptive scheduling helps | Simulator, 30 seeds, 450 runs | Reactive / periodic | Verified: adaptive 94.21%, reactive 82.93%, periodic 73.58% | Synthetic cost only | [replay](evidence/continuation-20261024/v01-reproduction.txt), [metrics](results/summary.json) | Different workload/metric from v0.2 |
| v0.1 idle ablation | Decay is needed for the gain | Readiness-only counterfactual, 150 adaptive runs | Original adaptive | Historical receipt: same action outcomes | Decisions 7,969→7,402; synthetic cost 2,494.2→2,437.5 | [audit](evidence/baseline-check/independent-audit.json) | Exploratory, not rerun here |
| offline-final-v2 | State/retrieval improve completion | Fixture, 30 seeds × 6 families × 6 conditions × budgets 2/4/8 = 3,240 | C event/deadline; E state withheld | Verified: budget 4 C/D/E 38.89%, D without retrieval 22.22%; D/E schedules match | Budget 8 mean C 5.111, D 7.311 | [analysis](experiments/v02/offline-final-v2/ANALYSIS.md), [fresh receipt](evidence/continuation-20261024/stored-evidence.json) | Fixture content policy ignores state |
| live-heldout-v1 | Hybrid D improves on C | Claude Haiku exact 20251001 model, 6 families, 18 scenarios × 2 repetitions × 5 policies = 180; budget 6 | C; E schedule-matched/state withheld | **Verified C 55.56%, D 55.56%**; D−C 0 pp, 95% interval −11.11 to +11.11 pp | D 216 calls (6.00/episode), C 184 (5.11); all policies 844; total USD unknown | [raw](experiments/v02/live-heldout-v1/results.jsonl), [fresh receipt](evidence/continuation-20261024/stored-evidence.json) | Synthetic/virtual deadlines; no advantage or equivalence established |
| live-pilot-v1 / v2 | Adapter/runtime feasibility | 30 episodes each, frozen pilot protocols | Five policies | Historical receipts: wake-up, stream-limit and tool-request failures retained | See pilot reports; total charges unknown | [v1](experiments/v02/live-pilot-v1/ANALYSIS.md), [v2](experiments/v02/live-pilot-v2/ANALYSIS.md) | Development exposure, not held-out evidence |
| live-runtime-demo-v1 | Continue after a document arrives | Fictional Juniper; real elapsed 40.215s | No second owner message | Historical receipt: brief and local clarification | 3 calls; subscription charge unknown | [receipt](experiments/v02/live-runtime-demo-v1/receipt.json) | Not replayed live here |
| routing-development-v1 | Routing is operational | 6 trials | Fixed Haiku / Sonnet | Historical receipt: valid 1/2, 2/2, router 2/2; artifact checks 0/2, 0/2, 1/2 | Charges unknown | [report](experiments/v02/routing-development-v1/report.json) | Too small for superiority claims |
| improvement-proposal-v1 | Longer reflection reduces calls | Fixture, 3 scenarios × baseline/candidate | Reflection 30s vs 60s | Historical receipt: both 2/3 completion; queued, not promoted | 22→19 calls | [report](experiments/v02/improvement-proposal-v1/report.json) | Development only; never self-applied |

These findings concern task performance under evaluated conditions. They provide
no evidence for or against AI consciousness.

## Evidence and limits to retain

- `README.md` explains operation; `MORNING_REPORT.md` and `TEST_REPORT.md` record
  historical results; `MODEL_SUPPORT.md` and `SECURITY.md` define provider boundaries.
- The live comparison above is independently verified from stored evidence, without
  new inference. All failed episodes remain in denominators. Bootstrap seed 719,
  2,000 draws, scenario clusters with repetitions averaged first reproduce exactly.
- Codex inference remains disabled pending verified tool isolation. The local
  integration envelope/stub is not working cross-project A2A/MCP interoperability.
- Human review, broader real-world evaluation, physical power-loss validation and
  complete historical cost accounting remain outstanding. Do not turn unknowns into
  successes. See `FUTURE_RESEARCH.md` for proposals, not automatically approved work.
- Preserve `preserved/v0.1/`, `results/`, frozen `experiments/` and prior failures.
  New trials need new IDs/directories; never rerun failures to replace their record.

## Engineering lessons, failures and open questions

- **Accounting:** schema-2 `calls` remain logical deliberations. New
  `provider_attempts` rows identify each provider invocation, including known-unsent
  failures and linked routed fallbacks. `status()['telemetry']` aggregates only unique
  attempt rows. Never add event receipts, per-model subtotals and logical-call costs
  together. Unknown values stay null; CLI estimates are not subscription invoices.
- **Recovery:** atomic additive migration retains old rows and marks their missing
  attempt coverage explicitly. Crash-before-receipt pauses with `process_restart`;
  crash-after-receipt keeps measured cost and still does not resend the logical call.
  Duplicate finalization cannot change totals. New tests cover both boundaries.
- **Attribution/privacy:** provider failure codes are separate from application
  rejection and control discard. Telemetry permits measured fields, not arbitrary
  error/progress/response text. Existing runtime context/action records still contain
  approved content; this is not encryption or a general data-retention redesign.
- **Negative results:** extra continuous-state complexity has no demonstrated
  performance benefit here. The aborted `offline-final` remains preserved because
  table/stale-field scorer defects invalidated that development comparison.
- **Known issues:** 24/844 historical live calls lack usage; no reliable backfill.
  CLI internal retries are opaque (`cli_num_turns` is not a retry count). Legacy
  out-of-horizon feasibility and SQLite ResourceWarning remain documented, unchanged.
  A call can have a successful provider receipt but a rejected/unknown application
  outcome. Human prose review, power-loss testing and extended soak remain unverified.
- **Open questions:** does state help on broader, human-reviewed workloads at equal
  budgets? Can future provider metadata expose internal retry/usage coverage? What
  reliability holds across longer attended runs? None authorizes a new campaign.
- **Sensitive files:** `.runtime/` (tokens, state, quota ledger), ignored unit databases,
  frozen source/results, `preserved/v0.1/`, prior failures, pre-existing notes. Read
  historical databases without runtime initialization; never expose tokens or
  rewrite evidence. The preservation receipt is [here](evidence/continuation-20261024/preservation.json).

## Continuation assessment and next step

**Ready for supervised local development**, with a fresh status/process check at
each session. Live inference, unattended operation and external integrations are
not authorized by this audit or by these notes.

Current stopping condition: offline diagnosis delivered; no fix or commit.
**One recommended next task:** calibrate the artifact-scoring contract with 12
manually labeled source/artifact/layout cases; stop at one reviewed contract and
agreed expected verdicts. Preserve historical scores. This supersedes the earlier
next-task suggestion; it does not authorize implementation or another benchmark.

Maintenance: replace the current checkpoint after verification; retain links to old
evidence and unresolved failures. Use `decisions.md` for durable choices.

## Append-only engineering changelog

- **2026-10-24 · Telemetry continuation baseline:** current root and `main` match;
  HEAD remains `a0ecdd5`. The three pre-existing untracked notes were copied to
  `.cache/continuation-20261024-original/` before edits. Source, frozen evidence,
  ignored experiment databases and runtime files were hashed (62,585 files).
  Fresh offline checks: accounting **9/9**, runtime **78/78**, legacy **28/28**.
  Logs: [continuation evidence](evidence/continuation-20261024/).
  No matching project process was found. Historical browser/live/soak claims have
  receipts but have not been repeated. Next: reconstruct stored experiment scores
  and add bounded per-attempt failure/cost accounting without new model calls.
- **2026-10-24 · Stored-evidence verification:** `scripts/verify_stored_evidence.py`
  re-scored **3,240 offline + 180 live** stored episodes and reconstructed both
  reports exactly, including scenario-cluster bootstrap intervals; **3,422**
  database integrity checks passed. C and D each completed **20/36 = 55.56%**;
  D used **216 calls (6.00/episode)** versus C's **184 (5.11/episode)**.
  These are verified stored measurements, not new live trials or an equivalence
  result. Historical total cost remains unknown. Receipt:
  [stored-evidence.json](evidence/continuation-20261024/stored-evidence.json).
  Archived v0.1's **28 tests and 450 runs** reproduced byte-identically:
  [replay log](evidence/continuation-20261024/v01-reproduction.txt).
  Next: implement and test the additive attempt ledger.
- **2026-10-24 · Telemetry verified:** additive attempt schema 1 on core schema 2;
  18 new regressions, **96 runtime + 28 legacy = 124 passing tests**. Full frozen
  offline replay also matched all 3,240 episode metrics (wall timing excluded).
  No historical costs were invented or trials replaced. Live validation of the new
  instrumentation remains unverified. Next: review this diff and its receipts.
- **2026-10-24 · Review checkpoint:** a real historical SQLite copy migrated twice
  with all existing rows preserved. Final comparison checked 62,585 original files:
  only the nine intended existing source/docs files changed; none were deleted;
  all remaining bytes, including frozen/ignored results and `.runtime`, matched.
  No project processes or listeners on 8787/8789 remained. [Validation receipt](evidence/continuation-20261024/validation.json).
  Stopped without commits/pushes. Next: review the telemetry diff and migration evidence.
- **2026-10-24 · Offline failure diagnosis:** 180 original unit results re-scored
  using frozen source; 181 distinct databases checked read-only. All 32 unsuccessful
  C/D cases traced, with 29 free of recorded call errors; exclusive mechanisms are
  23 field-layout, five message-path and four suppressed-notification cases.
  C/D pairs: 17 both pass, 13 both fail, three wins each. D's 32 net additional calls
  include useful recovery work, but establish no performance advantage or equivalence.
  Six in-memory probes expose scoring sensitivity/blind spots without changing
  historical verdicts. All 26 campaign errors and 24/844 missing-usage calls are
  accounted for separately. [Verification/preservation](evidence/failure-diagnosis-20261024T132605Z/verification.json).
  No runtime changes, new inference, benchmark or software-suite rerun. Next:
  the bounded artifact-contract calibration above; full semantic quality remains unknown.
