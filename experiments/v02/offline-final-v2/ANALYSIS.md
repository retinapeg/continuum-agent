# offline-final-v2: regenerated analysis

Split: **offline-development**. Provider: `fixture` / `rules-v2`.
Attempted: **3240 / 3240** declared episodes. Statuses: `{'succeeded': 3240}`.

| Condition / call budget | Episodes | Completion | Valid-only completion | Pooled precision | Pooled recall | Mean calls | Mean interruptions | Conditional virtual latency (s) | All-attempt USD estimate / outcome |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A/budget-2 | 180 | 22.22% | 22.22% | 100.00% | 17.65% | 1.500 | 0.167 | 0.000 | — |
| A/budget-4 | 180 | 22.22% | 22.22% | 100.00% | 17.65% | 1.500 | 0.167 | 0.000 | — |
| A/budget-8 | 180 | 22.22% | 22.22% | 100.00% | 17.65% | 1.500 | 0.167 | 0.000 | — |
| B/budget-2 | 180 | 22.22% | 22.22% | 100.00% | 17.65% | 2.000 | 0.167 | 6.000 | — |
| B/budget-4 | 180 | 28.89% | 28.89% | 28.00% | 24.71% | 4.000 | 0.833 | 18.857 | — |
| B/budget-8 | 180 | 28.89% | 28.89% | 28.00% | 24.71% | 4.833 | 0.833 | 18.857 | — |
| C/budget-2 | 180 | 22.22% | 22.22% | 100.00% | 17.65% | 2.000 | 0.167 | 0.000 | — |
| C/budget-4 | 180 | 38.89% | 38.89% | 40.00% | 35.29% | 3.944 | 0.833 | 3.000 | — |
| C/budget-8 | 180 | 38.89% | 38.89% | 40.00% | 35.29% | 5.111 | 0.833 | 3.000 | — |
| D/budget-2 | 180 | 22.22% | 22.22% | 100.00% | 17.65% | 2.000 | 0.167 | 0.000 | — |
| D/budget-4 | 180 | 38.89% | 38.89% | 40.00% | 35.29% | 4.000 | 0.833 | 3.000 | — |
| D/budget-8 | 180 | 38.89% | 38.89% | 40.00% | 35.29% | 7.311 | 0.833 | 3.000 | — |
| D_no_memory/budget-2 | 180 | 5.56% | 5.56% | — | 0.00% | 2.000 | 0.000 | — | — |
| D_no_memory/budget-4 | 180 | 22.22% | 22.22% | 20.00% | 17.65% | 4.000 | 0.833 | 6.000 | — |
| D_no_memory/budget-8 | 180 | 22.22% | 22.22% | 20.00% | 17.65% | 7.311 | 0.833 | 6.000 | — |
| E/budget-2 | 180 | 22.22% | 22.22% | 100.00% | 17.65% | 2.000 | 0.167 | 0.000 | — |
| E/budget-4 | 180 | 38.89% | 38.89% | 40.00% | 35.29% | 4.000 | 0.833 | 3.000 | — |
| E/budget-8 | 180 | 38.89% | 38.89% | 40.00% | 35.29% | 7.311 | 0.833 | 3.000 | — |

Null values are unavailable or have no denominator. Precision/recall above are pooled; JSON also retains conditional episode means and contributing counts. Valid-only means no call-level failure; a failed or denied tool action still counts as a valid protocol execution with an unsuccessful task outcome. A recorded model call is one CLI invocation, which may contain internal retries and auxiliary inference requests. USD values are CLI API-equivalent estimates, never subscription invoices. Missing cost in any attempted episode makes total cost/outcome unknown.

## Factuality, clarification and reliability

| Condition / budget | Supported fields | Stale fields, mean | Contradiction handled | Appropriate clarification | Appropriate inaction | Recovery | Duplicate effects, mean |
|---|---:|---:|---:|---:|---:|---:|---:|
| A/budget-2 | — (n=0) | 0.000 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 0.00% (n=30) | 0.000 (n=180) |
| A/budget-4 | — (n=0) | 0.000 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 0.00% (n=30) | 0.000 (n=180) |
| A/budget-8 | — (n=0) | 0.000 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 0.00% (n=30) | 0.000 (n=180) |
| B/budget-2 | — (n=0) | 0.000 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 0.00% (n=30) | 0.000 (n=180) |
| B/budget-4 | 100.00% (n=120) | 0.000 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 20.00% (n=30) | 0.000 (n=180) |
| B/budget-8 | 100.00% (n=120) | 0.000 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 20.00% (n=30) | 0.000 (n=180) |
| C/budget-2 | — (n=0) | 0.000 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 0.00% (n=30) | 0.000 (n=180) |
| C/budget-4 | 75.00% (n=120) | 0.167 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 100.00% (n=30) | 0.000 (n=180) |
| C/budget-8 | 75.00% (n=120) | 0.167 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 100.00% (n=30) | 0.000 (n=180) |
| D/budget-2 | — (n=0) | 0.000 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 0.00% (n=30) | 0.000 (n=180) |
| D/budget-4 | 75.00% (n=120) | 0.167 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 100.00% (n=30) | 0.000 (n=180) |
| D/budget-8 | 75.00% (n=120) | 0.167 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 100.00% (n=30) | 0.000 (n=180) |
| D_no_memory/budget-2 | — (n=0) | 0.000 (n=180) | 0.00% (n=30) | 0.00% (n=50) | 100.00% (n=10) | 0.00% (n=30) | 0.000 (n=180) |
| D_no_memory/budget-4 | 80.00% (n=150) | 0.167 (n=180) | 0.00% (n=30) | 0.00% (n=50) | 100.00% (n=10) | 100.00% (n=30) | 0.000 (n=180) |
| D_no_memory/budget-8 | 80.00% (n=150) | 0.167 (n=180) | 0.00% (n=30) | 0.00% (n=50) | 100.00% (n=10) | 100.00% (n=30) | 0.000 (n=180) |
| E/budget-2 | — (n=0) | 0.000 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 0.00% (n=30) | 0.000 (n=180) |
| E/budget-4 | 75.00% (n=120) | 0.167 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 100.00% (n=30) | 0.000 (n=180) |
| E/budget-8 | 75.00% (n=120) | 0.167 (n=180) | 100.00% (n=30) | 60.00% (n=50) | 100.00% (n=10) | 100.00% (n=30) | 0.000 (n=180) |

Counts are contributing episodes for each metric; task-specific metrics have fewer eligible episodes. These are descriptive means, not additional confirmatory significance tests. Parsed supported fields do not certify unrestricted prose.

## Resource accounting

| Condition / budget | Episode wall time, mean seconds | Interruptions / simulated hour | Known USD subtotal | Complete USD total | Uncached input | Cached reads | Cache creation | Output tokens |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A/budget-2 | 0.012 | 5.000 | — | — | — | — | — | — |
| A/budget-4 | 0.013 | 5.000 | — | — | — | — | — | — |
| A/budget-8 | 0.014 | 5.000 | — | — | — | — | — | — |
| B/budget-2 | 0.013 | 5.000 | — | — | — | — | — | — |
| B/budget-4 | 0.023 | 25.000 | — | — | — | — | — | — |
| B/budget-8 | 0.029 | 25.000 | — | — | — | — | — | — |
| C/budget-2 | 0.013 | 5.000 | — | — | — | — | — | — |
| C/budget-4 | 0.023 | 25.000 | — | — | — | — | — | — |
| C/budget-8 | 0.033 | 25.000 | — | — | — | — | — | — |
| D/budget-2 | 0.014 | 5.000 | — | — | — | — | — | — |
| D/budget-4 | 0.027 | 25.000 | — | — | — | — | — | — |
| D/budget-8 | 0.034 | 25.000 | — | — | — | — | — | — |
| D_no_memory/budget-2 | 0.011 | 0.000 | — | — | — | — | — | — |
| D_no_memory/budget-4 | 0.022 | 25.000 | — | — | — | — | — | — |
| D_no_memory/budget-8 | 0.031 | 25.000 | — | — | — | — | — | — |
| E/budget-2 | 0.012 | 5.000 | — | — | — | — | — | — |
| E/budget-4 | 0.022 | 25.000 | — | — | — | — | — | — |
| E/budget-8 | 0.035 | 25.000 | — | — | — | — | — | — |

Known subtotals include only episodes with complete recorded cost telemetry; they are lower bounds, not total cost. Wall time includes local processing/provider waits for an episode. Interruption rates use the 120-second simulated horizon and must not be read as observed real-world hourly contact rates. Missing usage remains unknown. Actual subscription charges and rate dates are unobserved.

## Paired differences

| D minus control / budget | Scenario clusters | Completion difference | 95% bootstrap interval |
|---|---:|---:|---:|
| D-minus-A/budget-2 | 180 | +0.00 pp | [+0.00, +0.00] pp |
| D-minus-B/budget-2 | 180 | +0.00 pp | [+0.00, +0.00] pp |
| D-minus-C/budget-2 | 180 | +0.00 pp | [+0.00, +0.00] pp |
| D-minus-E/budget-2 | 180 | +0.00 pp | [+0.00, +0.00] pp |
| D-minus-A/budget-4 | 180 | +16.67 pp | [+11.11, +21.67] pp |
| D-minus-B/budget-4 | 180 | +10.00 pp | [+4.44, +15.56] pp |
| D-minus-C/budget-4 | 180 | +0.00 pp | [+0.00, +0.00] pp |
| D-minus-E/budget-4 | 180 | +0.00 pp | [+0.00, +0.00] pp |
| D-minus-A/budget-8 | 180 | +16.67 pp | [+11.11, +21.67] pp |
| D-minus-B/budget-8 | 180 | +10.00 pp | [+4.44, +15.56] pp |
| D-minus-C/budget-8 | 180 | +0.00 pp | [+0.00, +0.00] pp |
| D-minus-E/budget-8 | 180 | +0.00 pp | [+0.00, +0.00] pp |

## Family completion

| Family | A | B | C | D | E | D_no_memory |
|---|---:|---:|---:|---:|---:|---:|
| changed_instructions | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| deadline_followup | 33.33% | 33.33% | 33.33% | 33.33% | 33.33% | 33.33% |
| delayed_dependencies | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| document_update | 0.00% | 13.33% | 0.00% | 0.00% | 0.00% | 0.00% |
| interrupted_work | 0.00% | 13.33% | 66.67% | 66.67% | 66.67% | 66.67% |
| memory_revision | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 0.00% |

Offline family values pool call budgets; use per-budget tables for resource comparisons. There are six handcrafted templates, not broad task generalization. Zero differences or narrow intervals do not establish equivalence.

## Execution failures and schedule checks

Call failures: `{}`. All remain in attempted-episode results.
Realized D/E call schedules match in 540/540 comparable pairs. Mismatches are retained below in machine-readable analysis, including safety stops.

## Interpretation limits

Supported-fact accuracy covers parsed Status/Risk fields only. Stale-field counts are not a complete semantic contradiction detector. Clarification checks use a predefined narrow rubric. Latency is conditional on a matched opportunity and uses virtual world time. Provider tokens are aggregate telemetry; auxiliary CLI models are included once. Workload recovery denotes a clean reopen; crash recovery has separate tests.

Review packets are prepared for independent human review; no completed human review is claimed. Model self-grades do not determine scores.
