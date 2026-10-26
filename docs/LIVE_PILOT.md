# Bounded live trigger validation

The user requires explicit opt-in before inference. No live invocation is authorised by merely opening the laboratory. The installed CLI flag probe is in `experiments/v1/claude-cli-probe.json` and made no authentication or inference calls.

Concrete pilot: three independently presented public states from the development seed-0 change world, event/deadline policy, observation/update caps 12, at simulated seconds 0, 45 and 80. Only `experiments/v1/live-public-contexts.json` crosses the provider boundary. It contains prior beliefs, received observations, remaining budgets and public events; no ground truth, seed, change schedule or hidden parameters.

Use the existing Claude subscription CLI and exact model `claude-haiku-4-5-20251001`. At most three provider attempts, 25 seconds per inference, 90 seconds overall plus bounded process cleanup. Subscription verification is read-only. No authentication changes, API-key fallback, tools or model-proposed effects. The existing CLI proposal schema is reused; only a short decision summary and next observation delay are accepted. Proposed actions/memories/messages invalidate the response and remain in failure receipts.

```sh
.venv/bin/python -m continuum.lab.live pilot \
  --contexts experiments/v1/live-public-contexts.json \
  --directory experiments/v1/live-pilot-001 \
  --model claude-haiku-4-5-20251001 --max-calls 3 \
  --deadline-seconds 90 --opt-in
```

This pilot tests CLI compatibility, structured trigger proposals, model identity and receipt accounting on fixed inputs. It does not measure closed-loop prediction performance or establish an LLM scheduling advantage. Classical estimation stays the numerical reference. Every attempted, failed, known-unsent and uncertain invocation is distinguished; usage and CLI-reported cost estimates are retained where available. Actual subscription charges remain unknown. An existing pilot directory cannot be reused or overwritten.
