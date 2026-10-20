# Test report — 20 October 2026

The final local runtime suite passed **78 tests** in **2.101 seconds**. The separately preserved v0.1 suite passed **28 tests** in **0.336 seconds**, and all three original 450-run benchmark files reproduced byte-identically. These are distinct suites: **106 passing tests total**, not 106 live model trials.

| Check | Actual result | Evidence |
|---|---|---|
| Runtime, state, memory, security, scorer and HTTP tests | 78/78 passed | [Full log](evidence/build/final-runtime-tests.txt) |
| Archived v0.1 tests and exact benchmark replay | 28/28; runs.csv, summary.json, manifest.json identical | [Replay log](evidence/build/v01-reproduction.txt) |
| Frozen development offline-v2 replay | All 3,240 per-unit metrics identical, wall timing excluded | [Replay log](evidence/build/offline-v2-reproduction.txt) |
| Final frozen offline replay | All 3,240 per-unit metrics identical; elapsed wall timing excluded | [Final replay log](evidence/build/offline-final-reproduction.txt) |
| Final offline matrix | 3,240/3,240 completed; D/E call times identical | [Analysis](experiments/v02/offline-final-v2/ANALYSIS.md) |
| Chromium desktop/mobile UI | Passed; no page errors or mobile overflow | [Browser receipt](evidence/build/browser-smoke.json) |
| Final real wall-clock soak | 600.013 seconds; 30 fixture deliberations; shutdown joined and stop retained | [Final soak receipt](evidence/build/soak-final.json) |
| Earlier real wall-clock fixture soak | 120.035 seconds; pause, resume, stop, joined shutdown; stop retained after reopen | [Soak receipt](evidence/build/soak.json) |
| Real Claude runtime demo | Three successful model calls; source-backed artifact and local clarification, 40.215 seconds | [Demo receipt](experiments/v02/live-runtime-demo-v1/receipt.json) |
| Frozen live campaign | 180/180 episodes; 844 attempted CLI invocations; 36/36 D/E schedules match | [Analysis](experiments/v02/live-heldout-v1/ANALYSIS.md) |
| Post-campaign live adapter check | Exact requested/reported model; 5.727 seconds; no cleanup warnings | [Preflight](evidence/build/post-campaign-preflight.json) |
| Completed resume after source change | Zero new calls; raw results hash unchanged | [Resume receipt](evidence/build/completed-resume.json) |
| Integration envelope HTTP adapter | Real local stub; duplicate delivery/cursor tested | `tests_runtime/test_contract_http.py` |
| Independent scientific-method review | Final denominator blocker resolved; no remaining material protocol blocker | [Review resolution](evidence/baseline-check/scientific-review-resolution.json) |

## Failure and adversarial coverage

- Analytical dynamics: semigroup consistency, zero elapsed time, long gaps, bounds, nonfinite/reversed clocks and restart wall-clock clamping. Discrete state and timestamp-only analytical updates are explicit controls.
- Durable execution: exclusive ownership, duplicate/conflicting/out-of-order observations, claim/effect/receipt crash points, persisted pending proposal, completed activation deduplication, stale ownership recovery and unknown inference recovery. Clean reopen and simulated crash injection are distinguished.
- Controls: pause/resume/stop persistence, cancellation during deliberation, revocation during a delayed tool, suppressed historical replies, quiet hours, interruption budgets, duplicate messages and muted topics.
- Memory: confirmed versus proposed assertions, correction history, conflicts, private exclusions, retrieval-budget receipts, duplicate assertion forgetting, derived-context purge and stale read-cache handling.
- Provider boundaries: nonblocking stdin deadline, total output bound, EOF without newline, invalid stream object, invalid/nonfinite proposals, subscription enforcement/revalidation, missing primary usage with available per-model telemetry, cleanup permission errors and Codex fail-closed.
- Security: traversal/symlink/unannounced paths, fake source IDs, injected permissions, authenticated same-origin controls, private memory API isolation, repository boundaries, malformed goals and secret-pattern redaction before persistence.
- Failure handling: simulated disk-full artifact write, SQLite query-only write failure, provider outcome-unknown pause and no blind resend. These are controlled fault injections, not physical power-loss or disk-exhaustion testing.
- Scoring: hand-calculated positive, negative, stale, duplicate and failed effects; structural table format; stale bold/table claims; failed-episode recall denominator; unknown action/cost telemetry stays null.
- Scientific isolation: public-prefix schedule ignores private labels; D/E schedules match; model waiting/completion cannot suppress explicit experimental wakes. Context compression removes whole records and logs exclusions.

The browser smoke exercises authenticated connection, goal creation, owner chat history, artifact reading, confirmed memory, correction with supersession history, pause/resume and a 390-pixel viewport. It uses Chromium, not a mocked DOM. Screenshot evidence is [desktop](evidence/build/dashboard-desktop.png) and [mobile](evidence/build/dashboard-mobile.png).

## Regressions found and repaired

1. A read receipt did not reactivate a waiting goal. Successful read/search/event tools now persist an observation; a regression test verifies continuation.
2. Stream fragments could bypass output accounting or block on stdin. I/O is nonblocking with combined byte bounds and deadlines; partial secrets are not logged.
3. A CLI auxiliary model was initially mistaken for a main-model switch. Primary identity and aggregate usage are now separate; the original failed preflight is retained.
4. Cancellation/forget races could preserve stale responses. Epoch checks and serialized apply/forget paths prevent stale proposal persistence/effects.
5. A model-dependent waiting gate weakened the schedule ablation. Explicit experiment schedules now bypass that gate.
6. A stray pipe could satisfy a table requirement, and table-form stale claims escaped the stale counter. Both have explicit regression tests.
7. Failed infrastructure episodes could disappear from pooled opportunity denominators. Their opportunities remain; unavailable action counts and incomplete cost totals stay unknown.
8. Terminal-error and discarded-response usage was lost. After the frozen campaign finished, accounting was separated from proposal acceptance, completed-only resume was permitted after source drift, and campaign database connections were explicitly closed. Nine new regressions pass. Historical telemetry remains incomplete; no trial was backfilled.

The first pilot's smaller output bound caused real failures; those runs remain unchanged. The final bound is one million combined stdout/stderr bytes. Token requests and byte limits are separate controls.

## What these checks do not establish

No production-readiness, multi-user isolation, general semantic factuality, multi-day reliability, actual cross-project integration or exactly-once external effects is claimed. Codex inference remains disabled. The integration stub is not A2A/MCP. No generated executable code capability exists; a subprocess would not itself be a security sandbox. Human-review packets are prepared but not yet reviewed by a human. Live matrix outcomes and failure taxonomy belong in [MORNING_REPORT.md](MORNING_REPORT.md), not the unit-test count.

Run the exact commands in [README.md](README.md). Source/test hashes and uncaptured-build-usage reasons are in `evidence/build/milestone-*.json`. Parent coding-session token usage was not available and was not invented.
