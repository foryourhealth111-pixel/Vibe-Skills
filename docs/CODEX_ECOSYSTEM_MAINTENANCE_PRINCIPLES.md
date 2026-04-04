# Codex VCO Ecosystem Maintenance Principles

Status: Active
Audience: Maintainers of Codex-compatible VCO ecosystem
Invocation: Documentation only. This file is not a callable skill and must not be referenced from SKILL routing paths.

## 1. Purpose

Define a stable, compatibility-first maintenance system for the Codex VCO ecosystem, where many dependencies are manually adapted for Codex behavior and cannot be replaced by raw upstream content.

## 2. Scope

This policy governs:
- `bundled/skills/*`
- workflow/compatibility skills that also live under `bundled/skills/*`
- `rules/*`
- `hooks/*`
- `agents/templates/*`
- `mcp/*`
- `config/*` dependency and lock manifests
- install/check scripts

## 3. Core Axioms

1. Local Codex rewrites are authoritative.
2. Upstream repositories are sources for reference, not direct replacement.
3. Compatibility is a product requirement, not an afterthought.
4. Every change must be reproducible, reversible, and reviewable.

## 4. Compatibility Contract

### 4.1 Source of truth

- Runtime source of truth is local bundled content.
- Upstream references in lock files are traceability metadata.
- If local and upstream conflict, local compatible behavior wins until explicitly migrated.

### 4.2 No blind sync rule

Never overwrite `bundled/*` with upstream files without manual compatibility review.

### 4.3 Explicit adaptation boundary

Each adapted dependency must document:
- upstream origin
- adaptation intent
- known behavior deltas
- rebase strategy

## 5. Change Classification and Release Discipline

### 5.1 Change classes

- Class A: Documentation-only
- Class B: Non-routing config/rule updates
- Class C: Skill behavior updates (potentially breaking)
- Class D: Installer/runtime orchestration updates
- Class E: Cross-cutting compatibility migration

### 5.2 Required release level

- Class A/B: patch
- Class C/D: minor
- Class E: minor or major depending on migration burden

## 6. Dependency Lifecycle

For each external project (superpowers, ralph, SuperClaude, claude-code-settings, spec-kit, claude-flow):

1. Observe upstream changes.
2. Triage impact against Codex compatibility contract.
3. Adapt in local bundled copy.
4. Verify against compatibility matrix.
5. Update lock metadata.
6. Release with migration notes.

## 7. Verification Gates

No merge without all gates passing:

1. Structural gate
- install script succeeds in clean target
- check script reports no hard failures

2. Compatibility gate
- core orchestration skills are present and routable
- adapted dependencies remain internally consistent

3. Safety gate
- write guard passed for md/txt writes
- secret scan passed
- JS/TS console guard passed or intentionally annotated

4. Regression gate
- no unintended change to protocol routing semantics
- no destructive behavior introduced in install/update scripts

## 8. Version and Lock Management

- Maintain `config/upstream-lock.json` for source traceability.
- Maintain `config/dependency-map.json` for local sync map.
- Any dependency update requires lock update in the same change set.
- If compatibility behavior changes, include migration section in changelog.

## 9. Documentation Requirements

Every compatibility-impacting change must include:
- rationale
- impacted dependencies
- expected behavior change
- rollback method
- operator validation commands

## 10. Rollback and Incident Policy

For broken releases:

1. Freeze dependency sync.
2. Revert to last known good commit.
3. Publish incident note with root cause and containment.
4. Patch with focused compatibility fix.

## 11. Ownership and Review

Minimum review model:
- one compatibility reviewer
- one installer/runtime reviewer

For Class D/E changes, require both reviewers explicitly sign off.

## 12. Operational Checklists

### 12.1 Pre-merge checklist

- Updated locks and dependency map if needed
- install/check smoke passed
- guards passed
- docs updated

### 12.2 Post-merge checklist

- verify branch is clean
- verify GitHub default install path still works
- record follow-up tasks for deferred upstream rebases

## 13. Anti-Patterns

- copying upstream wholesale into bundled runtime paths
- changing multiple dependency families without staged verification
- silent behavior changes without migration notes
- treating optional tools as mandatory at install time

## 14. Local and Remote Sync Rule

- Local skills path and GitHub repository must be synchronized intentionally.
- Use controlled sync scripts and avoid ad hoc manual drift.
- If divergence is required temporarily, open a tracking issue and set an expiry.

## 15. Definition of Done for Ecosystem Maintenance

A maintenance task is done only when:
- local bundled compatibility is correct
- repository lock metadata is updated
- install/check flows pass in clean environment
- policy and migration notes are documented
