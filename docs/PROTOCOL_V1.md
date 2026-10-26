# Continuum laboratory evaluation protocol v1

This protocol is fixed before the final held-out run. `freeze` records the selected development parameters, exact generated worlds, source hashes, this document, and a source archive. Neither freezing nor deterministic evaluation invokes Claude. A live pilot is separate evidence and is not pooled into these results.

## Question and primary outcome

Does an uncertainty-aware observation scheduler improve mean episode prediction RMSE relative to strong periodic and event/deadline schedulers under equal observation and inference caps in a partially observed changing world?

The primary outcome is the arithmetic mean of episode RMSEs for one-second-ahead position forecasts on every 0.5-second simulated tick that has a complete target within the 120-second episode. Sleeping periods remain in scoring. Predictions are evaluated against private simulator truth by an independent scorer. All policies have the same forecast targets. A zero-position predictor is reported as a reference for signal decay, not as a tuned competitor.

No novelty, optimality, general autonomy, or LLM superiority claim follows from this experiment. The existing v0.2 failure to show a hybrid completion advantage remains a separate preserved result.

## Shared world and information boundary

The world is a damped oscillator evolved with the exact state-transition matrix, with initial position 1 and velocity 0. Nominal angular frequency is 0.8, damping is 0.015, and observation noise standard deviation is 0.08. The simulated clock is independent of computer speed. The policies know the common initial state and nominal model, but receive neither the scenario name, world seed, future change times, actual current oscillator parameters, nor private trajectory.

Each world seed determines two hidden parameter-change times on the simulation grid: approximately 22.5–37.5% and 56.67–73.33% of the horizon. Changes set frequency/damping to 1.25/0.012 and 0.55/0.025 respectively. `protocol.json` contains the actual full configuration for each held-out case. Measurement noise is keyed to the world seed and measurement tick, independent of policy and call order. A stale observation retains its original measurement timestamp.

Four equally weighted scenario families are used:

- `no_change`: genuinely constant physical parameters, with noisy observations.
- `change`: the two hidden parameter changes.
- `stale`: the same changes, plus stale observations during seconds 42–62 with a 12-second lag.
- `adversarial`: the same changes, plus sensor bias +1.5 during seconds 50–57 and −1.5 during seconds 83–87.

Public inspection events occur at seconds 19, 49, and 89. Public deadlines occur at 25%, 50%, and 75% of the horizon. These do not announce hidden changes. Every physical measurement requires a charged observation. All non-oracle schedulers receive the same typed public fields and available action types. The Python boundary prevents accidental leakage; it is not a sandbox for malicious policy code.

## Policies and controlled resources

The competitors are fixed-period, event/deadline, original-hybrid adaptation, and uncertainty-aware scheduling. The hybrid adaptation reuses the preserved original analytic state dynamics; it is not a byte-identical replay of the original assistant-task policy. The uncertainty scheduler uses a greedy expected variance-reduction proxy plus budget pacing, not an optimal value-of-information solution.

All four use the same nominal two-state Kalman estimator and the same detector. A normalized innovation magnitude greater than 2.6 can produce an alert, subject to a 10-second refractory interval and a cap of 30 alerts. Stale measurements are rejected. Innovations exceeding magnitude 8 are rejected as contradictory while remaining detection evidence. Rejected updates retain their receipts and count as failed operations.

For each experimental condition, both observation and inference caps are either 12 or 24. An inference is a classical Kalman measurement-update attempt; there are zero model calls. Observation costs 1, inference costs 2, and each executed alert costs 0.1. Clock progression, cheap scheduler evaluation, prior propagation, fixed-grid predictions, and independent scoring are declared shared numerical overhead. They do not consume the measurement-update budget. Resource caps are equal; realized consumption may differ and is reported.

## Development selection

Development seeds are **0, 1, 2, 3**, crossed with four scenario families and two budget levels. Each scheduler receives exactly three candidate configurations, each evaluated on all 32 development worlds/budgets:

| Scheduler | Candidates |
| --- | --- |
| Fixed period | `period_scale`: 0.75, 1.0, 1.5 |
| Event/deadline | `period_scale`: 0.75, 1.0, 1.5 |
| Original hybrid adaptation | `period_scale`: 0.75, 1.0, 1.5 |
| Uncertainty aware | `threshold`: 0.015, 0.035, 0.08 |

This is **384 development units**, with equal tuning allowance. For each scheduler, choose the lowest mean episode RMSE across all development conditions. Exact ties select the first declared candidate. Every candidate's metrics, receipts, forecasts, and failures are saved. Any runtime exception or source drift makes the development selection invalid and blocks freezing. Expected unsuccessful operations in stale/adversarial scenarios remain scientific outcomes rather than exclusions.

## Held-out evaluation and uncertainty

Held-out seeds are **1000 through 1011**, crossed with four scenarios, two budgets, and four selected policies: **384 units**. No threshold or model change is permitted after freezing. Every policy sees the same world configuration and counterfactual measurement process for each matched condition.

For each baseline, compute uncertainty RMSE minus baseline RMSE within each seed/scenario/budget pair. Average the eight paired differences within each seed. Bootstrap the twelve seed means with replacement for **2,000 replicates**, using bootstrap seed **20261026**. Report the mean paired difference and interpolated 2.5th/97.5th percentiles. Negative differences favor uncertainty. These are descriptive 95% intervals without multiplicity correction; a pair-specific interval below zero is not a general superiority claim.

Report overall and scenario/budget means for RMSE, zero-reference RMSE, Gaussian negative log likelihood, nominal 95% coverage, detection delay, censored delay, missed changes, false alarms, observations, inference updates, alerts, composite cost, and failed receipts. Also report total missed changes, detections, false alarms, and failures. Conditional delays are averaged only where defined, with the number of defined episodes disclosed. They must be interpreted together with misses and censored delay.

Alerts match chronologically to the earliest unmatched change within the inclusive interval from change time to 20 seconds afterward. Matching is one-to-one. Unmatched alerts, including early, late, and duplicate alerts, are false alarms. Missed changes contribute 20 seconds to censored delay. No-change episodes have undefined detection delay, not zero delay. Gaussian intervals are evaluated as empirical calibration outcomes, not assumed guarantees after model mismatch.

## Failure handling and evidence

Each unit saves the complete world configuration, truth trajectory, forecasts, observations, event receipts, resource consumption, status, and metrics. Raw results are JSON Lines; traces and receipts are gzip-compressed JSON Lines. Runtime exceptions preserve their type, message, stack trace, and all prior receipts. The remaining scheduled units still run, but **any runtime exception invalidates aggregate performance comparisons**. Failed units are never silently omitted or treated as successful.

Campaign output directories must be new and repository-local. Historical artifacts cannot be overwritten. An interrupted output remains preserved; this version deliberately refuses to rerun into that directory. A replacement campaign requires a fresh freeze and directory. Source drift before execution blocks the run; detected drift during execution invalidates its comparison. Final evidence hashes are recorded in `run-receipt.json`.

`verify --reproduce` reruns completed deterministic units in memory, compares metrics and complete traces, and excludes only measured wall-clock elapsed time from result comparison. It does not rewrite the frozen files. It requires matching frozen source; the archive contains the exact Python sources and tests needed for a separate repository-local reconstruction if the working tree later changes.

## Commands

```sh
.venv/bin/python -m continuum.lab.campaign develop --directory experiments/v1/development-001
.venv/bin/python -m continuum.lab.campaign freeze --directory experiments/v1/heldout-001 --development experiments/v1/development-001
.venv/bin/python -m continuum.lab.campaign run --directory experiments/v1/heldout-001
.venv/bin/python -m continuum.lab.campaign verify --directory experiments/v1/heldout-001 --reproduce
```

The final held-out run must wait until implementation and acceptance checks are finished. A failed hypothesis is an acceptable result; tuning against held-out outcomes is not.
