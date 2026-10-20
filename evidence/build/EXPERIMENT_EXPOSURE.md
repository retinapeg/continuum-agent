# Experiment exposure ledger

- `v01-check`: original deterministic baseline reproduced; exploratory idle-activation counterfactual examined. No causal continuous-state advantage established by that audit.
- `offline-v1`, `offline-v2`: development seeds 0–29, all six templates, budgets 2/4/8. Their outcomes were inspected while repairing the runtime and scorer. They are not held-out evidence.
- `offline-final`: partial development run aborted after independent scorer review; evidence retained with ABORTED.md.
- `offline-final-v2`: final development offline matrix after schedule/scorer fixes. Replayed from frozen source in a fresh repository-local copy; equal metrics exclude nondeterministic wall elapsed time.
- `live-pilot-v1`, `live-pilot-v2`: seed 101, every family, development evidence. Sonnet/budget 4 and Haiku/budget 6 respectively. Pilot-v2 uses the earlier tighter streaming byte bound. All attempted outcomes remain published.
- `routing-development-v1`: seeds 301/302, fixed Haiku/fixed Sonnet/rule router, one call each. Separate from the main scientific comparison; no inference of router superiority.
- `improvement-proposal-v1`: seeds 200–202, fixture-only baseline versus candidate configuration copy. Human-readable diff queued; service unchanged. Promotion requires fresh evaluation and owner review.
- `live-runtime-demo-v1`: fictional owner goal with a document appearing after startup; real wall-clock demonstration, not part of any scored matrix.
- `live-heldout-v1`: seeds 1001–1003, six families, two repetitions, A–E, budget 6, one exact primary model. Protocol/source archive frozen before any of these outcomes. Further use of these scenarios for tuning must be labelled development/exposed; no automatic promotion uses them.

Every live call is a stochastic trial. Fixed seeds describe worlds and order, not deterministic model output. Source snapshots preserve pilot defects rather than retroactively scoring them as repaired software.

After all 180 held-out episodes completed, a coordinator-applied accounting/recovery patch was verified by regression tests and one fresh adapter preflight. It did not tune prompts, policies or scoring. Frozen outcomes and missing historical usage remain unchanged. No additional scored held-out trial was run.
