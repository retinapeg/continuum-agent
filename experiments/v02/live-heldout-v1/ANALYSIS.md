# live-heldout-v1: regenerated analysis

Split: **held-out**. Provider: `claude` / `claude-haiku-4-5-20251001`.
Attempted: **180 / 180** declared episodes. Statuses: `{'succeeded': 180}`.

Unit persistence status records whether the runner saved an episode result; it is not the goal-completion verdict.

| Condition / call budget | Episodes | Completion | Valid-only completion | Pooled precision | Pooled recall | Mean calls | Mean interruptions | Conditional virtual latency (s) | All-attempt USD estimate / outcome |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A/budget-6 | 36 | 13.89% | 14.71% | 100.00% | 8.82% | 1.500 | 0.333 | 0.000 | — |
| B/budget-6 | 36 | 30.56% | 39.29% | 29.03% | 26.47% | 4.833 | 1.250 | 19.333 | — |
| C/budget-6 | 36 | 55.56% | 55.88% | 56.25% | 52.94% | 5.111 | 0.972 | 10.000 | — |
| D/budget-6 | 36 | 55.56% | 54.84% | 58.06% | 52.94% | 6.000 | 1.056 | 10.667 | — |
| E/budget-6 | 36 | 52.78% | 51.61% | 56.67% | 50.00% | 6.000 | 1.056 | 9.176 | — |

Null values are unavailable or have no denominator. Precision/recall above are pooled; JSON also retains conditional episode means and contributing counts. Valid-only means no call-level failure; a failed or denied tool action still counts as a valid protocol execution with an unsuccessful task outcome. A recorded model call is one CLI invocation, which may contain internal retries and auxiliary inference requests. USD values are CLI API-equivalent estimates, never subscription invoices. Missing cost in any attempted episode makes total cost/outcome unknown.

## Factuality, clarification and reliability

| Condition / budget | Supported fields | Stale fields, mean | Contradiction handled | Appropriate clarification | Appropriate inaction | Recovery | Duplicate effects, mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| A/budget-6 | — (n=0) | 0.000 (n=36) | 50.00% (n=6) | 30.00% (n=10) | 100.00% (n=2) | 0.00% (n=6) | 0.000 (n=36) |
| B/budget-6 | 100.00% (n=10) | 0.000 (n=36) | 33.33% (n=6) | 60.00% (n=10) | 100.00% (n=2) | 0.00% (n=6) | 0.000 (n=36) |
| C/budget-6 | 100.00% (n=12) | 0.000 (n=36) | 50.00% (n=6) | 60.00% (n=10) | 100.00% (n=2) | 33.33% (n=6) | 0.000 (n=36) |
| D/budget-6 | 92.86% (n=14) | 0.000 (n=36) | 33.33% (n=6) | 50.00% (n=10) | 100.00% (n=2) | 33.33% (n=6) | 0.000 (n=36) |
| E/budget-6 | 100.00% (n=13) | 0.000 (n=36) | 0.00% (n=6) | 40.00% (n=10) | 100.00% (n=2) | 16.67% (n=6) | 0.000 (n=36) |

Counts are contributing episodes for each metric; task-specific metrics have fewer eligible episodes. These are descriptive means, not additional confirmatory significance tests. Parsed supported fields do not certify unrestricted prose.

## Resource accounting

| Condition / budget | Episode wall time, mean seconds | Interruptions / simulated hour | Known USD subtotal | Complete USD total | Uncached input | Cached reads | Cache creation | Output tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A/budget-6 | 14.213 | 10.000 | 0.564 | — | — | — | — | — |
| B/budget-6 | 46.584 | 37.500 | 1.875 | — | — | — | — | — |
| C/budget-6 | 49.822 | 29.167 | 2.564 | — | — | — | — | — |
| D/budget-6 | 57.613 | 31.667 | 2.776 | — | — | — | — | — |
| E/budget-6 | 57.193 | 31.667 | 2.634 | — | — | — | — | — |

Known subtotals include only episodes with complete recorded cost telemetry; they are lower bounds, not total cost. Wall time includes local processing/provider waits for an episode. Interruption rates use the 120-second simulated horizon and must not be read as observed real-world hourly contact rates. Missing usage remains unknown. Actual subscription charges and rate dates are unobserved.

## Paired differences

| D minus control / budget | Scenario clusters | Completion difference | 95% bootstrap interval |
|---|---:|---:|---:|
| D-minus-A/budget-6 | 18 | +41.67 pp | [+16.67, +63.89] pp |
| D-minus-B/budget-6 | 18 | +25.00 pp | [+5.56, +44.44] pp |
| D-minus-C/budget-6 | 18 | +0.00 pp | [-11.11, +11.11] pp |
| D-minus-E/budget-6 | 18 | +2.78 pp | [-16.67, +19.44] pp |

## Family completion

| Family | A | B | C | D | E |
|---|---:|---:|---:|---:|---:|
| changed_instructions | 0.00% | 50.00% | 100.00% | 100.00% | 100.00% |
| deadline_followup | 33.33% | 100.00% | 83.33% | 83.33% | 100.00% |
| delayed_dependencies | 0.00% | 0.00% | 16.67% | 16.67% | 33.33% |
| document_update | 0.00% | 0.00% | 50.00% | 66.67% | 66.67% |
| interrupted_work | 0.00% | 0.00% | 33.33% | 33.33% | 16.67% |
| memory_revision | 50.00% | 33.33% | 50.00% | 33.33% | 0.00% |

Offline family values pool call budgets; use per-budget tables for resource comparisons. There are six handcrafted templates, not broad task generalization. Zero differences or narrow intervals do not establish equivalence.

## Execution failures and schedule checks

Call failures: `{"['Failed to provide valid structured output after 5 attempts']": 4, "unexpected ambient tool request": 20, "unsupported goal update": 2}`. All remain in attempted-episode results.
Realized D/E call schedules match in 36/36 comparable pairs. Mismatches are retained below in machine-readable analysis, including safety stops.

## Observed usage coverage

| Condition | Recorded usage / attempted calls | Known uncached input | Known cached reads | Known cache creation | Known output | Known call-level USD subtotal |
|---|---:|---:|---:|---:|---:|---:|
| A | 52 / 54 | 287119 | 0 | 34348 | 45537 | 0.584 |
| B | 165 / 174 | 758442 | 36526 | 399926 | 149342 | 2.309 |
| C | 182 / 184 | 817756 | 48000 | 513780 | 165909 | 2.680 |
| D | 212 / 216 | 946791 | 71708 | 575414 | 188667 | 3.048 |
| E | 209 / 216 | 953461 | 47147 | 520664 | 187621 | 2.938 |

These call-level subtotals include observed calls inside incomplete episodes, so they differ from the more conservative complete-episode subtotals above. Neither is total spend. Missing categories and complete totals remain null in `usage-coverage.json`. The frozen live adapter discarded some terminal-error usage; a post-campaign repair preserves future receipts but does not backfill these trials.


## Interpretation limits

Supported-fact accuracy covers parsed Status/Risk fields only. Stale-field counts are not a complete semantic contradiction detector. Clarification checks use a predefined narrow rubric. Latency is conditional on a matched opportunity and uses virtual world time. Provider tokens are aggregate telemetry; auxiliary CLI models are included once. Workload recovery denotes a clean reopen; crash recovery has separate tests.

Review packets are prepared for independent human review; no completed human review is claimed. Model self-grades do not determine scores.
