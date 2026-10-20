# live-pilot-v2: regenerated analysis

Split: **pilot**. Provider: `claude` / `claude-haiku-4-5-20251001`.
Attempted: **30 / 30** declared episodes. Statuses: `{'succeeded': 30}`.

| Condition / call budget | Episodes | Completion | Valid-only completion | Pooled precision | Pooled recall | Mean calls | Mean interruptions | Conditional virtual latency (s) | All-attempt USD estimate / outcome |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A/budget-6 | 6 | 0.00% | 0.00% | — | 0.00% | 1.500 | 0.333 | — | — |
| B/budget-6 | 6 | 16.67% | 16.67% | 50.00% | 16.67% | 2.167 | 0.500 | 6.000 | 0.182 |
| C/budget-6 | 6 | 33.33% | 50.00% | 50.00% | 33.33% | 4.167 | 1.000 | 3.000 | — |
| D/budget-6 | 6 | 33.33% | 40.00% | 33.33% | 33.33% | 4.167 | 0.833 | 3.000 | — |
| E/budget-6 | 6 | 66.67% | 80.00% | 66.67% | 66.67% | 3.833 | 0.667 | 3.000 | — |

Null values are unavailable or have no denominator. Precision/recall above are pooled; JSON also retains conditional episode means and contributing counts. USD values are CLI API-equivalent estimates, never subscription invoices. Missing cost in any attempted episode makes total cost/outcome unknown.

## Paired differences

| D minus control / budget | Scenario clusters | Completion difference | 95% bootstrap interval |
|---|---:|---:|---:|
| D-minus-A/budget-6 | 6 | +33.33 pp | [+0.00, +66.67] pp |
| D-minus-B/budget-6 | 6 | +16.67 pp | [-33.33, +66.67] pp |
| D-minus-C/budget-6 | 6 | +0.00 pp | [+0.00, +0.00] pp |
| D-minus-E/budget-6 | 6 | -33.33 pp | [-66.67, +0.00] pp |

## Family completion

| Family | A | B | C | D | E |
|---|---:|---:|---:|---:|---:|
| changed_instructions | 0.00% | 0.00% | 100.00% | 100.00% | 100.00% |
| deadline_followup | 0.00% | 0.00% | 100.00% | 100.00% | 100.00% |
| delayed_dependencies | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| document_update | 0.00% | 0.00% | 0.00% | 0.00% | 0.00% |
| interrupted_work | 0.00% | 0.00% | 0.00% | 0.00% | 100.00% |
| memory_revision | 0.00% | 100.00% | 0.00% | 0.00% | 100.00% |

Offline family values pool call budgets; use per-budget tables for resource comparisons. There are six handcrafted templates, not broad task generalization. Zero differences or narrow intervals do not establish equivalence.

## Execution failures and schedule checks

Call failures: `{"model slot unavailable or cancelled": 1, "total provider output limit exceeded": 3, "unexpected ambient tool request": 1}`. All remain in attempted-episode results.

## Interpretation limits

Supported-fact accuracy covers parsed Status/Risk fields only. Stale-field counts are not a complete semantic contradiction detector. Clarification checks use a predefined narrow rubric. Latency is conditional on a matched opportunity and uses virtual world time. Provider tokens are aggregate telemetry; auxiliary CLI models are included once. Workload recovery denotes a clean reopen; crash recovery has separate tests.

Review packets are prepared for independent human review; no completed human review is claimed. Model self-grades do not determine scores.
