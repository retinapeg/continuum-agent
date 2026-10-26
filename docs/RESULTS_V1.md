# Frozen oscillator results — Continuum 1.0

**The tested uncertainty-aware heuristic performed worse on prediction RMSE than every baseline.** This is a negative result for this declared heuristic, estimator, budget range and world family; it does not rule out other uncertainty-aware or learned schedulers.

Protocol and source were frozen before the final evaluation. Development used 384 units with three candidates per scheduler. Held-out evaluation used 12 new seeds × four scenario families × two observation/update budgets × four policies = **384 units**, 96 per policy. All 384 units completed, with **zero runtime exceptions** and **zero model calls**. Full deterministic reproduction matched every score and complete trace, excluding wall-clock execution time.

| Policy | Mean RMSE ↓ | 95% coverage | NLL ↓ | Censored delay (s) ↓ | Misses / 144 changes | False alarms | Failed updates | Mean cost |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Fixed period | 0.2700 | 95.1% | 0.3563 | 15.20 | 91 | 26 | 109 | 54.082 |
| Event / deadline | 0.2620 | 91.3% | 0.2680 | 17.99 | 117 | 16 | 98 | 54.045 |
| Original hybrid adaptation | 0.2521 | 92.5% | 0.2569 | 16.88 | 106 | 22 | 86 | 54.062 |
| Uncertainty aware | 0.3135 | 91.0% | 0.4556 | 17.51 | 107 | 19 | 195 | 54.058 |

All policies used a mean of 18 observations and 18 classical measurement updates (equal allocation across caps 12 and 24). The common zero-position reference had mean RMSE 0.3679. Failed updates are retained stale/contradictory rejections, not missing episodes. Their budgets are still charged. Cost is a declared dimensionless resource score, not money.

| Paired comparison | Uncertainty minus baseline RMSE | Descriptive 95% seed-bootstrap interval |
|---|---:|---:|
| vs Fixed period | +0.0434 | [0.0331, 0.0552] |
| vs Event / deadline | +0.0515 | [0.0405, 0.0619] |
| vs Original hybrid adaptation | +0.0614 | [0.0533, 0.0709] |

The intervals resample twelve seed clusters, 2,000 times, after averaging paired scenario/budget differences within each seed. Positive differences mean uncertainty was worse. These are descriptive, without multiplicity correction. The hybrid adaptation had the lowest observed mean RMSE here; the protocol did not predeclare pairwise superiority tests between the three baselines.

Detection remains weak: every policy missed most changes. Censored delay assigns 20 seconds to a miss; conditional delay is also recorded in report.json with its defined-episode denominator. No-change episodes have no detection-delay value. Prediction improvement must not be mistaken for reliable change detection. Aggregate calibration can also conceal poor coverage in particular scenarios; complete breakdowns are retained.

## Why this does not reverse the old result

The v0.2 assistant-task hybrid and event/deadline policies both achieved 55.56% completion, with hybrid consuming 6.00 versus 5.11 CLI invocations. That historical experiment demonstrated no continuous-state completion advantage. The oscillator uses a shared classical estimator and an explicit adaptation of the original scheduling equations; its different metric and task cannot overturn the old result.

## Evidence

- [Frozen protocol](../experiments/v1/heldout-001/protocol.json) and [protocol digest](../experiments/v1/heldout-001/protocol.sha256).
- [Machine-readable report](../experiments/v1/heldout-001/report.json), [all per-unit results](../experiments/v1/heldout-001/results.jsonl), and [complete traces / actual receipts](../experiments/v1/heldout-001/traces.jsonl.gz).
- [Run receipt](../experiments/v1/heldout-001/run-receipt.json) and [exact reproduction receipt](../experiments/v1/validation/heldout-reproduction.json).
- [All development candidates](../experiments/v1/development-001/development.json). No held-out retuning was performed.
- [Method and assumptions](PROTOCOL_V1.md), [prior research](RELATED_WORK.md), and [acceptance evidence](ACCEPTANCE_V1.md).
