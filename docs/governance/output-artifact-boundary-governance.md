# Output Artifact Boundary Governance

## Goal

`outputs/**` is for runtime artifacts. `references/fixtures/**` is for governed baseline material.

The repository still carries historical tracked outputs because some comparison workflows depend on them. Wave123 turns that legacy state into an explicit migration contract instead of silent drift.

## Current Boundary

- `outputs/**`: generated at runtime, should remain untracked unless explicitly allowlisted as historical carry-over.
- `references/fixtures/**`: governed baseline fixtures used for retro-compare, routing stability, or external-corpus regression reference.

## Stage Plan

### Stage 1 — Explicit Registry

- register legacy tracked outputs in `config/outputs-boundary-policy.json`;
- forbid any new tracked output outside the allowlist;
- keep migration targets explicit.

### Stage 2 — Fixture Migration

Wave123 advances the repo to **Stage 2 — Fixture Migration**:

- baseline copies are mirrored into `references/fixtures/**`;
- policy declares `migration_stage = stage2_mirrored`;
- `migration-map.json` records source -> fixture copy coverage;
- tracked outputs may still exist temporarily, but the fixture boundary is now explicit.

Required terms for this stage:

- `references/fixtures/**`
- `stage2_mirrored`
- `strict_requires_zero_tracked_outputs`

### Stage 3 — Strict Mode

- remove the remaining tracked historical outputs;
- set `strict_requires_zero_tracked_outputs = true`;
- make `git ls-files outputs` return zero.

## Enforcement

`scripts/verify/vibe-output-artifact-boundary-gate.ps1` must verify:

- tracked outputs remain fully allowlisted;
- disallowed runtime roots are not tracked;
- policy count stays aligned with the tracked legacy set;
- stage2 mirrored fixture copies exist under the declared fixture roots.
