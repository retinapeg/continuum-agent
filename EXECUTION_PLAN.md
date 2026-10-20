# CONTINUUM execution plan

One source writer: coordinator. Independent readers and experiment workers only; separate run directories/databases. Build lock: `.build.lock` held with OS `flock`; runtime also takes its own ownership lock. No commits, sibling access, or separately billed APIs.

| Deliverable | Acceptance | Dependency | Progress |
|---|---|---|---|
| Preserve v0.1 | Readable tar, hashes, restore instructions; original 450-run outputs intact | None | Verified: 28 tests, 450 runs, byte-identical outputs; source snapshot readable |
| Durable runtime/state/memory | Restart and cancellation tests; analytical/discrete controls; revision and forgetting receipts | Baseline | Implemented; recovery/state/memory tests pass |
| Model adapters | Official docs/help; isolated structured proposal; bounded streaming; live preflight or exact blocker | CLI auth | Claude live verified; Codex deliberately disabled for isolation blocker |
| Capabilities/chat/UI | Source-backed artifact, local initiative, authenticated controls and real browser smoke | Runtime/adapters | Live three-call document demo and real Chromium smoke passed |
| Frozen evaluation | Six families; A–E plus memory ablation; resumable 30-seed offline; paired live held-out after pilot | Reliable runtime/scorers | Complete: 3,240 offline/reproduced; 180 held-out live episodes, 844 attempted calls; all 36 D/E schedules matched |
| Reliability/security | Crash checkpoints, leases, unknown outcome, injection/path/auth/permission tests; wall-clock soak | Runtime/UI | Complete: 78 runtime + 28 legacy tests; 120-second and 600.013-second soaks; post-campaign accounting repair and live preflight passed |
| Integration/router/improvement | Strict local envelope/stub; inspectable routing; proposal-only diff | Runtime/evaluation | HTTP stub tested; six routing trials done; candidate diff queued, unapplied |
| Reports and receipts | Source/test hashes per milestone; measured failures/ties; exact commands | All | Complete: final analysis, figures, usage coverage, TEST_REPORT and MORNING_REPORT; source/test receipts and restore integrity verified |

Consequence queue: real external messaging/payments/deployments/API billing remain disabled. Live subscription CLI calls on fictional fixtures are authorised. Generated executable code execution remains disabled. No extra permission is currently required for the local implementation.
