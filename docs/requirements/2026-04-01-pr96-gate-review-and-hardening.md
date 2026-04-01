# 2026-04-01 PR96 Gate Review And Hardening

- Topic: review PR `#96`, fix the blocking gate failure, and document additional risks surfaced by the runtime-core / skill-catalog split follow-up.
- Mode: interactive_governed
- Goal: restore a passing PR gate for the new `skill-catalog` profile verification without broadening the packaging split into unrelated lock-regeneration work.

## Deliverable

A bounded repair batch that:

1. fixes the blocking `gates` job failure in `scripts/verify/vibe-skill-catalog-profile-gate.ps1`
2. adds regression coverage so the newly introduced gate cannot be referenced by CI while remaining syntactically invalid
3. produces an evidence-backed review of any additional risks uncovered while diagnosing PR `#96`

## Constraints

- Keep the public `minimal` and `full` packaging contract unchanged
- Do not re-couple `skill-catalog` manifests back into runtime freshness truth
- Do not widen this PR into a general bundled-skill lock regeneration unless the new gate fix cannot land safely without it
- Preserve existing review fixes already attached to PR `#96`

## Acceptance Criteria

- `pwsh -NoProfile -File scripts/verify/vibe-skill-catalog-profile-gate.ps1` parses and completes successfully in the canonical repo
- targeted tests cover both workflow wiring and the syntax-sensitive shape of the new catalog gate artifact block
- the PR review summary distinguishes the blocking regression from any pre-existing or adjacent CI debts discovered during diagnosis

## Non-Goals

- regenerating `config/skills-lock.json` for unrelated bundled skill hash drift
- redesigning the whole `gates` workflow orchestration model in this batch
- changing the runtime-core / skill-catalog packaging split semantics beyond what is required for correctness

## Inferred Assumptions

- the current PR gate blocker is confined to the newly added `vibe-skill-catalog-profile-gate.ps1`
- the `offline-skills` hash noise is an adjacent repository debt and must be reported even if it stays outside the smallest safe fix
