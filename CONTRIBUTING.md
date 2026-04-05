# Contributing to VCO Skills Codex

This repository is open to contributions, but it is not an "edit anywhere"
repo.

`vco-skills-codex` contains runtime entrypoints, routing policy, bundled
mirrors, provenance records, release evidence, and contributor-safe governance
surfaces. The first job of a contributor is to choose the correct surface
before making a change.

---

> **TL;DR — Three safe contribution paths for most contributors:**
>
> 1. **Add or improve documentation** → work in `docs/**`, `references/**`, or `templates/**`. These are always safe to edit.
> 2. **Add governance guidance or verification scripts** → work in `scripts/governance/**` or `scripts/verify/**`.
> 3. **Anything else** → read the zone table and proof matrix before touching any files. If uncertain, open an Issue first.

---

## Start Here

1. Read the zone table:
   [`references/contributor-zone-decision-table.md`](references/contributor-zone-decision-table.md)
2. Classify your change with the proof matrix:
   [`references/change-proof-matrix.md`](references/change-proof-matrix.md)
3. Read the formal change-control rules if your change is not obviously
   docs-only:
   [`docs/developer-change-governance.md`](docs/developer-change-governance.md)
4. If your change touches a frozen or guarded surface, stop and write or attach
   a plan before editing:
   [`docs/plans/2026-03-13-post-upstream-governance-developer-entry-plan.md`](docs/plans/2026-03-13-post-upstream-governance-developer-entry-plan.md)

## Default Safe Contribution Path

If you are not sure where to work, stay in the additive contributor-safe zones:

- `docs/**`
- `references/**`, except `references/fixtures/**`
- `scripts/governance/**`
- `scripts/verify/**`
- `templates/**`

These surfaces are the preferred place to add documentation, governance
contracts, verification gates, and operator guidance without changing runtime
behavior.

## Do Not Edit These Surfaces Casually

Do not directly edit these paths unless your change explicitly owns the plan and
proof burden (see "When a Plan Is Mandatory" below):

- `install.ps1`
- `install.sh`
- `check.ps1`
- `check.sh`
- `SKILL.md`
- `protocols/**`
- `scripts/router/**`
- `bundled/**`
- tracked `outputs/**`
- `third_party/**`
- `vendor/**`

Those areas either control runtime behavior directly or represent mirrored,
generated, vendored, or compliance-sensitive content.

## Choose Your Change Class

### Docs-only

**What this means**: You are changing explanatory docs, reference guides, plans,
or governance text. You are not changing how the runtime behaves.

**Examples**: Fixing a typo in `docs/quick-start.md`, adding a new guide under
`docs/install/`, improving the wording in `references/contributor-zone-decision-table.md`.

Start with:

- [`docs/README.md`](docs/README.md)
- [`references/contributor-zone-decision-table.md`](references/contributor-zone-decision-table.md)
- [`references/change-proof-matrix.md`](references/change-proof-matrix.md)

### Governance or Policy

**What this means**: You are changing a public promise, repo rule, gate
definition, or machine-readable policy surface. These changes affect how the
repo self-describes its rules.

**Examples**: Adding a new rule to `conflict-rules.md`, updating the
contributor zone table to recognize a new file category.

Always read:

- [`docs/developer-change-governance.md`](docs/developer-change-governance.md)
- [`docs/distribution-governance.md`](docs/distribution-governance.md)
- [`docs/repo-cleanliness-governance.md`](docs/repo-cleanliness-governance.md)

### Mirror, Fixture, Provenance, or Compliance

**What this means**: You are touching files that are copies or records of
something that lives elsewhere. The source of truth is not in this repo.

**Examples**: Updating a vendored library under `third_party/**`, refreshing
a bundled mirror under `bundled/**`.

These changes are never mirror-first. The canonical source must change first,
then sync and proof must follow. Use this class when you touch:

- `bundled/**`
- `references/fixtures/**`
- tracked `outputs/**`
- `third_party/**`
- `vendor/**`

### Runtime-affecting

**What this means**: You are changing something that alters the default behavior
of the governed runtime — install flow, routing logic, protocol instructions,
or packaged behavior.

**Examples**: Editing `SKILL.md` to add a new stage, modifying `install.ps1`,
changing routing logic in `scripts/router/**`.

These changes require a plan before implementation and a stronger proof bundle
before completion (see below).

## When a Plan Is Mandatory

> **"Frozen surface"**: A file is "frozen" or "guarded" when it is a direct
> control point for the runtime — install scripts, routing rules, protocol
> definitions (`protocols/**`), and the primary skill contract (`SKILL.md`).
> These are called **Z0 files** (Zone 0 = highest protection level). Editing
> them without a plan risks breaking the runtime for all users.

> **"Proof bundle"**: Evidence that your change works and doesn't break
> anything. The minimum is `[Command] → [Output] → [Claim]` — you ran a
> specific check, here is the output, and here is what it proves. For
> runtime-affecting changes, the proof bundle is more extensive (see the
> change-proof-matrix for details).

Write or attach a plan before editing if any of the following are true:

- you are changing a **Z0 frozen control-plane file** (install scripts,
  routing, protocols, `SKILL.md`)
- you are changing multiple zones in one task
- you are changing install, check, router, protocol, or packaging behavior
- you are changing vendored, mirrored, provenance, or disclosure surfaces
- you cannot explain the required proof set before you start editing

The current program plan for developer entry is:

- [`docs/plans/2026-03-13-post-upstream-governance-developer-entry-plan.md`](docs/plans/2026-03-13-post-upstream-governance-developer-entry-plan.md)

## Minimum Proof Expectation

Use the proof matrix for the exact path, but the default floor is:

- **docs-only changes**: `git diff --check` plus link and navigation sanity
  check (do the links still work?)
- **governance changes**: relevant gates must still pass, plus updated
  documentation that reflects the policy change
- **guarded or runtime-sensitive changes**: explicit **proof bundle** with
  `Command → Output → Claim` evidence for each critical behavior

The matrix is here:

- [`references/change-proof-matrix.md`](references/change-proof-matrix.md)

## Stop and Escalate

Stop working and open an Issue (or comment on an existing one) if any of the
following are true — do not guess your way through these situations:

- you are about to edit `bundled/**` as if it were the source of truth (it is
  not — the canonical source lives elsewhere)
- you are about to hand-edit tracked `outputs/**` (these are generated)
- you cannot identify the canonical source for a mirrored file
- you are touching `third_party/**` or `vendor/**` without provenance and
  disclosure updates
- you do not know which gates must pass before you claim non-regression

## Useful Navigation

- repo docs index:
  [`docs/README.md`](docs/README.md)
- formal change-control rules:
  [`docs/developer-change-governance.md`](docs/developer-change-governance.md)
- contributor zone table:
  [`references/contributor-zone-decision-table.md`](references/contributor-zone-decision-table.md)
- change proof matrix:
  [`references/change-proof-matrix.md`](references/change-proof-matrix.md)
- developer entry baseline:
  [`references/developer-entry-contract.md`](references/developer-entry-contract.md)
- current docs cleanup governance:
  [`docs/requirements/2026-04-05-github-visible-docs-worklog-purge.md`](docs/requirements/2026-04-05-github-visible-docs-worklog-purge.md)

## Scope Note

This contributor guide is the human entry surface for the developer-entry
rollout. Formal enforcement evidence for templates, gating, and non-regression
proof lives in the developer-entry contract and the active verify surfaces,
not in a large tracked archive of dated status logs.
