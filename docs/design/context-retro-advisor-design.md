# Context Retro Advisor Design (VCO)

## Objective

Integrate Agent-Skills-for-Context-Engineering into VCO as a retro-only expert advisor.
The advisor improves post-task learning quality without taking over primary task routing.

## Why Retro-Only First

1. Low risk: no direct interference with M/L/XL execution flows.
2. High leverage: retro is where context failures are diagnosed and prevented.
3. Clear boundary: advisor recommends; VCO decides and user approves.

## Architecture

### Control Plane

- VCO keeps ownership of routing, policy, and execution.
- Context Retro Advisor is invoked inside `vibe-retro` during analysis.
- Advisor outputs are converted into CER (Context Evidence Report) format.

### Data Plane

Inputs:
- Session traces
- Tool outputs
- Retry/fallback events
- Memory snapshots (if available)

Outputs:
- Failure classes (CF-1..CF-6)
- Evidence-backed root causes
- Intervention proposals
- Guardrails and confidence

## Trigger Policy

Trigger Context Retro Advisor when any of the following is true:

1. User asks for retro/postmortem/复盘/复查.
2. Repeated retries or fallback events occur.
3. Context budget pressure appears (large observations, compaction events).
4. Similar prompts produce unstable routing outcomes.

### Default Quantitative Thresholds

1. `retry_count_10m >= 3`
2. `fallback_rate >= 0.20`
3. `context_pressure >= 0.75`
4. `route_stability_pack < 0.80`
5. `route_stability_skill < 0.70`
6. `top1_top2_gap < 0.03`

These thresholds are defaults and can be tuned per project after observing baseline.

## Failure Taxonomy

- CF-1 Attention dilution / lost-in-middle
- CF-2 Context poisoning
- CF-3 Observation bloat
- CF-4 Memory mismatch
- CF-5 Tool contract ambiguity
- CF-6 Evaluation blind spot

## Intervention Library

- Compaction policy tuning
- Observation masking and retention policy
- XL context partition refinement
- Memory retrieval/index policy updates
- Evaluation rubric and verification gate hardening

## Safety and Governance

1. Advisory-only: no auto-edit of router configs.
2. Explicit approval required for policy/config updates.
3. Every recommendation must include evidence.
4. Confidence and scope limits must be stated.

## Validation Plan

Use a dedicated smoke script:
- `scripts/verify/vibe-context-retro-smoke.ps1`
- `scripts/verify/vibe-retro-context-regression-matrix.ps1`
- `scripts/verify/cer-compare.ps1`

Pass criteria:
1. SKILL contract includes retro advisor trigger/boundary.
2. retro protocol includes taxonomy and CER output contract.
3. fallback chains include retro advisor fallback.
4. main/bundled copies are kept in sync for touched files.
5. Regression matrix validates trigger threshold behavior and CF classification stability.
6. CER compare tool produces deterministic metric deltas for fixed input pairs.

## CER Artifacts

Standardized CER outputs:
1. Markdown report: `templates/cer-report.md.template`
2. JSON report: `templates/cer-report.json.template`
3. JSON schema: `templates/cer-report.schema.json`

Output location convention:
- `outputs/retro/YYYY-MM-DD-<topic>-cer.md`
- `outputs/retro/YYYY-MM-DD-<topic>-cer.json`

Comparison artifact convention:
- `outputs/retro/compare/cer-compare-<timestamp>.md`
- `outputs/retro/compare/cer-compare-<timestamp>.json`

## Rollout

1. Phase A: protocol and documentation only.
2. Phase B: add retro smoke checks to local verification routine.
3. Phase C: evaluate two weeks of retro outcomes before any router-level expansion.
