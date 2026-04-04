# Skills Consolidation Roadmap (VCO-Centered)

## Objective

Consolidate scattered skills into a small number of domain packs, then route all pack execution through `vibe` with deterministic quality gates and safe fallback to existing routing.

## Scope

- In scope:
  - Pack definition and routing overlay for `vibe`
  - Alias compatibility for legacy skill names
  - Verification scripts and phase acceptance checks
- Out of scope:
  - Rewriting third-party plugin source code
  - Removing existing fallback chains
  - Breaking existing explicit-command behavior

## Current Baseline

- Skill files under `skills/`: 243
- Active skill files excluding `tmp/`: 260
- Duplicate frontmatter names: 19 groups
- Known hot spots:
  - `code-review`: 5 variants
  - `xlsx`: 2 variants
  - `vibe/bundled/*` overlap with top-level skills

## Target State

- Public entry skills reduced to `<= 35`
- Duplicate-name groups reduced to `0`
- `vibe` performs:
  - grade routing (`M/L/XL`)
  - task-type routing (`planning/coding/review/debug/research`)
  - pack routing overlay (new)
  - skill ranking inside selected pack (new)
  - fallback to legacy matrix when confidence is low

## Phase Plan

### Phase 0: Governance Baseline

- Deliverables:
  - this roadmap
  - routing config skeleton (`pack-manifest`, `alias-map`, `thresholds`)
- Acceptance:
  - config files exist and pass parse checks
  - no existing routing behavior changed yet

### Phase 1: Pack Router Scaffolding

- Deliverables:
  - pack definitions with grade/task boundaries
  - score thresholds and safety constraints
  - alias map for duplicate and legacy names
- Acceptance:
  - `vibe-pack-routing-smoke.ps1` passes
  - all required packs present
  - no alias loops

### Phase 2: VCO Documentation Integration

- Deliverables:
  - `SKILL.md` adds Pack Router overlay
  - conflict/fallback/extending references updated
- Acceptance:
  - docs reference config paths consistently
  - explicit command priority unchanged

### Phase 3: Incremental Skill Migration

- Deliverables:
  - batch migration by domain
  - each batch includes pre/post inventory diff
- Acceptance:
  - per batch rollback plan validated
  - duplicate count monotonically decreases

### Phase 4: Compatibility Convergence

- Deliverables:
  - legacy aliases retained for transition window
  - deprecation warnings cataloged
- Acceptance:
  - high-frequency legacy aliases remain stable
  - no critical route breakage in smoke tests

### Phase 5: Cleanup and Freeze

- Deliverables:
  - deprecated duplicates removed after window
  - final inventory and governance report
- Acceptance:
  - target metrics met
  - all smoke scripts pass

## Quality Gates

- Gate A (design): scope, boundaries, rollback defined
- Gate B (implementation): config valid, no rule conflicts
- Gate C (verification): scripts pass, outputs reviewed
- Gate D (release): migration report and residual risks published

## Rollback Strategy

- Keep legacy matrix routing always available during migration.
- If pack confidence < threshold or any config error, route to legacy matrix.
- Preserve alias mappings until post-migration stability is confirmed.

## Reporting Cadence

- Per phase:
  - changed files list
  - verification commands and outputs
  - decisions and unresolved risks
