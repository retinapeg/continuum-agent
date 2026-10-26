# Continuum 1.0 acceptance record

The central experiment, four-policy comparison, persistent receipts and dashboard are demonstrated. Work stops here: no learned trigger, orchestrator, integration or additional product features were added.

| Requirement | Demonstrated evidence |
|---|---|
| 1. Hidden world changes independently | Analytical oscillator tests compare unobserved changed/unchanged worlds; hidden changes are not public events. `tests_lab/test_world.py` |
| 2. Only authorised observations | Frozen `PolicyInput` excludes world/seed/parameters; a deliberately over-budget policy cannot invoke the sensor. `test_world.py`, `test_engine.py` |
| 3. Scheduling changes obtained information | Schedulers produce different observation timestamps under identical worlds; held-out prediction errors differ materially. `test_engine.py`, `heldout-001/results.jsonl` |
| 4. Same world replays across policies | Counterfactual sensor noise depends on timestamp, not call order. Shared world fingerprints and complete trace reproduction pass. |
| 5. Independent reproducible scoring | Hand-calculated RMSE/NLL/coverage, target-time checks, one-to-one alerts, misses, malformed data and resource isolation tests. All 384 final units reproduce exactly. |
| 6. Actual calls, failures and effects recorded | SQLite operation/event receipts; failed updates and failed legacy tool effects remain failed. Three actual Claude CLI invocations have exact model/output/accounting receipts. |
| 7. Persistence survives restart | Checkpoint recovery matches uninterrupted execution; restart pauses durably; exclusive owner locks and duplicate operations are tested. Confirmed/proposed memory isolation and contradictory assertions are tested. |
| 8. Dashboard shows real evidence | Nine real-Chrome acceptance checks, zero page errors; actual simulation controls, delayed truth reveal, independent scores and clickable receipt references. |
| 9. Understandable within 30 seconds | First screen states the question, hidden oscillator, four policies and limited budget; Run, step, replay and setup share one route. Desktop and 390px mobile screenshots inspected. This is a design/inspection criterion, not a timed human usability study. |
| 10. README states best result and failed hypothesis | Frozen uncertainty heuristic is worse on RMSE; historical v0.2 hybrid completion hypothesis remains unsupported. Both are prominent, with evidence and scope. |

**Tests:** 51 laboratory + 88 runtime + 28 legacy = **167 passing tests**. The archived v0.1 test suite also passes and its benchmark artifacts reproduce byte-for-byte.

**Comparative evaluation:** 384 development units, protocol/source freeze, then 384 held-out units. No runtime exceptions; expected rejected operations remain in metrics. Full per-unit traces and scores reproduce. There was no tuning after held-out evaluation.

**Browser validation:** [passing receipt](../experiments/v1/validation/browser-v5/receipt.json), [desktop](../experiments/v1/validation/browser-v5/desktop.png), [mobile](../experiments/v1/validation/browser-v5/mobile.png). Earlier selector, reveal-toggle and event-overlap failures were fixed; their original failure receipts remain in `experiments/v1/browser-smoke-v1` and `experiments/v1/validation/browser-v2` / `browser-v3`. Deterministic and replay controls make no model calls. The separate live-pilot status displays actual recorded results.

**Live validation:** Explicit user opt-in preceded the three-attempt pilot. 3/3 valid proposals, exact `claude-haiku-4-5-20251001`, zero failures, 51.824 seconds. This is fixed-context trigger/adapter validation, not a live closed-loop efficacy experiment. [Exact live results](LIVE_RESULTS_V1.md).

**Preservation:** [verification receipt](../experiments/v1/validation/preservation-check.json) confirms all 149 original historical experiment/report files unchanged, the pre-redesign archive hash intact, and every original shared-quota-ledger row retained. Three new invocation rows are the authorised pilot. Other original runtime files are unchanged. Missing original per-unit SQLite/telemetry was not invented or reconstructed as fact. No sibling repository, global instructions, authentication, Git automation, commit or push was changed/performed.

Machine-readable verification:

- [Laboratory tests](../experiments/v1/validation/lab-tests.txt)
- [Runtime tests](../experiments/v1/validation/runtime-tests.txt)
- [Legacy tests](../experiments/v1/validation/legacy-tests.txt)
- [Historical reproduction](../experiments/v1/validation/v01-reproduction.txt)
- [Final held-out reproduction](../experiments/v1/validation/heldout-reproduction.json)
- [Frozen evaluation results](RESULTS_V1.md)

Limits: one oscillator family, two tested budget levels, twelve held-out seed clusters, heuristic scheduling, misspecified nominal estimator after changes, weak change detection, no malicious-policy sandbox, no claim of optimal VOI or scientific novelty. The dashboard's interactive defaults are exploratory and need not equal the development-selected frozen configuration. User-injected runs never enter the held-out evidence.
