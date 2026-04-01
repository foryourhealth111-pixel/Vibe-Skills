# 2026-04-01 PR96 Gate Follow-up Closure

- Topic: close the two residual risks left after PR `#96` gate repair: workflow exit-code masking and stale / platform-unstable bundled skill lock hashing.
- Mode: interactive_governed
- Goal: make the `gates` workflow fail honestly when a sub-gate fails, and restore `skills-lock` / offline-skills verification to a deterministic cross-platform state.

## Deliverable

A bounded follow-up batch that:

1. hardens the GitHub Actions `gates` step so each invoked PowerShell gate must propagate its non-zero exit status
2. makes bundled skill directory hashing deterministic across platforms
3. refreshes `config/skills-lock.json` from the canonical generator after the hashing fix
4. adds regression coverage for both the workflow exit-propagation contract and the deterministic lock-generation behavior

## Constraints

- Keep the runtime-core / skill-catalog split semantics unchanged
- Do not weaken `offline-skills` detection just to make the gate green
- Preserve `skills-lock` as a bundled-skill manifest rather than inventing a new lock format
- Keep the repair batch focused on the identified workflow and hashing debts

## Acceptance Criteria

- the `gates` workflow step explicitly fails when any invoked sub-gate exits non-zero
- `scripts/verify/vibe-generate-skills-lock.ps1` and `scripts/verify/vibe-offline-skills-gate.ps1` compute bundled skill directory hashes deterministically across Windows and Linux ordering behavior
- `config/skills-lock.json` matches the current canonical bundled skill corpus after regeneration
- local verification proves both the workflow contract and offline-skills lock contract

## Non-Goals

- redesigning the entire GitHub Actions layout
- changing pack routing, runtime packaging, or skill-catalog profiles beyond the lock/hash follow-up
- adding new bundled skills or removing existing ones

## Inferred Assumptions

- `Sort-Object FullName` is the source of the Windows/Linux hash drift for mixed-case skill directories
- `timesfm-forecasting` is a genuine stale lock entry rather than a gate false positive
