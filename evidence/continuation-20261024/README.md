# 24 October 2026 continuation receipts

One writer, existing `main`, HEAD `a0ecdd5`; no commit, new live trial or service.
The user authorized one telemetry improvement after auditing the existing v0.2.

| Evidence | Meaning |
|---|---|
| [preservation.json](preservation.json) | Initial state and hash of the full local 62,585-file manifest; original notes retained under `.cache/continuation-20261024-original/` |
| [baseline-runtime.txt](baseline-runtime.txt), [baseline-legacy.txt](baseline-legacy.txt) | 78 + 28 passed before source edits |
| [baseline-accounting.txt](baseline-accounting.txt), [first-accounting.txt](first-accounting.txt) | Existing 9 accounting tests passed before/after the first implementation |
| [telemetry-tests.txt](telemetry-tests.txt) | Initial 17 new tests passed; the final suite includes an additional crash-after-receipt regression |
| [final-runtime.txt](final-runtime.txt), [final-legacy.txt](final-legacy.txt) | 96 + 28 passed; legacy SQLite ResourceWarning persists |
| [stored-evidence.json](stored-evidence.json) | 3,240 offline + 180 live episodes re-scored, original reports reconstructed, 3,422 SQLite integrity checks; no inference |
| [v01-reproduction.txt](v01-reproduction.txt), [offline-reproduction.txt](offline-reproduction.txt) | Archived v0.1 tests/450-run files byte-identical; final frozen v0.2 3,240 episodes identical except wall timing |
| [migration-copy.json](migration-copy.json) | Historical schema-2 unit copied locally, opened twice with additive migration; all existing rows unchanged; no backfill |
| [validation.json](validation.json) | Checks, tested source hashes, final preservation comparison, Git/process state and limitations |

Exact reproduction commands and environment assumptions are in [learning.md](../../learning.md).
Never invoke campaign `report`, `analyze`, or `resume` on original frozen evidence
just to inspect it: those commands write there. `scripts/verify_stored_evidence.py`
uses immutable read-only databases and regenerates reports only in disposable copies.

Files changed for this continuation:

- `continuum/runtime/telemetry.py` (new), `database.py`, `engine.py`, `providers.py`,
  `routing.py`: additive attempt persistence, failure classification, known/unknown
  usage coverage, existing fallback attribution and content-free telemetry fields.
- `tests_runtime/test_telemetry.py` (new): 18 fixture/fault-injection regressions.
- `scripts/verify_stored_evidence.py` (new): reproducible offline audit, no provider calls.
- `learning.md`, `decisions.md`, `MORNING_REPORT.md`, `README.md`, `TEST_REPORT.md`:
  current checkpoint, architectural rationale, experiment register and evidence limits.

`AGENTS.md` was pre-existing and remains byte-identical. No old test or experimental
record was deleted. Frozen source, results, ignored databases and `.runtime` contents
retain their initial hashes. This validates preservation, not general production readiness.
