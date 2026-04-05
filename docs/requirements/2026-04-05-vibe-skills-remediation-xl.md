# Vibe-Skills Remediation XL Requirement

Date: 2026-04-05
Run ID: 20260405-vibe-skills-remediation-xl
Mode: interactive_governed
Runtime lane: root_governed

## Goal

Implement the approved remediation plan for the audited repository issues in an XL governed wave, restoring verification credibility, reducing semantic duplication, making Python execution hermetic, and reconciling stale topology assertions without regressing behavior.

## Deliverable

An implementation set that:

- fixes the currently observed failing invariants
- keeps semantic ownership centralized
- preserves cross-platform and compatibility behavior
- leaves behind fresh verification evidence and cleanup receipts

## Constraints

- Work only within the frozen remediation scope
- Preserve thin-wrapper boundaries and avoid reintroducing local semantic truth copies
- Use TDD or existing failing tests as the red phase before production edits
- Keep child agents bounded and prevent overlapping write scopes
- Clean node/process and temp artifacts at the end of each major phase

## Acceptance Criteria

- CI Python validation surface covers the previously missed failing invariant classes
- `scripts/common/runtime_contracts.py` no longer owns duplicated runtime-surface semantics
- Python validation can run without leaving repo-owned bytecode residue
- Repo topology contract matches current architecture truth
- Focused verification passes, followed by broader regression evidence

## Product Acceptance Criteria

- Repository cohesion increases: contracts own contract semantics, verification owns verification policy, wrappers remain thin
- Coupling decreases: fewer fallback duplicates, fewer stale topology literals, fewer environment-sensitive side effects
- User-facing behavior and compatibility surfaces remain intact

## Manual Spot Checks

- CI target list includes the repaired failing invariant tests
- No `__pycache__` / `.pyc` residue remains under `apps`, `packages`, `scripts`, `tests` after verification
- Runtime contract consumers still import from the shared contracts package

## Completion Language Policy

- Only claim completion after focused verification, broader regression, cleanup, and node audit are recorded
- If any fix is partial or degraded, state that explicitly

## Delivery Truth Contract

- Implementation engagement
- Evidence before assertions
- No silent no-regression claims

## Non-Goals

- Unrelated feature work
- Large-scale architecture redesign beyond the frozen remediation wave
- Removing compatibility shims that still have active contractual callers

## Autonomy Mode

interactive_governed with unattended execution approved by the user

## Inferred Assumptions

- The user has approved the remediation design and wants end-to-end autonomous execution
- The current failing tests are sufficient red-phase anchors for most fixes
- Additional targeted tests may be added where workflow or execution behavior lacks adequate coverage
