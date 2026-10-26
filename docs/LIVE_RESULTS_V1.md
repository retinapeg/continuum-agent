# Live Claude pilot — exact results

The authorised pilot completed **3/3 valid trigger proposals**, with **0 failures**, in **51.824 wall-clock seconds**. All three invocations reported the requested `claude-haiku-4-5-20251001` model through installed Claude Code 2.1.310. No proposed tools, messages, memory updates or goal updates were executed.

| Public simulated time | Status | Proposed next observation | Wall-clock latency | Reported model |
|---:|---|---:|---:|---|
| 0 s | succeeded | 5 s | 19.930 s | claude-haiku-4-5-20251001 |
| 45 s | succeeded | 5 s | 17.745 s | claude-haiku-4-5-20251001 |
| 80 s | succeeded | 10 s | 14.138 s | claude-haiku-4-5-20251001 |

These are **three CLI invocations**, with 11 CLI-reported internal turns in total. Internal service-request counts are not independently observed. Aggregate CLI-reported API-equivalent cost was **$0.0607254**, an estimate rather than a subscription charge. Actual charges remain unknown. All three contexts were attempted; there were zero known-unsent attempts, zero unknown invocation counts and zero failures in this pilot.

This validates the installed CLI path, exact model reporting, structured trigger outputs and accounting under the declared limits. It does **not** validate the quality of the proposed delays, model explanations, numerical estimation or closed-loop scheduling performance. The model summaries are raw proposals, not factual operation receipts. No new live comparative-performance claim is made.

- [Prepared scope and limits](LIVE_PILOT.md).
- [Exact public contexts](../experiments/v1/live-public-contexts.json).
- [Pilot manifest](../experiments/v1/live-pilot-001/manifest.json).
- [Every attempt, proposal and receipt](../experiments/v1/live-pilot-001/attempts.jsonl).
- [Full result and accounting](../experiments/v1/live-pilot-001/report.json).
- SQLite calls/events remain in `experiments/v1/live-pilot-001/pilot.sqlite`; it is ignored by Git but retained locally.

The pre-existing v0.2 failed pilots, failure analyses and incomplete telemetry are untouched. Current mocked failure tests verify that invalid responses, failed effects and known-unsent attempts cannot become successes.
