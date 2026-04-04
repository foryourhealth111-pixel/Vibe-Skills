# ORIGIN Provenance Policy

## Purpose

`ORIGIN.md` is the per-asset provenance record for any repo-local upstream retention under `vendor/**`.

Without `ORIGIN.md`, the repo cannot safely answer:

- where this asset came from
- under which license it is governed
- whether it is verbatim or modified
- whether it is shipped by default
- how it should be refreshed

## When `ORIGIN.md` Is Required

`ORIGIN.md` is required for any retained upstream asset root under:

- `vendor/upstreams/<slug>/`
- `vendor/mirrors/<slug>/`

It is not required for:

- `third_party/**` compliance-only material
- canonical VCO-authored runtime files
- docs that merely mention upstream sources

## Required Fields

Every `ORIGIN.md` must include:

- `canonical_slug`
- `upstream_repo`
- `upstream_ref`
- `license_spdx`
- `distribution_tier`
- `redistribution_posture`
- `integration_mode`
- `local_path`
- `shipped_by_default`
- `modified_by_vco`
- `refresh_command`
- `required_notice_files`
- `trademark_notes`
- `security_or_compliance_notes`

## Policy Rules

1. No retained upstream asset may enter `vendor/**` without `ORIGIN.md`.
2. `ORIGIN.md` must agree with the corresponding canonical registry entry.
3. `ORIGIN.md` must state whether the asset is verbatim or modified.
4. If an asset is not shipped by default, `ORIGIN.md` must say so explicitly.
5. If redistribution is restricted or unclear, the posture must be conservative.

## Enforcement

The enforcement gate is:

- `scripts/verify/vibe-origin-provenance-gate.ps1`

Phase 0 policy-only mode allows `vendor/**` to contain only scaffolding.
The moment a real retained upstream asset appears, `ORIGIN.md` becomes mandatory.
