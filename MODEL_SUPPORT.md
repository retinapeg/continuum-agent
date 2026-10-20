# Model support and accounting

Verified locally on 20 October 2026. Provider integrations use installed subscription CLIs; no separately billed API adapter is enabled. Exact identifiers are configuration values, not display-name guesses.

| Adapter | Installed version | Authentication | Status |
|---|---|---|---|
| Deterministic fixture | rules-v2 | none | Locally tested control; not an LLM |
| Claude Code | 2.1.236 | `claude.ai`, Max subscription status | Live structured preflights verified for `claude-sonnet-4-6` and `claude-haiku-4-5-20251001` |
| Codex CLI | 0.163.0 | `codex login status` reports ChatGPT | Command adapter implemented; inference **disabled / NOT VERIFIED** because complete ambient-tool isolation has not been established |

The initial Sonnet preflight was labelled NOT VERIFIED because it treated auxiliary Haiku accounting as a model switch. That receipt remains preserved. A corrected preflight verified the main assistant identity separately from auxiliary usage. Main-model switches remain errors; a CLI classifier is recorded as auxiliary work rather than silently relabelled.

Claude commands use supported installed flags: safe mode, empty built-in tools, strict empty MCP configuration, no slash commands, no Chrome, no session persistence, empty settings sources, a strict proposal schema and streaming JSON. Initialization must explicitly report a tool list containing only StructuredOutput, and assistant messages must report the requested main identity. `--bare` is deliberately avoided because the installed help says it skips subscription OAuth/keychain authentication. Existing login homes are preserved; no authentication file is copied or inspected. Subscription status is revalidated at least once per 60 seconds of provider reuse, before a subsequent invocation; API-key environment overrides remain stripped on every invocation.

Codex exec supports ignoring user config while retaining authentication, read-only sandboxing and many tool-disabling configuration switches. These do not independently prove that every tool, managed integration or filesystem read is removed. The adapter therefore fails before inference with a known-unsent isolation error. A future verified tool inventory or independently enforced sandbox is required. It does not fall back to an API or weaker isolation.

## Bounded process execution

Adapters use argv arrays and a restricted inherited environment. They stream progress counts as bytes arrive; complete proposals become readable UI events after redaction. Partial text is not retained because secrets can straddle chunks. Hidden reasoning is neither requested nor recorded. Nonblocking stdin prevents a child that does not read input from bypassing the deadline. A real byte counter covers stdout plus stderr; token limits are requested separately. Cancellation/deadline signals only the owned process group, including descendants after leader exit. Cleanup permission errors are recorded as warnings with descendant cleanup marked unverified, rather than concealing the primary outcome. The combined stdout/stderr bound is 1,000,000 bytes; the earlier pilot cap of 180,000 bytes caused observed stream-framing failures.

Timeout after send is outcome-unknown. A missing executable, unavailable subscription or rejected isolation preflight is known-unsent. There are no automatic CLI request retries in scientific campaigns. CLI-internal retry behavior may be opaque and is bounded by the external wall deadline.

## Usage and money

The final Claude `usage` object can cover the main model while `modelUsage` additionally includes an auxiliary classifier. The adapter retains primary usage separately, labels aggregate source `modelUsage_aggregate`, then aggregates each reported model row once for total uncached input, cached reads, cache creation and output. It never adds those rows to the final cumulative usage again. Missing categories remain null.

CLI-provided `costUSD` values are labelled **API-equivalent estimates**, with the CLI as the rate source, rate date unknown and USD as estimate currency. They are not subscription invoices. Actual account charges are unobserved and remain null. Development preflight/model-build receipts are separate from experimental episode receipts. Parent coding-session usage was not captured and is not estimated.

The frozen campaign used accounting calculation version 1, which discarded available terminal-error usage and usage from responses discarded after a control change. Its missing totals remain unknown; no historical trial was rerun or backfilled. The post-campaign repair uses version 2: the same normalization handles success and error results, cancelled proposals retain accounting without executing, and a reported terminal total is used only if per-model costs are unavailable. It is never added to per-model totals. Nine regression tests and a fresh **5.727-second live Claude preflight** passed. [Repair receipt](evidence/build/accounting-repair-applied.json) · [Live preflight](evidence/build/post-campaign-preflight.json).

One recorded call is an attempted CLI invocation, not necessarily one inference request. The CLI can perform internal retries or auxiliary inference. Known call-level usage subtotals, missing coverage and unknown complete totals are published separately in the final campaign's [usage coverage](experiments/v02/live-heldout-v1/usage-coverage.json).

## Routing

`config/routing.example.json` contains inspectable task classes, exact models, live-verification flags and observed valid-response counts. A smoothed reliability estimate `(valid+1)/(attempts+2)` ranks eligible candidates, with deterministic ties. The example has only preflight observations and is not evidence of comparative task quality. Known-unsent fallback is off by default. Outcome-unknown calls are never automatically routed again. Router decisions log candidate set, chosen model, reason, attempt, fallback and prior timestamp. Main scientific comparisons use a fixed provider/model, not this router.

## Official references checked

- [Codex noninteractive execution](https://developers.openai.com/codex/noninteractive/)
- [Codex authentication](https://developers.openai.com/codex/auth/)
- [Codex configuration reference](https://developers.openai.com/codex/config-reference/)
- [Codex exact model identifiers](https://developers.openai.com/codex/models/)
- [Claude CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Claude model configuration and subscription caveats](https://code.claude.com/docs/en/model-config)
- [Claude usage accounting](https://code.claude.com/docs/en/agent-sdk/cost-tracking)

Installed help was checked alongside documentation because current documentation can describe flags absent from the installed release. No claim of support is based solely on a newer documentation page.
