# CONTINUUM — decisions

## D001 · Accepted · Repository-specific, attended continuation (2026-10-24)

**Accepted — current user scope.** Work only in this checkout, one branch and writer
at a time. Do not restart the build, mix sibling repositories, run unattended, launch
background work, create worktrees, commit or push without an explicit new request.
Reason: preserve ownership of code, evidence and running processes across sessions.
Evidence: [AGENTS.md](AGENTS.md), current user instructions. Parallel writers and
worktrees were rejected by scope; slower serial work is accepted. Revisit only on
explicit owner authorization with one task and stopping condition.

## D002 · Accepted · Lightweight persistent context (2026-10-24)

**Accepted — this audit.** `AGENTS.md` directs future sessions to `learning.md`
(verified state, evidence, blockers, next step) and this file (choices and rationale).
Update them at verified milestones and handoff, not after every command. They are
local repository documents, not runtime memory, a scheduler or authorization.
Evidence: [learning.md](learning.md) and [handoff](MORNING_REPORT.md). A separate
knowledge service would add scope and maintenance. Manual freshness checks remain
necessary; revisit if these short files can no longer provide reliable handoffs.

## D003 · Accepted · Preserve v0.1 and frozen evidence (2026-10-24)

**Retained project contract; reaffirmed by user.** Inspect edits before writing.
Preserve prior successes and failures, raw results and frozen sources. Use a new
trial ID for fresh evaluation. Unknown inference outcomes require reconciliation,
not blind replay. Source/results must not be rewritten to match a preferred claim.
Keep v0.1 interfaces and stock outputs compatible. Evidence: [archive](preserved/v0.1/RESTORE.md),
[fresh byte-identical replay](evidence/continuation-20261024/v01-reproduction.txt).
Rewriting old records to repair scoring/accounting was rejected; known defects stay
visible. Revisit implementations only under a new version/trial ID with comparisons.

## D004 · Accepted · Verification and inference boundary (2026-10-24)

**Retained implementation boundary.** Keep fixture tests distinct from live evidence.
Codex stays disabled until isolation is demonstrated. C/D's historical tie does not
prove added value or equivalence. Existing CLI login does not authorize new inference,
external disclosure, API billing, integrations or automatic improvement promotion.
Evidence: [MODEL_SUPPORT.md](MODEL_SUPPORT.md), [SECURITY.md](SECURITY.md),
`tests_runtime/test_telemetry.py`. No global configuration, sibling connections,
real user data, external requests or billing are authorized. Local fixture tests
may create transient joined HTTP/process fixtures. We accept unavailable live
features instead of weakening isolation. Revisit Codex only after demonstrated
tool isolation **and** explicit live authorization; integrations require separate scope.

## D005 · Accepted · SQLite remains the persistence foundation (2026-10-24)

Keep core schema 2 and its `calls` layout. Add `provider_attempts` and
`meta.attempt_schema=1` in one transaction. Existing databases remain readable;
the migration does not backfill historical attempts or edit old calls/events.
Evidence: [database](continuum/runtime/database.py), [telemetry](continuum/runtime/telemetry.py),
[migration/recovery regressions](tests_runtime/test_telemetry.py).
An actual historical unit was also migrated twice in a disposable copy, with every
existing table row unchanged: [migration receipt](evidence/continuation-20261024/migration-copy.json).
An altered `calls` layout risks older readers/positional inserts; a new telemetry
service/database would add unnecessary dependencies. Accepted tradeoff: old data
has explicit missing coverage. Revisit storage only when measured requirements
exceed SQLite's local transactional model. Never migrate frozen originals for analysis.

## D006 · Accepted · Reliability and evidence before feature complexity (2026-10-24)

Preserve current policies; additional continuous-state complexity must show a
measurable benefit at comparable budgets before expansion. Verified C/D completion
is 55.56% each, with D using more calls; the confidence interval does not establish
equivalence. Evidence: [reconstructed results](evidence/continuation-20261024/stored-evidence.json).
Adding dynamics now would have weak justification. Accepted limitation: narrow
synthetic tasks cannot settle general usefulness. Revisit after independently
reviewed, broader held-out evidence; no consciousness inference follows.

## D007 · Accepted · Attempts and outcomes have separate accounting (2026-10-24)

One logical deliberation can contain multiple provider attempts through the existing
known-unsent router fallback. Persist stable attempt/trace IDs and retry links before
invocation; persist success/error usage before accepting effects. Do not add retries.
Recovery finalizes unfinished attempts as unknown and pauses; replayed terminal
receipts cannot change totals. `status()['telemetry']` counts unique attempt rows,
with known subtotals, coverage counts and null incomplete totals. Logical `calls`
and events remain compatibility/audit views, not extra amounts to sum.

Evidence: [implementation](continuum/runtime/telemetry.py), [18 offline regressions](tests_runtime/test_telemetry.py).
Counting receipt events or parsing error strings was rejected: duplicates and
unstable/content-bearing messages weaken attribution. Use fixed failure codes and
allowlisted numeric metadata; preserve approved action content in its existing store.
Accepted limitations: historical usage cannot be recovered, estimates are not invoices,
and CLI internal retries are opaque; `cli_num_turns` must not be called a retry count.
Revisit when a provider exposes trustworthy per-request identities/usage, or an
authorized live check finds an adapter mismatch. No new instrumentation is live-verified yet.

## D008 · Deferred / supersedes earlier pending choice (2026-10-24)

The earlier notes-only audit selected no feature and suggested a fixture walkthrough.
The current owner request supersedes that suggestion with a bounded telemetry change
and review checkpoint. The walkthrough remains deferred. Human prose review, longer
reliability evaluation, wider workloads, live adapter validation, integrations and
automatic improvement promotion remain separate future decisions. Choose one next
task and stopping condition explicitly; a completed test suite does not authorize it.
