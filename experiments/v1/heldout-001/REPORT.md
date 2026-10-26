# Frozen oscillator evaluation

No paired comparison demonstrates lower uncertainty-policy RMSE with a 95% interval wholly below zero. This is a bounded oscillator result, not evidence of general autonomous-agent superiority or novelty.

Recorded units: 384 / 384. Model calls: 0. Mode: deterministic.

| Policy | RMSE ↓ | Zero RMSE | NLL ↓ | 95% coverage | False alarms | Cost | Failed receipts |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| periodic | 0.270042 | 0.367877 | 0.356287 | 0.951 | 0.271 | 54.082 | 109 |
| event_deadline | 0.261959 | 0.367877 | 0.268022 | 0.913 | 0.167 | 54.045 | 98 |
| original_hybrid | 0.252052 | 0.367877 | 0.256858 | 0.925 | 0.229 | 54.062 | 86 |
| uncertainty | 0.313457 | 0.367877 | 0.455568 | 0.910 | 0.198 | 54.058 | 195 |

Means are per episode except failed receipts, which are totals. Full detection/censoring and scenario/budget breakdowns are in report.json.

| Paired RMSE difference: uncertainty minus | Difference | Seed-cluster 95% interval |
| --- | ---: | --- |
| periodic | 0.043415 | [0.033091, 0.055238] |
| event_deadline | 0.051498 | [0.040463, 0.061882] |
| original_hybrid | 0.061405 | [0.053301, 0.070869] |

Intervals use the frozen seed-cluster bootstrap and are descriptive, without multiple-comparison adjustment. Operation failures, stale evidence rejections, and contradictions remain in the raw receipts.

The preserved v0.2 result remains unchanged: hybrid did not demonstrate a completion advantage over event/deadline scheduling. This evaluation measures a different task.
