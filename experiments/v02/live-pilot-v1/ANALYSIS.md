# live-pilot-v1: regenerated analysis

Split: **pilot**. Provider: `claude` / `claude-sonnet-4-6`.
Attempted: **30 / 30** declared episodes. Statuses: `{'succeeded': 30}`.

| Condition / call budget | Episodes | Completion | Valid-only completion | Pooled precision | Pooled recall | Mean calls | Mean interruptions | Conditional virtual latency (s) | All-attempt USD estimate / outcome |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A/budget-4 | 6 | 0.00% | 0.00% | 50.00% | 16.67% | 1.500 | 0.833 | 0.000 | — |
| B/budget-4 | 6 | 50.00% | 50.00% | 50.00% | 50.00% | 3.500 | 1.333 | 18.000 | 0.209 |
| C/budget-4 | 6 | 50.00% | 50.00% | 75.00% | 50.00% | 3.500 | 1.500 | 4.000 | 0.206 |
| D/budget-4 | 6 | 33.33% | 33.33% | 100.00% | 33.33% | 3.333 | 1.333 | 0.000 | 0.289 |
| E/budget-4 | 6 | 33.33% | 33.33% | 60.00% | 50.00% | 3.667 | 1.167 | 2.000 | 0.327 |

Null values are unavailable or have no denominator. Precision/recall above are pooled; JSON also retains conditional episode means and contributing counts. USD values are CLI API-equivalent estimates, never subscription invoices. Missing cost in any attempted episode makes total cost/outcome unknown.

## Paired differences

| D minus control / budget | Scenario clusters | Completion difference | 95% bootstrap interval |
|---|---:|---:|---:|
| D-minus-A/budget-4 | 6 | +33.33 pp | [+0.00, +66.67] pp |
| D-minus-B/budget-4 | 6 | -16.67 pp | [-50.00, +0.00] pp |
| D-minus-C/budget-4 | 6 | -16.67 pp | [-66.67, +33.33] pp |
| D-minus-E/budget-4 | 6 | +0.00 pp | [-50.00, +50.00] pp |

## Family completion

| Family | A | B | C | D | E |
|---|---:|---:|---:|---:|---:|
| changed_instructions | 0.00% | 100.00% | 100.00% | 0.00% | 100.00% |
| deadline_followup | 0.00% | 100.00% | 100.00% | 100.00% | 100.00% |
| delayed_dependencies | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| document_update | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| interrupted_work | 0.00% | 0.00% | 100.00% | 0.00% | 0.00% |
| memory_revision | 0.00% | 100.00% | 0.00% | 100.00% | 0.00% |

Offline family values pool call budgets; use per-budget tables for resource comparisons. There are six handcrafted templates, not broad task generalization. Zero differences or narrow intervals do not establish equivalence.

## Execution failures and schedule checks

Call failures: `{}`. All remain in attempted-episode results.

## Interpretation limits

Supported-fact accuracy covers parsed Status/Risk fields only. Stale-field counts are not a complete semantic contradiction detector. Clarification checks use a predefined narrow rubric. Latency is conditional on a matched opportunity and uses virtual world time. Provider tokens are aggregate telemetry; auxiliary CLI models are included once. Workload recovery denotes a clean reopen; crash recovery has separate tests.

Review packets are prepared for independent human review; no completed human review is claimed. Model self-grades do not determine scores.
