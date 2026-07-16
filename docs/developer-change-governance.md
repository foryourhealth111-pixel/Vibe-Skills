# Developer Change Governance

## Why This Exists

`vco-skills-codex` is not a flat repo where every directory carries the same
edit risk.

It contains:

- runtime control surfaces
- routing and packaging contracts
- governance and disclosure surfaces
- canonical-to-bundled mirrors
- fixtures, tracked outputs, and release evidence
- provenance-sensitive retained upstream surfaces

Without path-based change governance, a change that "looks small" can still
break routing, packaging, parity, provenance, or release safety.

This document turns that risk into an explicit contributor workflow.

## Reader Shortcuts

If you are contributing rather than redesigning the repo, start here:

- contributor zone table:
  [`../references/contributor-zone-decision-table.md`](../references/contributor-zone-decision-table.md)
- change proof matrix:
  [`../references/change-proof-matrix.md`](../references/change-proof-matrix.md)
- root contributor guide:
  [`../CONTRIBUTING.md`](../CONTRIBUTING.md)

## Core Rules

1. Classify the path before editing it.
2. Prefer additive work in low-risk zones.
3. Do not treat mirrored, generated, vendored, or tracked-output surfaces as
   casual edit targets.
4. Any change that can affect runtime, install, routing, packaging, provenance,
   or disclosure needs explicit proof, not confidence language.

## Zone Model

### Z0: Frozen Control Plane

Typical paths:

- `install.ps1`
- `install.sh`
- `check.ps1`
- `check.sh`
- `SKILL.md`
- `protocols/**`
- `scripts/router/**`
- routing lock and manifest files

Expectations:

- plan first
- baseline before the change
- runtime non-regression proof after the change
- no mixed-intent high-risk edits in a casual patch

### Z1: Guarded Governance and Policy

Typical paths:

- `config/**` outside frozen routing files
- `hooks/**`
- `rules/**`
- `agents/**`
- root `README.md`
- `LICENSE`
- `NOTICE`
- `THIRD_PARTY_LICENSES.md`

Expectations:

- additive-first
- public or policy changes must update their explanatory docs
- disclosure changes must stay aligned with canonical registries

### Z2: Guarded Mirror, Fixture, Provenance, and Compliance

Typical paths:

- `bundled/**`
- `references/fixtures/**`
- tracked `outputs/**`
- `third_party/**`
- `vendor/**`

Expectations:

- canonical-first, then sync
- no mirror-first editing
- no hand-maintained tracked outputs as substitute source
- no retained upstream content without provenance

### Z3: Preferred Contribution Zones

Typical paths:

- `docs/**`
- `references/**` except fixtures
- `scripts/governance/**`
- `scripts/verify/**`
- `templates/**`

This is the default contributor-safe surface.

Use it for:

- governance and contributor docs
- plans, closure reports, and SOPs
- new verification gates
- provenance templates and reference matrices
- additive tooling that does not replace runtime ownership

## Default Contributor Rule

If you cannot confidently justify a higher-risk edit, stay in `Z3`.

That means the default safe path for ordinary contributors is:

- `docs/**`
- `references/**` except fixtures
- `scripts/governance/**`
- `scripts/verify/**`
- `templates/**`

Do not assume the whole repo is open for equal editing.

## Change Classes

### Docs-only

Typical paths:

- `docs/**`
- `references/**` except fixtures
- `README.md`
- `docs/README.md`
- `CONTRIBUTING.md`

Minimum proof:

- `git diff --check`
- link and navigation sanity

### Governance or Policy

Typical paths:

- policy-facing `docs/**`
- `config/**`
- `scripts/governance/**`
- `scripts/verify/**`
- `NOTICE`
- `THIRD_PARTY_LICENSES.md`

Minimum proof:

- updated policy docs
- relevant gate reruns when behavior changes
- `Command -> Output -> Claim` evidence for guarded changes

### Compatibility, Fixture, Output Boundary, or Provenance

Typical paths:

- `bundled/**`
- `references/fixtures/**`
- tracked `outputs/**`
- `third_party/**`
- `vendor/**`

Minimum proof:

- canonical source identified
- compatibility materialization path identified when applicable
- parity, boundary, cleanliness, and provenance proof as applicable

### Runtime-affecting

Typical paths:

- any `Z0` surface
- anything that changes install, check, router, protocol, packaging, or default
  runtime behavior

Minimum proof:

- plan first
- baseline first
- runtime proof bundle after the change
- stop-ship if the proof is incomplete or red

## When a Plan Is Mandatory

Write or attach a plan before editing if:

- the target is in `Z0`
- the change crosses multiple zones
- the change affects runtime, install, routing, protocol, packaging, or default
  ownership
- the change affects vendored, mirrored, provenance, or disclosure surfaces
- you cannot explain the proof set before making the edit

Current program plan:

- [`plans/2026-03-13-post-upstream-governance-developer-entry-plan.md`](plans/2026-03-13-post-upstream-governance-developer-entry-plan.md)

## Runtime Proof Bundle

When the change is runtime-affecting or crosses into frozen or guarded
execution-sensitive surfaces, expect to justify the result with the relevant
subset of:

- `scripts/verify/vibe-pack-routing-smoke.ps1`
- `scripts/verify/vibe-current-routing-debt-gate.ps1`
- `scripts/verify/vibe-version-packaging-gate.ps1`
- `scripts/verify/vibe-output-artifact-boundary-gate.ps1`
- `scripts/verify/vibe-repo-cleanliness-gate.ps1`
- `scripts/verify/vibe-installed-runtime-freshness-gate.ps1`
- `scripts/verify/vibe-release-install-runtime-coherence-gate.ps1`

If the change also affects provenance, disclosure, or retained upstream closure,
expect the corresponding upstream and provenance gates as well.

For legacy-named packaging gates, read them through the current canonical-only
contract rather than assuming repo-tracked mirror sync is still an active
maintenance step.

## Explicitly Forbidden Shortcuts

These are never acceptable:

1. editing `bundled/**` as if it were the source of truth
2. hand-editing tracked `outputs/**` to fake clean state or passing evidence
3. lowering gates or loosening policy to make a problem disappear
4. changing public disclosure without updating canonical truth surfaces
5. retaining upstream code without provenance and license handling
6. changing runtime control surfaces without plan and proof

## Safe Contribution Definition

A change is only safe when all of the following are true:

- the path risk was classified correctly
- the change stayed inside the allowed ownership boundary
- the required proof set was executed or consciously scoped
- the conclusion can be defended with `Command -> Output -> Claim`
- no new mirror, provenance, disclosure, or runtime drift was introduced

The purpose of this document is not to slow contributors down. It is to keep
the repo extensible without letting path confusion become runtime regression.
