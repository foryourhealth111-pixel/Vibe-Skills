# Vendor Boundary

`vendor/**` is the repo-local upstream retention surface.

It is intentionally separate from `third_party/**`.

## Layout

- `vendor/upstreams/`
  Retained upstream assets that may later be promoted into a governed repo-local distribution posture.
- `vendor/mirrors/`
  Repo-local mirrors retained for audit, comparison, or operator convenience, but not shipped by default.

## Rules

1. `vendor/**` is not a free-form dump zone.
2. Every real retained upstream root must include `ORIGIN.md`.
3. `vendor/**` is not the canonical runtime edit surface.
4. Promotion from `vendor/**` requires tier, license, notice, and proof-gate closure.
5. Placeholder-only directories may keep `.gitkeep`, but any real retained payload must also declare fetch or refresh instructions.

## Current State

- the current repo tracks placeholder-only `vendor/upstreams/.gitkeep` and `vendor/mirrors/.gitkeep`
- no live retained upstream payload should be inferred from the existence of `vendor/**` alone

## What Does Not Belong Here

- local scratch files
- unmanaged git clones
- hidden backups
- runtime outputs

See:

- `../docs/distribution-governance.md`
- `../docs/governance/origin-provenance-policy.md`
