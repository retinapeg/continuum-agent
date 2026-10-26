# Phase 0 — preservation and scope

Starting commit: `6134705b8392f6fca84d00cee78aabd6c9243986`. Git was clean; no uncommitted source changes existed. Baseline: 28 legacy + 78 runtime unittest tests passed on 2026-10-26.

`preserved/pre-v1/repository.tar.gz` snapshots tracked source and all existing experiment/results/evidence files, including available ignored local runtime SQLite state (historical per-unit experimental databases were not present in this checkout). `manifest.json` records individual SHA-256 hashes and the archive digest. The snapshot may contain local runtime context; treat it as local evidence and review before publishing. No historical files are removed or rewritten.

| Decision | Paths | Purpose |
|---|---|---|
| Keep immutable | `experiments/v01-check`, `experiments/v02`, `preserved/v0.1`, `results`, `evidence`, historical root reports/protocol | Preserve original experiments, failures, manifests and receipts |
| Reuse | `continuum/runtime/database.py`, `memory.py`, `common.py`, `providers.py`, `dynamics.py` | SQLite transactions/provenance, memory, bounded Claude CLI and original hybrid equations |
| Keep as historical executable | `continuum/agents.py`, `simulation.py`, `scenarios.py`, `benchmark.py`, `continuum/research/` | Reproduce v0.1/v0.2 and their negative result |
| Replace default | `README.md`, default `continuum` entrypoint; add `continuum/lab/` and its UI | Focus on a physical partially observable experiment, not an assistant |
| Retire from default, retain source | `continuum/runtime/ui/`, `watcher.py`, `integration.py`, `facade.py`, `routing.py`, assistant goal/notification flows | No new orchestration, integrations or personal assistant functionality |
| Repair | `continuum/runtime/engine.py` notification handling | Completion claims must follow actual successful effect receipts; failure must remain visible |

The `leo.continuum.v1` memory facade and `leo.integration.v1` local contract are present, but the laboratory does not import/connect them. No sibling repository, global configuration, authentication, Git hooks or shell wrappers are changed. Existing experimental `.runtime` states are preserved; new laboratory runs use new directories. The reused provider quota infrastructure appended three invocation rows to `.runtime/provider-ledger.sqlite` for the explicitly authorised live pilot. Every original ledger row is unchanged and the original file is also in the pre-redesign archive.

Scientific baseline: the v0.2 live campaign reported equal 55.56% completion for hybrid and event/deadline policies, with hybrid consuming 6.00 versus 5.11 invocations. It demonstrated no continuous-state completion advantage. New oscillator results are a separate experiment and cannot revise that finding.

Acceptance sequence: verify deterministic hidden-world/time/observation tests first; then policy equality of access, independent scoring and frozen held-out evaluation; then receipt/restart tests and real-browser dashboard checks. Live inference is a separate explicit opt-in pilot, with no API fallback.
