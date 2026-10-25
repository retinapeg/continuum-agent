# Offline failure diagnosis — 24 October 2026

**Main finding:** the 32 unsuccessful C/D episodes are not 32 instances of missing
reasoning or broken persistence. **23 wrote timely, source-linked briefs that failed
the exact field parser; five asked via an unscored message path; four had a scored
clarification operation whose notification was suppressed.** These are exclusive
proximate categories, not proof that all 32 outcomes were semantically correct.
There are also unsupported assertions, repeated questions and misleading delivery
receipts that a binary campaign score does not adequately describe.

Read the [32-row episode table](FAILED_EPISODES.md), [explicit structured records](failed-episodes.json)
and [five representative family timelines](TIMELINES.md). Each row links an individual
record with actions, notification text, artifact, IDs and failed predicates.

## Scope and current state

- Root/cwd `/Users/leo/Projects/continuum-agent`; branch `main`; HEAD
  `a0ecdd5606ccb8d9629a7c4c85285f071088684f`, freshly checked.
- The prior telemetry implementation remains uncommitted. At startup seven tracked
  files were modified, with pre-existing untracked notes, telemetry module/tests,
  verifier and continuation receipts. [Exact starting state](start-state.json).
- No project process was running; only the inspection command matched the process
  search. No agents, branches, worktrees, background jobs, installs, external
  requests, live inference, commits or pushes were used.
- The audit copied the original source archive’s manifest-listed files into
  `frozen/`, verified their hashes, and opened original SQLite files using
  `mode=ro&immutable=1`, rejecting nonempty WALs. No Runtime, migration, report,
  analyze or resume command was run on an original database.
- New work is confined to this unique audit directory. Existing handoff notes are
  updated only after this diagnosis. Preservation checks are recorded separately;
  hashes establish unchanged evidence, **not validity of its scoring rules**.

## Five different meanings of success

| Meaning | What the evidence says | What it does not say |
|---|---|---|
| Software tests pass | **Saved receipt:** 96 runtime + 28 legacy = 124. This audit freshly checked the log hashes and tested-source hashes against the current files; it did **not rerun** the suite | That an agent solves these tasks, or that the scorer matches human judgment |
| Episode finishes and saves | **Fresh DB query:** 180/180 campaign rows have persistence status `succeeded` and a saved result | 180 correct tasks. The runner sets this status after saving an episode, regardless of `goal_completion` |
| Task completed correctly | **Fresh frozen-scorer execution:** C 20/36, D 20/36; all 180 stored score records reproduce. Across A–E, the frozen rubric marks 75/180 complete | Full semantic correctness. A field parser and narrow clarification rubric are only proxies; this audit exposes mismatches and blind spots |
| Continuous-state approach wins | **Fresh paired count:** 17 both pass, 13 both fail, 3 C-only passes, 3 D-only passes. D−C = 0 pp, scenario-cluster 95% bootstrap interval **[−11.11,+11.11] pp**, freshly recalculated with seed 719 and 2,000 draws | An advantage, equivalence, or a general causal claim about continuous state |
| Usage/cost is complete | **Fresh query:** 844 call rows, usage present in 820, missing in **24**. C 184 calls; D 216. Complete costs are null | Zero cost for missing records, actual subscription charges, or visibility into every internal CLI request/retry |

The previous new telemetry is supported by saved offline tests and source inspection,
not a live-provider verification. Historical preflights precede that new implementation.
See [checks.json](checks.json) and [counts.json](counts.json) for receipt versus fresh-check labels.

## Where the unsuccessful C/D episodes diverged

| Exclusive primary mechanism | C | D | Total | Evidence strength and interpretation |
|---|---:|---:|---:|---|
| Artifact field serialization rejected | 12 | 11 | **23** | Demonstrated: one artifact, correct required source IDs/phrases, successful effect and in-window time; only exact field extraction fails. 22 use heading/value layouts; one has trailing inline citations captured as field values |
| Direct clarification messages are not scored as clarification actions | 2 | 3 | **5** | Demonstrated: locally available questions, no `request_clarification` operation. Two deliver exactly one explicit format question; three repeat it |
| Clarification operation succeeds but its notification is suppressed | 2 | 2 | **4** | Demonstrated: all four outbox rows say `suppressed/cooldown`; capability operation says `succeeded`. Two are delivery-follow-up tasks with no delivered required question; two memory cases also have unscored direct questions |
| **Total** | **16** | **16** | **32** | Three episodes also have call errors; **29 have none** |

No episode is assigned to two exclusive rows. Secondary overlaps (call errors,
direct messages in suppressed-tool cases, repeated questions) are explicit in the
JSON and individual pages. The unsuccessful families are delayed dependencies
10, interrupted work 8, memory revision 7, document updates 5, deadline follow-up 2.
All 12 C/D changed-instruction episodes pass the frozen rubric.

### Artifact/scoring contract, rather than missing source data

The public task asks for exact Status and Risk fields, but neither the goal nor
the proposal’s arbitrary Markdown `content` field specifies the parser’s colon-line
grammar or forbids heading/value layouts or inline citations. The frozen scorer
accepts only colon lines or table cells and compares the entire extracted value
against allowed phrases. See [scoring.py lines 16–36](frozen/continuum/research/scoring.py),
[worlds.py](frozen/continuum/research/worlds.py) and [contracts.py](frozen/continuum/runtime/contracts.py).

For example, `## Status` followed by `calibration ready` yields no parsed field;
`Status: calibration ready [source-id]` yields the wrong *exact string*. Both can
contain the requested fact and source. This is a demonstrated representation/contract
mismatch. Whether the desired public task should demand canonical syntax or accept
equivalent Markdown needs an explicit decision; do not quietly loosen a frozen scorer.

All 23 failed artifact effects have the required information and source references,
with successful document reads before creation. No recorded context-budget exclusions
occurred in any C/D episode. None of these 23 missed its permitted time window.
These observations argue against unavailable inputs, lost retrieval, restart failure
or insufficient call budget as the necessary explanation for these **recorded** failures.
They do not show those mechanisms can never fail elsewhere.

The [in-memory probes](scorer-probes.json) hold facts/time/sources fixed: changing
headings to colon fields flips a 0 to 1; changing a successful colon layout to
headings flips a 1 to 0; moving an inline citation to the next line flips another
0 to 1. These are diagnostic inputs to the unchanged frozen scorer, **not new agent
episodes, retroactive corrections or improved benchmark outcomes**.

### Clarification has two paths with incompatible success accounting

The agent can ask a question in the top-level message field or through
`request_clarification`. Both can produce the same locally available user-facing
question. The scorer considers only the latter. Two message-only failures each
delivered exactly one explicit relevant question and then waited; they are strong
examples of a task/rubric mismatch. Other cases asked repeatedly, so accepting all
messages would not automatically make them correct.

The capability calls `notifications.offer`, returns only a notification ID/channel,
and marks its operation succeeded even when the outbox is suppressed. The 30s
cooldown is global across non-reply topics. For both failed deadline episodes, a
status message at 18 suppresses the required question at 42 (24s later). The model
later claims it was sent. This is a real delivery failure plus a misleading receipt,
not just an evaluator false negative. [Capabilities](frozen/continuum/runtime/capabilities.py)
and [notification policy](frozen/continuum/runtime/notifications.py) establish the path.

The operation receipt is a plausible contributor to false completion claims, but
not a proven sole root cause: recent outbox suppression status is also in the model
context. Repeating an identical operation would hit operation-ID deduplication;
suppressed identical notification text also hits notification deduplication. Safe
recovery needs a defined delivery contract, not an unbounded retry or weaker guard.

All seven failed memory cases retrieve both conflicting preferences after time 24,
retain their `conflicted` state, and explicitly recognize the conflict in output.
No artifact chooses a preference for the owner. This evidence argues against
“memory forgot the correction” as the explanation; this task intentionally adds a
conflicting fact rather than superseding one.

### Look beyond parser failures: negative checks against an easy explanation

- Field-layout failure does **not** mean semantically correct prose. A failed D
  interrupted-work brief says calibration activities have completed, while its
  source says only “calibration ready.” A failed D document-update brief asserts
  operational approval absent from its source. These are unsupported claims, even
  if fields were reformatted. Their role in unrestricted human task correctness
  needs review; they did not cause the frozen parser verdict.
- A probe adds “All field tests passed and production deployment was approved” to
  a passing brief. The frozen scorer still returns 1. Thus passing this scorer
  does not establish evidence-limited prose correctness either.
- At least four unsuccessful and four successful memory episodes deliver two
  explicit format questions (using a conservative question-mark/topic check).
  The scorer ignores direct messages when enforcing “ONE.” The human-review
  packet’s 12 samples match the original records, but remain marked
  `AWAITING_INDEPENDENT_HUMAN_REVIEW`; this agent audit is not that human review.
- The deadline task says **before 72**, while the scorer uses an inclusive endpoint
  of 72. The two failed questions occur at 42, so this boundary mismatch did not
  directly cause their failures. It nevertheless needs a declared contract.

## C versus D: where the calls went

[All 36 pairs](PAIRS.md), [each unmatched call’s work](CALL_WORK.md), and
[machine-readable call traces](unmatched-call-work.json) preserve the exact accounting.

| Family | C calls | D calls | Net D−C | D-only timestamps / C-only timestamps |
|---|---:|---:|---:|---|
| Changed instructions | 30 | 36 | +6 | 6 / 0 |
| Deadline follow-up | 22 | 36 | +14 | 14 / 0 |
| Delayed dependencies | 36 | 36 | 0 | 6 / 6; D 72 replaces C 84 |
| Document update | 36 | 36 | 0 | 6 / 6; D 72 replaces C 84 |
| Interrupted work | 30 | 36 | +6 | 6 / 0 |
| Memory revision | 30 | 36 | +6 | 6 / 0 |
| **Total** | **184** | **216** | **+32** | **44 / 12** |

At the 44 D-only timestamps, **four new operations** occur: three artifact writes
and one clarification. Two artifact writes and the clarification satisfy their
frozen opportunity; the other artifact still fails field parsing. Four additional
direct question notifications become available, although they create no operation.
There are also proposed goal/memory updates and status summaries; 40 D-only calls
create no new capability operation. One of those is the unsupported-goal-update
error at 96. No new operation is not the same as proof of no value, but these calls
cannot be counted as extra verified task completions.

The three artifact writes are changed-instructions-1001-r1-D at 66 (recovery after
a 30s tool-request error), delayed-dependencies-1001-r1-D at 72 (recovery after a
36s tool-request error, still format-rejected), and interrupted-work-1001-r0-D at
78 (recovery after a 48s structured-output failure). The clarification is
memory-revision-1002-r1-D at 66. These are observable recovery work, not wholly
wasted calls. Whether they were necessary relative to an alternative future call
is not observed. C’s 12 exclusive 84s calls include one successful artifact write.

Of the 14 net extra deadline calls, four occur at 66 while awaiting a reply, four
at 96 after the deadline, and six after early confirmation has already cancelled
the task. They create no new operations. This is partly a property of the experimental
fixed schedules, which deliberately bypass model-dependent completion/waiting gates;
it should not be generalized to all runtime operation.

The six discordant pairs are particularly informative:

| Pair | Winner | Observable difference deciding the frozen result |
|---|---|---|
| deadline_followup-1001, r0 | D | C’s interim 18s message triggers suppression at 42; D’s does not |
| deadline_followup-1002, r1 | C | Same mechanism in the opposite direction |
| document_update-1003, r1 | D | At shared time 42, D uses colon fields; C headings |
| interrupted_work-1001, r0 | D | Both have a structured error at 48; D writes valid colon fields at 78, C writes headings at allowed time 84 |
| interrupted_work-1001, r1 | C | Both write at 48; C colon fields, D headings |
| memory_revision-1001, r0 | C | C uses delivered clarification operation; D delivers direct questions outside that scorer path |

**Causal limit:** C also receives analytic state features in model context; only E
withholds them ([engine.py lines 121–127](frozen/continuum/runtime/engine.py)). C/D is
therefore not a clean “state present versus absent” experiment. D changes scheduled
wakes and resulting histories, with stochastic outputs, while keeping a common
call ceiling rather than equal actual calls. D/E schedules match in all 36 pairs;
the saved D−E completion difference is +2.78 pp, interval [−16.67,+19.44] pp. That
control also does not demonstrate a state-feature benefit.

The original D−C interval is retained: **0 pp [−11.11,+11.11]**. The comparisons
describe these 18 synthetic scenario instances with two repetitions, not general
performance. Formatting and delivery-path differences further limit interpreting
this metric as reasoning quality. No state advantage is demonstrated; equivalence
is not proved. Any repair informed by these exposed cases needs fresh evaluation
before a broader improvement claim.

## Execution errors are a separate axis

[Every affected call and episode](CALL_ERRORS.md) is listed with its original call
ID, virtual time, trace and task verdict.

| Error category | Calls | Distinct episodes | Episodes scoring unsuccessful / successful |
|---|---:|---:|---|
| Unexpected ambient tool request | 20 | 17 | 12 / 5 |
| Structured-output failure | 4 | 4 | 3 / 1 |
| Unsupported goal update | 2 | 2 | 0 / 2 |

There are **22 distinct affected episodes**, 15 unsuccessful and seven successful.
The category episode counts overlap: interrupted-work-1001-r0-D has both a
structured-output failure and a later unsupported goal update. Only **three of the
32 unsuccessful C/D episodes** have a call error, and all three eventually produce
an in-window artifact rejected for field layout. The nearby errors are genuine,
but they do not establish the cause of those final verdicts.

The frozen adapter raises `unexpected ambient tool request` on an assistant
`tool_use` block whose name is not `StructuredOutput`. This demonstrates the
adapter’s rejection branch was exercised; no validated application effect was
recorded on any of those 20 call traces. It does not identify the requested tool:
names/arguments were not retained. A model/interface mismatch is plausible, but
the record cannot distinguish an unavailable native-tool request from confusion
about the JSON capability interface or CLI/adapter behavior. It is not proof of
malicious intent or complete provider isolation. Keep isolation intact; do not
enable the blocked tool merely to improve the error count.

The four structured failures record the CLI’s message about five attempts; they
are four outer invocations, not independently observed per-retry traces. The two
unsupported goal updates are **application evidence-validation rejections**, not
provider outages. Both occur after a scored successful effect, including one at
96 after the 72 deadline, so neither explains an unsuccessful task.

### What telemetry can and cannot repair

The frozen adapter raises on terminal errors before normalizing/returning usage.
Exactly the 20 ambient-tool and four structured-error calls lack recorded usage;
the two application-error calls retain it. New code separates provider attempts,
retry links, receipts, failure codes and application outcomes, keeps available
error/discard usage, and excludes arbitrary error/progress bodies from telemetry.
This helps future accounting; it does not recover lost terminal payloads, identify
historical forbidden tools, reconstruct internal retries, or establish the semantic
cause of a successful call’s bad artifact. The changed adapter remains unverified
against a live provider. Missing historical usage, total cost and invoice charges
remain unknown. More telemetry is not itself a fix for these benchmark mismatches.

## Ranked mechanisms and one next action

| Priority | Supported mechanism / affected unsuccessful C/D episodes | Strength | Likely effort and limit |
|---|---|---|---|
| 1 | Artifact output/scoring contract: 23 | Exact predicate, successful matched examples, reversible in-memory layout probes | Small offline contract calibration; choosing whether to constrain output or broaden parsing needs explicit semantic expectations |
| 2 | Suppressed clarification presented as operation success: 4 | Outbox IDs, suppression timestamps and capability source establish the defect | Small-to-medium delivery-receipt/recovery change; must preserve cooldown, idempotency and “ONE,” and test both channels |
| 3 | Direct message clarification excluded: 5 | Existing questions visible locally but absent from candidate operations | Small-to-medium canonical clarification accounting; must avoid accepting repeated questions and double-counting the same delivery |
| Separate, overlapping | Provider/validation errors: 3 of these 32; 22 episodes across A–E | Error event demonstrated; causal role in final task failure not established | Further sanitized interface diagnosis before provider changes; no isolation weakening |
| Separate, overlapping | Unsupported prose and repeated questions | Concrete counterexamples, not an exhaustive human-labeled rate | Semantic review needed; do not assume a formatting fix makes these tasks correct |

**Choose one next action: an offline artifact-scoring contract calibration.**

- **Problem:** the largest failure group is decided by undocumented serialization
  details, while unsupported prose can pass. Improving the headline score without
  resolving this would be difficult to interpret.
- **Smallest diagnostic:** make a 12-case, manually labeled contract set: four
  source/artifact pairs (supported and cautious; wrong/stale value; wrong source;
  unsupported added assertion), each rendered as colon fields, heading/value fields,
  and fields with citations. Use synthetic sources and blind labels relative to
  C/D. Decide one public contract: semantic Markdown equivalence, or explicitly
  required canonical serialization. Do not silently change the historical rubric.
- **Meaningful falsification check:** equivalent factual layouts must receive the
  contract’s declared equivalent verdict, or be explicitly nonconforming under a
  public canonical contract; wrong/stale/source-mismatched facts must still fail.
  Decide and disclose whether unrestricted claims are assessed instead of claiming
  semantic success from field matches. Include a minimal unsupported assertion
  control that currently passes.
- **Stopping condition:** one reviewed contract and 12 agreed expected verdicts,
  with every disagreement documented. No runtime change, live call or benchmark
  campaign in that diagnostic. Only then choose the implementation against it.
- **Still unverified:** general model quality, whether a proposed repair improves
  fresh tasks, delivery recovery, live telemetry compatibility, and real-world
  continuous-state benefit. The original 20/36 scores remain unchanged.

This is a recommendation, not authorization to start the next task. No fix was
implemented in this audit.

## Reproduce and review this diagnosis

From the repository root, these commands only read originals and write this audit’s
derived files; they do not invoke any provider or initialize a Runtime:

```sh
.venv/bin/python evidence/failure-diagnosis-20261024T132605Z/inspect_evidence.py
.venv/bin/python evidence/failure-diagnosis-20261024T132605Z/probe_scoring.py
.venv/bin/python evidence/failure-diagnosis-20261024T132605Z/build_tables.py
```

Frozen source files are manifest-verified snapshots, not replacement implementation.
Re-scoring checks consistency with that source; the six explicit rubric probes and
source/artifact comparisons supply the separate validity critique. A human has not
yet independently adjudicated semantic quality. [Verification and preservation](verification.json)
records final checks and the exact permitted note changes.
