# 2026-04-04 Strong Repo Slimming Program

## Goal

Design a strong repository-slimming program for the latest `main` checkout that materially reduces historical noise, stale documents, oversized snapshots, dead scripts, and compatibility-era clutter while preserving runtime behavior, installer behavior, verification coverage, and release integrity.

## Deliverable

A governed slimming requirement packet and an executable plan that classify the repository into:

- safe-to-prune or archive-first surfaces
- contract-first refactor surfaces that must shrink only after ownership is clarified
- protected surfaces that must not be slimmed until downstream callers are removed or migrated

## Constraints

- Plan against the latest `origin/main` worktree in `/home/lqf/table/table9/Vibe-Skills-main`.
- Preserve install, check, release, runtime, adapter, verification, and catalog behavior.
- Do not treat generated compatibility projections as semantic owners.
- Prefer archiving, partitioning, or manifest-driven generation over destructive removal when live consumers still exist.
- Keep the repository aligned with high cohesion and low coupling principles:
  - one semantic owner per concern
  - thin compatibility shims
  - dated material separated from active entry surfaces
  - generated or reproducible payloads separated from long-lived canonical sources

## Current Architecture Snapshot

The latest checkout behaves like a mixed runtime-and-knowledge monorepo with eight distinct layers:

1. semantic core and contracts
   - `packages/**`
   - `core/**`
   - `config/**`
2. CLI and host-facing execution entrypoints
   - `apps/vgo-cli/**`
   - top-level install/check wrappers
   - `scripts/runtime/**`, `scripts/router/**`, `scripts/install/**`, `scripts/uninstall/**`
3. host adapter projections
   - `adapters/**`
4. generated distribution and packaging projections
   - `dist/**`
   - `distributions/**`
5. verification and replay surface
   - `scripts/verify/**`
   - `tests/**`
6. bundled product payload
   - `bundled/skills/**`
7. maintainership knowledge and policy surface
   - `docs/**`
   - `references/**`
   - `protocols/**`
   - `templates/**`
8. low-mass compliance or sample surfaces
   - `third_party/**`
   - `vendor/**`
   - `benchmarks/**`

Slimming must preserve layers 1 through 5 as live behavior-bearing surfaces.
The main reduction pressure should fall on layers 6 and 7, plus any compatibility duplication that can be proven non-authoritative.

## Current Evidence Snapshot

Current latest-checkout inventory observed during planning:

- repository size: about `45M`
- total tracked files: about `3779`
- markdown files: about `2181`
- PowerShell scripts: about `268`
- `bundled/`: about `30M`, `2120` files
- `docs/`: about `3.7M`, `593` files
- `references/`: about `1.9M`, `178` files
- `scripts/`: about `3.4M`, `323` files
- `tests/`: about `1.1M`, `151` files
- `dist/`: `17` files only
- `vendor/`: `3` files only
- `benchmarks/`: `9` files only
- `third_party/`: `7` files only
- `docs/archive/**`: `262` files
- live `docs/requirements/**`: `48` files
- live `docs/plans/**`: `27` files
- live `docs/releases/**`: `6` files
- `scripts/verify/**`: `205` files
- `references/proof-bundles/**`: `43` files
- `references/fixtures/**`: `45` files

Current heavy hotspots and duplication patterns:

- `bundled/skills/document-skills/**`: about `2.8M`, `131` files
- `bundled/skills/docx/**`: about `1.3M`, `59` files
- `bundled/skills/unsloth/references/llms-txt.md`: about `813K`
- triplicated OOXML schema payloads exist under:
  - `bundled/skills/docx/ooxml/**`
  - `bundled/skills/document-skills/docx/ooxml/**`
  - `bundled/skills/document-skills/pptx/ooxml/**`
- active skill-lock still tracks duplicate or alias-like skill families such as:
  - `bundled/skills/pymc`
  - `bundled/skills/pymc-bayesian-modeling`
  - `bundled/skills/torch-geometric`
  - `bundled/skills/torch_geometric`
- `scripts/verify/**` contains many family clusters, including:
  - `anti-proxy-*`: `7`
  - `prompt-intelligence-*`: `3`
  - `cross-plane-*`: `3`
  - `cross-host-*`: `3`

Current low-value slimming targets are not the smallest trees.
`dist/**`, `vendor/**`, `benchmarks/**`, and `third_party/**` are too small or too contract-linked to be the first-order size win.

## Acceptance Criteria

1. The plan names the highest-value slimming targets with concrete path families and a risk tier for each.
2. The plan distinguishes immediate archive or deletion candidates from contract-first refactors and protected surfaces.
3. The plan preserves functional behavior by requiring path-reference audits, targeted regression tests, and rollback boundaries before destructive changes.
4. The plan provides a wave structure that can be executed as reviewable, low-blast-radius PR batches rather than one large cleanup.
5. The plan includes explicit rules for historical docs, reference snapshots, scripts, proof bundles, and bundled skill payloads.
6. The plan distinguishes high-value slimming from low-yield churn, so maintainers do not spend review budget on tiny surfaces such as `vendor/**` before major payload families are tamed.
7. The plan treats bundled duplication, skill alias overlap, and verification-gate family sprawl as first-class structural problems rather than incidental cleanup.

## Product Acceptance Criteria

The slimming program is acceptable only if:

1. Maintainers can explain which paths are canonical source, compatibility projection, archive, fixture, or proof surface without ambiguity.
2. Public entry surfaces become simpler, while active runtime and installer behavior remain unchanged.
3. Historical material no longer crowds active navigation surfaces.
4. Large reproducible or low-signal assets gain a clear retention rule instead of remaining indefinitely by default.
5. Every proposed strong cut has a corresponding verification and rollback rule.
6. The final target state keeps runtime-bearing layers small and explicit while pushing bulk history, optional references, and duplicate assets behind archive, generation, or alias boundaries.

## Manual Spot Checks

- Open `docs/README.md`, `docs/plans/README.md`, `docs/requirements/README.md`, and `docs/releases/README.md` and confirm active surfaces are still discoverable after slimming.
- Check that installer-facing docs still point to the correct host and distribution surfaces.
- Confirm no plan recommends deleting `dist/*`, package-owned semantic cores, or active verification contracts without a migration owner.
- Confirm archive recommendations do not break links from current README, release, or status spines.

## Completion Language Policy

- This planning run may claim only that a slimming program has been produced and grounded in repository evidence.
- It must not claim that the repository has already been slimmed, simplified, or regression-safe after execution.
- Any future implementation batch must earn its own verification evidence before stronger completion language is used.

## Delivery Truth Contract

- Planning truth is authoritative only for classification, sequencing, and risk boundaries.
- Implementation truth remains pending until each slimming wave is executed and verified.

## Non-Goals

- No blanket deletion of `bundled/skills`, `dist`, `packages`, `tests`, or `outputs` contracts in this planning phase.
- No feature expansion, branding rewrite, or unrelated functional refactor.
- No silent promotion of convenience metrics such as raw file-count reduction over semantic clarity and safety.
- No cosmetic trimming of tiny directories like `vendor/**` or `benchmarks/**` as a substitute for addressing the real heavy surfaces.

## Inferred Assumptions

- The maintainer wants aggressive slimming, but not at the cost of runtime, release, or installer regressions.
- Historical documentation density is currently harming navigation and maintenance more than it is helping current contributors.
- Some large tracked assets remain because there was no retention policy, not because they are still the best source of truth.
- The next meaningful slimming step should focus on live knowledge surfaces, verification family sprawl, and bundled payload duplication before touching already-minimal compliance or sample directories.
