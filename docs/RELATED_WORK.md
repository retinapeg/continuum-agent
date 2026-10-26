# Related work and scope

Reviewed on 2026-10-26. This is a targeted primary-source review, not a systematic literature review. Continuum is a controlled research laboratory for comparing attention schedules. The current evidence does **not** establish scientific novelty, optimal scheduling, or a general autonomous-agent advantage.

## Directly relevant research

| Source | Relationship to this experiment |
| --- | --- |
| [SentinelBench: A Benchmark for Long-Running Monitoring Agents (2026)](https://arxiv.org/html/2606.05342v1) | Measures success, reaction time, and resource use in long-running monitoring, including no-operation tasks. Its `wait_for` implementation polls page changes and invokes an LLM on relevant differences. This makes strong event-conditioned baselines and complete accounting of underlying sensing essential. Continuum's physical system gives a narrower environment with numerical ground truth; it does not create a new scheduling problem. |
| [Trimpe and D'Andrea, Event-Based State Estimation with Variance-Based Triggering (2014)](https://is.mpg.de/uploads/publication_attachment/attachment/322/trimpe-TAC14b.pdf) | Triggers measurement transmissions using estimation variance and updates a Kalman estimator. An uncertainty threshold has direct classical precedent. The author-hosted PDF was indexed and its abstract reviewed; a direct PDF fetch returned HTTP 403. |
| [Hajishirzi et al., Greedy Algorithms for Sequential Sensing Decisions, IJCAI (2009)](https://ijcai.org/proceedings/2009/316) | Models change detection as a POMDP with sensing costs, detection-delay costs, detection rewards, and free partial observations. Establishes that costly observation timing and delayed detection already have a decision-theoretic literature. Its guarantees depend on assumptions; they do not transfer automatically to this oscillator. |
| [Memarzadeh and Pozzi, Value of information in sequential decision making (2016)](https://www.sciencedirect.com/science/article/pii/S0951832016300771) | Studies sequential POMDP inspection and monitoring, including fee-based observations. Uncertainty reduction is not itself value of information: information matters through its effect on decisions and future losses. Continuum's heuristic is therefore described as VOI-inspired, not an optimal VOI policy. |
| [Lu et al., Proactive Agent: Shifting LLM Agents from Reactive Responses to Active Assistance (2024)](https://arxiv.org/html/2410.12361v3) | Examines proactive assistance, timing, missed needs, and false detections. Evaluation includes a reward model trained from user judgments. The oscillator instead permits independent numerical scoring; it does not establish the social appropriateness of proactive assistance. |
| [Liu et al., Budget-Aware Tool Use Enables Effective Agent Scaling (2025; revised August 2026)](https://arxiv.org/html/2511.17006v2) | Separates hard tool budgets from consumed resources and supplies explicit budget state to agents. Evaluates resource use including tokens and tools. Continuum likewise exposes equal budget information and reports actual observations, inference, actions, and failures. Search-agent results are not assumed to transfer to dynamical systems. |

## Experimental implications

The following are design recommendations inferred from this literature and the proposed experiment, rather than results reported by those papers.

- Keep model identity, numerical estimator, detector, evidence interface, and resource caps common across schedulers. Identify any policy-specific estimation or detection differences as additional interventions.
- Give event/deadline and fixed-period baselines the same development-tuning allowance as the uncertainty policy. A weak periodic baseline is insufficient evidence of adaptive scheduling benefit.
- Distinguish event-triggered transmission after free sensing from the decision to purchase an observation. No policy may inspect an unpurchased measurement or a hidden change flag to decide whether to observe.
- Generate world dynamics and noise independently of action order. The same world seed must yield the same latent trajectory and the same available measurement at a given simulated timestamp across competing policies.
- Score fixed-horizon predictions on the same fixed grid, including sleeping periods. Exclude forecasts without a full future target, and report prediction coverage so abstention cannot silently improve error.
- Freeze development and held-out seeds, scenario families, estimator assumptions, costs, thresholds, detection windows, and scoring before held-out evaluation. Preserve the frozen manifest and all failures.
- Match alerts to changes one-to-one within a declared window. Repeated alerts cannot count as repeated detections. Report missed changes alongside conditional delay; use a declared censored-delay summary rather than dropping misses.
- Include genuine no-change episodes and report false alarms there separately. Public events must be independent of hidden changes; they are opportunities to reconsider, not ground-truth hints.
- Treat stale evidence as timestamped evidence. Reject it or use a declared out-of-sequence update; do not assimilate it as a current measurement. Contradictory measurements must remain visible in provenance.
- Report Gaussian interval coverage and negative log likelihood as empirical outcomes. Covariance can be confidently wrong after an unmodelled parameter shift; uncertainty estimates are not guarantees.
- Specify which numerical operations are shared fixed overhead and which consume inference budget. Free posterior updates on every tick would undermine the intended comparison of when to think.
- A freely damped oscillator can approach zero before late changes, making prediction easy and changes hard to identify. Document signal amplitude and observability, or provide sustained known forcing/appropriate low damping. A zero-prediction reference helps expose this failure mode.
- A typed Python information boundary prevents accidental leakage; it is not a sandbox against malicious policy code using introspection or filesystem access.
- Live model calls add service-time variability. Keep simulated time and wall-clock latency separate, retain failed calls, and never treat a repeated live call as deterministic replay.

## Preserved negative result

The prior Continuum experiment found **55.56% task completion for both the hybrid and event/deadline policies** across **180 live Claude-backed episodes**. Hybrid used **6.00 CLI invocations per episode versus 5.11** for the baseline. The reported paired completion difference was **0 percentage points**, with a **95% interval of [−11.11, +11.11]**. This did not demonstrate a completion advantage from continuous state. See the preserved [morning report](../MORNING_REPORT.md) and [original protocol](../EXPERIMENT_PROTOCOL.md).

New oscillator results concern a different task. They cannot erase that negative result or establish general benefits for personal assistants, orchestration, or multi-agent communication.
