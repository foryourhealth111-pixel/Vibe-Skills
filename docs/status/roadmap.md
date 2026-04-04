# Roadmap

Updated: 2026-04-04

## Positioning

This page is the sequencing map for the active `remaining-architecture-closure` program.

It answers:

1. which closure wave is active now;
2. which heavier cleanup tracks remain deferred;
3. what must become true before the repository can honestly claim closure.

It is not the proof contract, not the blocker census, and not the completion receipt.

## Operating Rule

Every closure wave still runs under one rule:

**no proof, no completion claim**

That means no semantic-owner retirement, no compatibility-surface deletion, and no broad cleanup claim until the replacement owner exists and fresh verification evidence is in hand.

## Active Track

The repository is in **architecture-closure mode**, not feature-expansion mode.

That means the current priority is:

1. remove or demote remaining duplicated semantic owners
2. keep contracts and package-owned cores as the canonical owners
3. refresh live status / closure surfaces so they match current evidence
4. only then move into the final proof-and-cleanup wave

## Current Closure Waves

### Wave 1: Remaining Owner Audit

Goal: identify the remaining script-text truth checks, fallback owners, and compatibility boundaries worth cutting.

Status: completed enough to rank the current microphases and drive the 2026-04-04 cut sequence.

### Wave 2: High-Value Contract Cutovers

Goal: move the highest-value remaining semantic owners onto shared contracts or package-owned cores.

Completed cuts in this wave include:

- frontmatter gate runtime-contract delegation
- CLI runtime entrypoint delegation
- verification runtime entrypoint delegation
- operator preview postcheck contract alignment
- PowerShell installed-runtime fallback reduction
- mirror-topology contract delegation
- release closure gates contract cutover

### Wave 3: Compatibility Boundary Closure

Goal: keep fallbacks and retained shims bounded, explicit, and non-authoritative.

Current rule: compatibility shims remain retained while live callers, manifests, installed payloads, or tests still depend on them.

### Wave 4: Architecture / Status Consistency Refresh

Goal: make the live architecture and status spine match the current closure facts.

Current microphases:

- architecture consistency audit refresh
- status spine catch-up

### Wave 5: Final Proof And Cleanup

Goal: finish the remaining architecture-consistency proof, residual-risk inventory, and honest closure language.

This wave is not yet complete.

## Deferred Explicit Tracks

These tracks remain governed backlog, not active closure claims:

- outputs strict-mode adoption and zero-tracked-outputs decision
- third-party source-root parameterization / externalization
- archive / prune windows beyond the current live status spine
- any blanket compatibility-shim deletion program

## Current Truth

- fresh focused verification exists for the latest contract cutover
- fresh full regression exists: `403 passed, 66 subtests passed in 510.12s (0:08:30)`
- `git diff --check` is clean for the latest completed microphase
- the root `remaining-architecture-closure` plan is still open
- bounded fallback inventory and retained compatibility surfaces still exist and must remain explicit

## Cross-Document Boundary

- active root requirement lives in [`../requirements/2026-04-04-remaining-architecture-closure.md`](../requirements/2026-04-04-remaining-architecture-closure.md)
- active root plan lives in [`../plans/2026-04-04-remaining-architecture-closure-plan.md`](../plans/2026-04-04-remaining-architecture-closure-plan.md)
- live runtime summary lives in [`current-state.md`](current-state.md)
- closure receipt lives in [`closure-audit.md`](closure-audit.md)
- blocker map lives in [`path-dependency-census.md`](path-dependency-census.md)

## Exit Conditions

The architecture-closure program is only complete when all of the following are true:

- remaining duplicated semantic owners are removed or demoted to bounded compatibility fallbacks
- live status and architecture surfaces reflect the same current truth
- residual-risk / fallback inventory is documented honestly
- fresh regression and hygiene evidence exists for the final closure wave
- completion language no longer outruns the repository's actually proven state
