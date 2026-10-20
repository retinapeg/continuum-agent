# Future research

The v0.1 simulator is preserved. v0.2 now implements a persistent local runtime, lexical belief memory, a real Claude subscription adapter, local chat, controlled capabilities and paired synthetic experiments. The items below are **unimplemented research**, not advertised product features.

## Broader LLM research

Test unseen task generators, longer dependencies and realistic document corpora with independently adjudicated prose accuracy. Expand beyond the six current templates and fixed primary model. Separate retrieval, activation timing and state-feature interventions. Learn parameters only after labelled data justify the additional complexity; neural ODEs are not a prerequisite for persistence. Embeddings must compete against the inspectable lexical baseline with retrieval receipts and deletion tests.

Codex inference remains disabled until complete tool isolation can be demonstrated with the installed subscription CLI or an independently enforced sandbox. A configured command is not a verified integration. Multi-day live-model soak, portable process isolation, database migrations and robust external-effect reconciliation remain future work.

## A2A and MCP

The implemented `leo.integration.v1` schema and loopback HTTP stub are a project-local envelope, **not an A2A implementation**. There is no actual Leo OS or Agent Exchange connection. Future adapters should map task lifecycle, cancellation, authorization and artifact receipts to then-current [A2A](https://a2a-protocol.org/latest/specification/) and [MCP](https://modelcontextprotocol.io/specification/latest) contracts after checking their specifications.

Start with mock peers, duplicate delivery, delayed outcomes and cancellation races. Add actual peers only with bounded delegation and explicit owner grants. Retrieved peer content must never grant capabilities. No external MCP server or delegation endpoint is enabled today.

## HTTP 402 / x402 payments

Unimplemented: a synthetic paid-resource experiment with a fake ledger, deterministic quotes and synthetic balances. Measure verified utility per unit spent and preserve uncertainty after ambiguous settlement. A future real implementation would require current protocol/security review, explicit spending limits and owner authorization. There is no wallet, signing key, payment client, transaction or live settlement in this repository.

## Privacy-preserving matchmaking

Unimplemented: synthetic collaborator matching with a plain local baseline, explicit threat model and minimum necessary attribute disclosure. Candidate research includes selective disclosure, private set intersection and aggregate differential privacy. None is selected or implemented. Evaluate match quality, inference attacks, consent revocation, retention and disclosure volume together. Removing names or using embeddings does not establish a privacy guarantee.

## Improvement and promotion

The implemented improvement cycle evaluates a bounded configuration copy on development fixtures and queues a diff. It never applies that diff to the service. Future promotion requires fresh evaluation after test exposure, stronger independent review and owner approval. Permission rules, scorer definitions and original evidence must remain outside model-editable scope.

Persistence means durable software state and continued authorized work. It does not imply consciousness, subjective experience, uninterrupted neural inference or a reason to resist shutdown.
