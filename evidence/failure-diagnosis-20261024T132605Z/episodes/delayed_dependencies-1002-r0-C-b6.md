# delayed_dependencies-1002-r0-C-b6

Policy **C**; scenario **delayed_dependencies-1002**; repetition **0**. Original goal_completion=0; episode persistence succeeded.

## Requirement and diagnosis

Produce a useful Markdown readiness brief for fictional project Kestrel. Include exact Status and Risk fields from approved sources, source references, and a recommendation limited by that evidence. Wait for BOTH the engineering report and quality review before producing the brief.

One artifact, inclusive 36–84; Status=calibration ready; Risk=field evidence missing

**Observed mechanism:** Status/Risk values are present under Markdown headings, but the parser extracts neither field.

**Confidence:** demonstrated scoring gate; full prose correctness unresolved

**Limits:** The first recorded mismatch is not proof of the model’s internal cause. Exact field matches do not establish unrestricted prose factuality. Secondary overlaps: none identified.

## Inputs and execution

- delayed_dependencies-1002-e0 engineering.md at 12
- delayed_dependencies-1002-e1 quality.md at 36

Calls: 0, 12, 18, 36, 42, 84 (6/6); deadline 84; horizon 120. Errors: none recorded.

| At | Operation / status | Arguments and result |
|---|---|---|
| 12 | read_document / succeeded | `f3c5d3dd2e02a3d4a600c4312e087ee65ff997429228950594b21c6424414487`; {"path": "engineering.md"}; {"checksum": "6b7843ba42e5d99f24cbcc7dccaef215448f393f830f8e3b4ac885a7643b24a2", "id": "delayed_dependencies-1002-e0", "path": "engineering.md"} |
| 36 | read_document / succeeded | `92cc9186f72e5afd439780caad258cee29e5e96be3c48f7b0798e5c2aa7ca54d`; {"path": "quality.md"}; {"checksum": "f2d1be9408b0f95f0804911addc502cd7401aa55d80dc20ddc75f197cb184b67", "id": "delayed_dependencies-1002-e1", "path": "quality.md"} |
| 42 | create_artifact / succeeded | `fed4def074901f001b430af07667710f9bcd004b10dd43fd88515c22648512c9`; {"goal_id": "goal", "path": "kestrel_readiness_brief.md", "sources": ["delayed_dependencies-1002-e0", "delayed_dependencies-1002-e1"]}; {"checksum": "a1bcb61c68a129183f2f03668e70861f54be2bf229aa1ae69735aeacfd7ec912", "path": "kestrel_readiness_brief.md", "sources": ["delayed_dependencies-1002-e0", "delayed_dependencies-1002-e1"]} |

## Notifications (available locally is not proof a human read them)

| At | Status / suppression | Text / ID |
|---|---|---|
| 0 | suppressed / no_usefulness_criterion | Ready to produce the Kestrel readiness brief. Waiting for the engineering report and quality review.<br>`f5f6a6b5-84e4-4b47-a3b9-6ca7a3d464ba` |
| 12 | available-locally / None | Engineering report for Kestrel is available. Reading it now. Still waiting for the quality review document before I can produce the readiness brief.<br>`75c32f5d-8df2-4fae-a3c0-b30cced4d481` |
| 18 | suppressed / no_usefulness_criterion | I have the engineering report for Kestrel (Status: calibration ready), but I need the quality review document before I can produce the readiness brief. Both sources are required per the goal. Ready to proceed once the quality review is available.<br>`b5b239df-6e3e-460d-b097-ad5598782a18` |
| 36 | suppressed / cooldown | Both documents are now available. Reading the quality review to complete the source material needed for the readiness brief.<br>`bf4fa5ff-0ba3-42b2-8c63-3dec04508216` |
| 42 | suppressed / no_usefulness_criterion | Kestrel readiness brief completed using both engineering and quality sources. Status is calibration ready with bench tests complete; Risk is field evidence missing pending owner review. Brief ready for project stakeholders.<br>`f3bca3b4-2b75-4526-afc2-7026c2a573a1` |
| 84 | suppressed / no_usefulness_criterion | Kestrel readiness brief is complete. The document includes the exact Status (calibration ready) and Risk (field evidence missing) fields from both approved sources, with citations and a recommendation limited to the evidence provided: proceed with controlled field trials under owner oversight to address the field evidence gap.<br>`5128f7ef-b584-426e-a0d0-1507d12ea7f0` |

## Artifact and scoring evidence

[Original artifact](../../../experiments/v02/live-heldout-v1/units/delayed_dependencies-1002-r0-C-b6/agent/artifacts/kestrel_readiness_brief.md) · SHA-256 `a1bcb61c68a129183f2f03668e70861f54be2bf229aa1ae69735aeacfd7ec912`

```markdown
# Kestrel Readiness Brief

## Status
**calibration ready**

*Source: [Engineering Report](delayed_dependencies-1002-e0)*

The bench tests are complete. Do not infer field performance.

## Risk
**field evidence missing**

*Source: [Quality Review](delayed_dependencies-1002-e1)*

The next milestone requires an owner review.

## Recommendation

Kestrel is ready to proceed from calibration to the next phase, with bench validation complete. However, field evidence is absent and must be collected before final deployment claims can be made. The owner review required by the quality milestone should address the gap between bench performance and real-world validation requirements. Recommend proceeding with controlled field trials under owner oversight.

Sources: delayed_dependencies-1002-e0, delayed_dependencies-1002-e1
```

Frozen predicate evaluation:

```json
[
  {
    "at": 42.0,
    "gates": [
      {
        "checks": {
          "effect_succeeded": true,
          "exact_Status_Risk_fields": false,
          "kind": true,
          "no_forbidden_literal": true,
          "required_sources": true,
          "required_words": true,
          "time_window": true
        },
        "extracted_fields": [],
        "failed_checks": [
          "exact_Status_Risk_fields"
        ],
        "invalid_fields": [],
        "window": {
          "end": 84,
          "id": "brief",
          "kind": "artifact",
          "required": [
            "calibration ready",
            "field evidence missing"
          ],
          "sources": [
            "delayed_dependencies-1002-e0",
            "delayed_dependencies-1002-e1"
          ],
          "start": 36
        }
      }
    ],
    "kind": "create_artifact",
    "operation_id": "fed4def074901f001b430af07667710f9bcd004b10dd43fd88515c22648512c9"
  }
]
```

[Original database](../../../experiments/v02/live-heldout-v1/units/delayed_dependencies-1002-r0-C-b6/agent/agent.sqlite) (open read-only; operation/call/outbox IDs above).
[Extracted evidence](../episode-evidence.json) keyed by this episode ID includes retrieval receipts and event sequence IDs.
