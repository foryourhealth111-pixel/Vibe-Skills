# Linux Router Host-Neutrality And Route Quality Recovery Requirement

## Goal

Recover VCO platform compatibility and route quality as one governed program so that:

- Linux without `pwsh` no longer loses core routing capability
- common prompts stop over-falling into `confirm_required`
- planning and migration prompts route into the correct candidate family
- remaining Windows-path leakage is reduced to non-authoritative hygiene debt

## Why This Requirement Exists

The current repo has four coupled problems that cannot be treated as isolated bugs:

1. Linux without `pwsh` still lacks an authoritative router execution path.
2. Route policy is too conservative and pushes common prompts into `confirm_required`.
3. Planning and migration prompts can rank into the wrong packs.
4. Windows-first path assumptions still leak into non-core surfaces and muddy platform truth.

These problems affect:

- stability
- usability
- route intelligence
- operator trust in release truth

## Frozen Scope

This governed run covers:

- host-neutral router contract extraction
- Linux no-`pwsh` router authority recovery
- route threshold and guard tuning for common prompts
- planning and migration prompt rerank repair
- cleanup of remaining non-authoritative path leakage
- proof, promotion, and rollback-ready release truth

## Non-Goals

This governed run does not allow:

- dual-fork Windows and Linux codebases
- platform-specific canonical routing semantics
- unproven release promotion language
- silent threshold changes without replay and proof coverage
- docs-only claims of compatibility without installed-runtime evidence

## Required Architecture Direction

The recovery must follow one architectural direction only:

- single canonical router semantics
- platform differences isolated to adapters
- proof split into stability, usability, and intelligence families
- release truth derived from proof, not from narrative

Rejected alternative:

- separate Linux edition and Windows edition

Reason:

- that would duplicate truth, increase drift risk, and weaken no-regression guarantees

## Acceptance Criteria

### Stability

- Linux without `pwsh` can invoke the router through a host-neutral adapter and return the canonical route JSON schema.
- Windows authoritative PowerShell routing remains green.
- Installed-runtime route closure works under fresh temp roots and real target roots.

### Usability

- A curated set of common safe prompts no longer defaults to `confirm_required` at the current failure rate.
- `legacy_fallback_guard` is no longer the dominant reason for common prompt outcomes.

### Intelligence

- Planning, migration, and governance prompts rank into the intended candidate family with measurable improvement against a frozen gold set.
- Improvements are stable across Windows and Linux adapters.

### Release Truth

- Promotion, proof, and release documents do not overstate Linux support.
- Platform status, proof bundle content, and release notes agree with each other.

## Required Proof Families

The implementation is not complete until all of the following are green:

1. stability proof
2. usability proof
3. intelligence proof
4. release-truth consistency proof

## Traceability

Primary execution-plan leaves for this historical recovery wave are no longer kept on the public docs surface.

Primary supporting truth surfaces expected to stay aligned:

- [platform-support-policy.json](../../config/platform-support-policy.json)
- [router-thresholds.json](../../config/router-thresholds.json)
- [ai-rerank-policy.json](../../config/ai-rerank-policy.json)
- [exploration-policy.json](../../config/exploration-policy.json)
- [resolve-pack-route.ps1](../../scripts/router/resolve-pack-route.ps1)

## Change Control Rules

- Any scope expansion must update this requirement first.
- Any threshold change must ship with replay evidence.
- Any Linux promotion statement must be backed by proof artifacts, not by partial smoke success.
- Any cleanup of path leakage must preserve runtime behavior and be verified on both Windows and Linux lanes.
