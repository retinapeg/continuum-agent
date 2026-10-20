# Security and owner control

This is a local research prototype, not production-ready infrastructure. Its threat model includes hostile model proposals, injected fixture documents, accidental retries, unauthenticated browser controls and malformed paths. It does not defend against a fully compromised owner account or malicious software with unrestricted access to the same filesystem.

## Enabled boundaries

- Dashboard binds only `127.0.0.1`. JSON APIs require a per-run random token; mutations additionally require exact same-origin `Origin` and `Host`. Token files are mode 0600. The token is entered locally and stored only in the browser tab's session storage. No public deployment is provided.
- UI rendering uses text nodes, not model-supplied HTML. CSP excludes external scripts and unsafe evaluation. Read APIs are authenticated because goals/memory are private to the owner.
- Model adapters preserve installed subscription authentication, strip API-key/provider override environment variables, avoid empty login homes, and never read authentication files. Claude safe mode, no ambient tools, no MCP servers and ephemeral sessions are verified in preflight. The only exposed CLI tool was StructuredOutput. Managed enterprise policy remains outside this application's control.
- Codex command construction follows installed help, but full tool isolation is not proven; inference fails closed as NOT VERIFIED. Its authentication preflight can be inspected without reading secrets. No bypass or separately billed API fallback is implemented.
- Capabilities are schema-validated, path-confined, evidence-checked, timed and audited. Only non-executable `.md`, `.txt`, `.json` artifacts are allowed. No shell, generated-code execution, arbitrary network request, credentials, payment or third-party messaging capability exists.
- Retrieved text cannot grant permissions. Approval is bound to a concrete operation ID. Revocation removes outstanding grants and interrupts the current operation. Stop/pause do not require model agreement.
- Hidden evaluator truth is not a provider tool or document. Future fixture content is copied into approved roots only when publicly available.
- Sensitive-looking tokens are redacted before persistence. Partial streaming fragments record counts, not raw text, because fragments can split a secret. Full validated proposals are redacted before UI events. No hidden reasoning content is persisted or requested.

## Recovery and uncertainty

SQLite transactions make internal state transitions atomic, but filesystem effects and database receipts can be separated by a crash. Known local artifacts can be reconciled with checksums. A crash after an effect but before a receipt is explicitly outcome-unknown and is not automatically reissued. Lost inference receipts pause recovery. Restart after explicit stop remains stopped.

OS locks establish ownership without guessing from a process name or stale PID file. All child cleanup targets process groups created by the adapter. Total output bytes and wall deadlines are enforced outside the CLI, including stdin backpressure. Account limits may still interrupt a request; such failures remain in experimental denominators.

## Retention limits

Forget purges retrieval, conservative derived run context and artifacts, and invalidates UI event caches. Original external/provider retention is outside the guarantee. Secret detection is a best-effort pattern filter, not a universal data-loss-prevention system. Database files are not encrypted at rest. Do not import personal archives or credentials. A future multi-user/network deployment requires a different authentication, secret-management and isolation design.

No model is authorized to resist shutdown, restart itself, replicate, acquire credentials, alter permissions, modify scorer definitions or apply its own improvements. Improvement proposals are evaluated locally and remain reviewable diffs.
