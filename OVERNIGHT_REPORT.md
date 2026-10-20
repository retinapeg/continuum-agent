# CONTINUUM v0.1 execution report

Date: **2026-10-20**. Repository: `/Users/leo/Projects/continuum-agent`. Interpreter: **Python 3.13.15**.

## Scope and stopping condition

Built v0.1 in the initially empty, clean repository on the existing `main` branch. No new branch, worktree, subagent, commit, push, external API call, message, payment, or transaction was created. No dependencies were downloaded. The work is local and uncommitted. No ongoing agent process or scheduled background task was installed.

The requested stopping condition is met: implementation, deterministic benchmark evidence, tests, recruiter-facing README, and explicitly unimplemented future-research proposals are present. The report title does not imply that an agent ran unattended overnight.

## Delivered

- Standard-library Python package and runnable CLI.
- SQLite event ingestion, facts with revision/expiry, pending/completed/cancelled tasks, continuous-state checkpoints, and decision/action receipts.
- Exact exponential state decay with event impulses and a state-dependent adaptive idle timer.
- Reactive, periodic, and adaptive clocks using the same memory, observations, and action policy.
- Five deterministic scenario regimes, including cancellation, irrelevant events, and misleading readiness estimates.
- Completion, memory, precision/recall, latency, interruptions, and synthetic cost accounting.
- Per-run CSV, aggregate JSON, paired seed-bootstrap intervals, and SHA-256 provenance.
- README with architecture, runnable commands, measured outcomes, limitations, and demonstrated engineering skills.
- `FUTURE_RESEARCH.md` covering LLMs, A2A/MCP, HTTP 402/x402, privacy-preserving matchmaking, causal ablations, and operational recovery; all unimplemented.

## Actual verification

| Check | Observed result |
|---|---|
| `python3 -m unittest discover -s tests -v` | **28 passed**, recorded runtime **0.346 s**; full output in `results/tests.txt` |
| `python3 -m continuum benchmark --seeds 30 --output results` | **450 runs** across 150 matched environments |
| Independent second full benchmark into a temporary output directory | `runs.csv`, `summary.json`, and `manifest.json` were **byte-identical** |
| Manifest verification | Every recorded Python source/test hash and CSV/summary hash matched |
| Adaptive CLI demo, seed 0, quiet deadlines | 10/10 feasible goals, 10 attempts, 37 decisions, 13.95 cost units, zero successful-task latency |
| Periodic CLI demo on the same scenario | Exited successfully and returned periodic-policy results |
| Saved SQLite demo | `PRAGMA integrity_check` returned `ok`; 10 action receipts found |
| Repeat CLI demo against nonempty database | Correctly rejected, exit code **2**, with an empty-database requirement |
| `python3 -m compileall -q continuum tests` | Passed |
| `git diff --check` | Passed for tracked diff; new files were still untracked |

The reliability suite includes transaction rollback, clean reopen, monotonic time across actions and observations, conflicting and repeated event IDs, cancellation-before-action ordering, cooldown, exact decay, hand-calculated metrics, and a case where periodic precision beats adaptive precision. No test establishes resilience to operating-system crashes, concurrent writers, or real tool failures.

## Benchmark outcome

Arithmetic means over 30 seeds × 5 regimes per policy:

| Policy | Completion / recall | Memory accuracy | Precision | Successful latency | Interruptions | Cost units |
|---|---:|---:|---:|---:|---:|---:|
| Reactive | 82.93% | 100% | 92.36% | 1.415 | 8.83 | 13.56 |
| Periodic | 73.58% | 100% | 90.20% | 1.789 | 8.03 | 10.50 |
| Adaptive | 94.21% | 100% | 88.23% | 0.227 | 10.85 | 16.63 |

Adaptive minus reactive: **+11.28 percentage points completion**, 95% paired seed-bootstrap interval **[9.58, 12.84]**. Additional cost: **+3.07 units**, interval **[2.92, 3.22]**.

Adaptive minus periodic: **+20.63 percentage points completion**, interval **[18.22, 23.09]**. Additional cost: **+6.13 units**, interval **[5.87, 6.42]**.

These intervals resample seed-level differences averaged across the fixed five regimes, preserving pairing. They quantify only variation under this generator, not uncertainty about real-world performance. Cost is an arbitrary declared formula, not actual API spending.

Counterevidence: all policies complete 100% of wide-window goals; periodic is cheapest there. Reactive ties adaptive completion in event-aligned and noisy regimes. Under misleading estimates, adaptive intervention precision drops to 41.14%, versus 61.79% reactive and 51.00% periodic. Adaptive is not a universal winner.

## Interpretation and limitations

The implemented comparison supports a narrow conclusion: an adaptive timer improves completion in these selected synthetic timing environments, with a measurable cost and false-intervention trade-off. It does **not** answer the broad intelligence question.

All policies have persistent memory and observe every event, including while the periodic agent is asleep. Consequently, perfect shared memory accuracy is a control check, not evidence that adaptive agents remember better. Confidence decay is exposed but not used for action selection. A readiness-only timer ablation is needed to establish whether activation dynamics add value.

The 120-unit scenarios contain independent single-step goals, not genuine multi-day dependent plans. Scheduling is integer-resolution even though state transitions support fractional time. There is no real user, model, network, task execution, or autonomous service. Latency only covers completed tasks and must be read with completion rates. The simulator does not resume interrupted runs; only storage state and receipts survive clean reopen. Fact accuracy is exact lookup with known expiry, not semantic recall.

## Reproduce

From the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 -m continuum benchmark --seeds 30 --output results
python3 -m continuum demo --policy adaptive --scenario quiet_deadlines --seed 0
```

The benchmark overwrites its three named output artifacts in the chosen output directory. Use a separate directory to compare a new run. `results/tests.txt` records the completed test run; its timing is not a deterministic artifact. `results/demo.json` records the checked CLI output. Database files are local and ignored by Git.

**Next step:** review the README and checked-in benchmark evidence. No further implementation is part of v0.1.
