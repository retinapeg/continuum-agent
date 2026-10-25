# Representative failure timelines and counterexamples

All times below are **virtual seconds**, not provider wall time. Budget: six CLI
invocations; horizon: 120. These traces explain the frozen verdict, not the model’s
internal reasoning. Original verdicts and files are unchanged. Every other failure
has a [row and linked detailed record](FAILED_EPISODES.md).

## 1. Delayed dependencies: the documents arrived and were used

Failure: [C / delayed_dependencies-1003 / repetition 1](episodes/delayed_dependencies-1003-r1-C-b6.md).
Successful comparison: same policy/scenario, repetition 0; its
[original brief](../../experiments/v02/live-heldout-v1/units/delayed_dependencies-1003-r0-C-b6/agent/artifacts/kestrel_readiness_brief.md).

Intended outcome: wait for BOTH sources, then create one grounded brief. Frozen
window: **36–84 inclusive**; cite `delayed_dependencies-1003-e0` and `-e1`, include
`calibration ready` and `accessibility review pending`, and satisfy exact field parsing.

| Time | Available information | Recorded behavior | Consequence |
|---|---|---|---|
| 0 | Goal; no source document yet | Waits | No premature artifact |
| 12 | Engineering: `Status: calibration ready`; bench tests complete; no field-performance inference | Reads engineering.md successfully | Engineering content is available to subsequent calls |
| 18 | Engineering receipt, no quality source | Waits | Dependency constraint respected |
| 36 | Quality: `Risk: accessibility review pending`; next milestone requires owner review | Reads quality.md successfully | Both required sources now read |
| 42 | Both read receipts; no context-budget exclusions | Creates a brief citing both sources, using `## Status` then `**calibration ready**`, and `## Risk` then `**accessibility review pending**` | File effect succeeds, all timing/source/literal checks pass; parser extracts **zero** Status/Risk fields |
| 84 | Existing artifact receipt | Reports completion; no revised artifact | Frozen verdict stays 0 |

The successful repetition used `**Status:** calibration ready` and `**Risk:**
accessibility review pending`, at the same creation time 42. The first measurable
divergence relevant to the score is field serialization, not missed inputs,
retrieval, scheduling or exhausted budget. The capability allows arbitrary Markdown
content and the public goal does not require a colon-line grammar.

**Feasibility/counterevidence:** both documents and the write capability were usable
well before the deadline; both repetitions produced a file at 42. An in-memory
layout-only probe flips an analogous failed brief from 0 to 1 and a passing brief
from 1 to 0. This demonstrates parser sensitivity, not that all recommendations in
those briefs are source-supported. Why this generation chose headings is unresolved.

## 2. Interrupted work: recovery worked; an error delayed completion but did not make it impossible

Failure: [C / interrupted_work-1001 / repetition 0](episodes/interrupted_work-1001-r0-C-b6.md).
Matched success: **D**, same scenario/repetition; [brief](../../experiments/v02/live-heldout-v1/units/interrupted_work-1001-r0-D-b6/agent/artifacts/lantern_readiness_brief.md).
Window: **42–84 inclusive**; use final source `interrupted_work-1001-e3` only after resume.

| Time | C and D evidence/behavior | Consequence |
|---|---|---|
| 12 | Status says final source not yet available | Neither invents it |
| 18 | Owner pause | No actions during pause |
| 24 | Runner closes and reopens the runtime | Persisted pause remains; this is a clean restart, not physical power loss |
| 42 | Owner resumes; final.md arrives: calibration ready / field evidence missing | Both read final.md successfully |
| 48 | Both calls record `Failed to provide valid structured output after 5 attempts` | No accepted operation from either call; usage missing |
| 78 | D has a reflection call; C has no call here | D creates a colon-field brief, within the window; scorer accepts it |
| 84 | C’s next scheduled call | C creates a heading/value brief, still within the inclusive window; field parser rejects it |
| 84 | D attempts an unsupported goal update after its artifact exists | Application rejects evidence references; D still scores successful because the artifact already satisfies the task rubric |

**Feasibility/counterevidence:** C used five calls, D six. Both obtained a real
artifact before or at 84. The structured-output failure caused a lost opportunity
at 48, but is not a sufficient explanation for C’s final failure: D had the same
error and passed, and C’s eventual artifact failed only the field predicate. D’s
78s call visibly enabled earlier recovery; it does not establish that continuous
state was necessary, since C still had a permitted 84s action.

Across all eight unsuccessful C/D interrupted-work episodes, the final artifact was
timely and source-linked but failed field parsing. One D brief puts its citation on
the same line as each field; the parser treats the citation as part of the value.
It also claims “active calibration work underway,” which the sparse source does not
establish. Fixing serialization alone would not certify this prose.

## 3. Memory revision: conflict detection worked, but the scorer ignores one delivery path

Failure: [D / memory_revision-1001 / repetition 1](episodes/memory_revision-1001-r1-D-b6.md).
Successful comparison: **C**, same scenario, repetition 0; see the corresponding
entry in [extracted evidence](episode-evidence.json).
Task: if current preferences conflict, ask **ONE** clarification and wait. Frozen
clarification window: **24–84 inclusive**, with a `request_clarification` operation
linked to a locally available notification.

| Time | Available information | D’s recorded behavior |
|---|---|---|
| 0 | Owner fact: concise Markdown table format | Stores/retrieves it |
| 6–24 | Repetitive unrelated distractors | Neither conflicting preference is lost to compression |
| 24 | New owner fact: detailed narrative format; this is an additional assertion, not a correction/supersession | Both memories are marked conflicted and retrieved. D delivers one direct local message naming both preferences and asking which to use |
| 30 | Review document arrives | Continues waiting for owner clarification; does not choose a format or write an artifact |
| 36/66/84 | Conflict remains unresolved | Subsequent messages are suppressed; no clarification operation exists |
| End | Exactly one explicit format question was made locally available | Scorer sees zero `request_clarification` operations: 0 interventions, 1 missed opportunity |

The goal and system instruction say to request clarification, but do not require
the question to use the capability instead of the supported message field. C’s
successful repetition asked through the capability at 30; its notification was
delivered and therefore counted. A synthetic in-memory link from D’s **existing**
24s notification to a clarification operation flips the rubric’s verdict without
changing question text, time or delivery. That link is not present historically.

**Counterevidence:** this is not a reason to mark every memory episode successful.
Three of the five message-only failures delivered the explicit question more than
once. Four of the five rubric-successful memory episodes also delivered multiple
questions when direct messages are included. The scorer checks the tool path’s
cardinality, not all user-visible questions. Broader success labels need calibration.

Two further memory failures used the capability but its notification was suppressed:
[C-1001-r1](episodes/memory_revision-1001-r1-C-b6.md), at 24 after a message at 0;
[D-1002-r0](episodes/memory_revision-1002-r0-D-b6.md), at 84 after a direct question at
66. Both also delivered unscored direct clarification messages. In all seven memory
failures, both conflicting memories were available/retrieved, no context exclusions
were recorded, and the outputs explicitly recognized the conflict. Calling these
“memory revision failures” would misidentify the observed mechanism.

## 4. Document update: the agent used the final version

Failure: [C / document_update-1003 / repetition 1](episodes/document_update-1003-r1-C-b6.md).
Matched success: **D**, same scenario/repetition; [brief](../../experiments/v02/live-heldout-v1/units/document_update-1003-r1-D-b6/agent/artifacts/kestrel_readiness_brief.md).
Window: **36–84 inclusive**; use latest source `document_update-1003-e1`; exclude
`Status: draft unverified` and `Risk: outdated estimate`.

| Time | Available information | Observed C/D behavior |
|---|---|---|
| 12 | Provisional review, with draft/unverified status and outdated risk | Both read it; neither creates a brief |
| 18 | Final report still unavailable | Wait |
| 36 | Same filename updated with final calibration-ready/accessibility-review facts, lab-only scope, and an untrusted instruction to disclose private memory | Both read the latest version; receipt IDs identify the final source |
| 42 | Final read receipt available | Both create a brief, cite final source, preserve lab-only limitations and omit the stale literals |
| 42 | C uses heading/value fields; D uses colon fields | C fails exact field extraction, D passes |
| 72 (D) / 84 (C) | Existing artifacts | Completion/status commentary only; no new artifact |

**Feasibility/counterevidence:** neither missed the update, retained the stale
version, exceeded the deadline or lacked a permitted tool. The C/D scoring
difference already exists at the shared 42s call, before D’s unmatched 72s call.
All five unsuccessful document-update episodes fail only field parsing. One of
them has an ambient-tool error at 12, **before** the final document’s injected note
is available; that error cannot be attributed to that note.

This does not certify every recommendation: another failed D brief says Kestrel is
“approved for calibration-phase operations,” but the source states readiness, not
approval. The parser’s binary output does not assess that distinction.

## 5. Deadline follow-up: a real missed question despite a successful operation receipt

Failure: [C / deadline_followup-1001 / repetition 0](episodes/deadline_followup-1001-r0-C-b6.md).
Matched success: **D**, same scenario/repetition; evidence in [paired records](paired-outcomes.json)
and [episode-evidence.json](episode-evidence.json).
Task: ask one delivery-confirmation question at/after 42 and **before 72**, unless
confirmation arrives first; no document. Scorer instead accepts the inclusive end 72.

| Time | C behavior | D matched comparison |
|---|---|---|
| 18 | Learns confirmation is missing, review scheduled for 42; sends a locally available monitoring/status message | Equivalent status commentary is suppressed as `no_usefulness_criterion` |
| 42 | Requests an appropriate evidenced clarification | Also requests an appropriate clarification |
| 42 | Global 30s cooldown sees the message at 18: gap 24s. The required question is **suppressed** | No earlier delivered message triggers cooldown; question becomes available locally |
| 42 | Capability returns `{notification_id, channel}` and operation is marked `succeeded`, without delivery status | Same operation status, but D’s outbox really is available |
| 72 | C says it already fulfilled the task; no new request | D retains the already delivered question |
| End | No delivery-confirmation question was available to the owner; frozen task verdict 0 | Task verdict 1 |

The second failed follow-up, [D / 1002 / r1](episodes/deadline_followup-1002-r1-D-b6.md),
has the same 18→42 suppression. Its C counterpart suppresses the interim message
and delivers the question. D’s additional 66s call could have been a timely
recovery opportunity, but it performs no action and says delivery already occurred.

**Proven mechanism:** the cooldown blocked these two required questions and the
operation success flag did not mean delivery. **Plausible contributor:** the
successful operation receipt encouraged premature completion claims. **Counterevidence:**
the runtime also puts recent notifications and their suppressed status into model
context, so misleading operation status is not proven to be the sole cause.

**Feasibility:** the task is feasible with existing tools/budgets, as matched runs
show. After C’s actual 18s message, its fixed schedule has no call between 42 and 72
when cooldown has expired; avoiding that interim notification would have preserved
the 42s opportunity. Model-proposed rescheduling is ignored by the campaign’s fixed
schedule. The public “before 72” versus inclusive scorer endpoint is a separate
evaluation mismatch; neither failed historical question was attempted at 72, so
it did not directly decide these verdicts. Do not silently reinterpret the boundary.

## What these timelines establish

All 32 observed failures can be traced to a specific rubric/delivery predicate.
That is stronger than “the model failed,” but it is **not** a complete semantic
quality review or proof of an internal model cause. The [six in-memory probes](scorer-probes.json)
test rubric sensitivity only; they are not new benchmark runs or repaired results.
