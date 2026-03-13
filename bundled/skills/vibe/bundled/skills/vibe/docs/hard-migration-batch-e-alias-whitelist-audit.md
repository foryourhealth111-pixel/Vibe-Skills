# Hard Migration Report - Batch E Alias Whitelist Audit

Date: 2026-02-24
Mode: audit-only (no deletion)
Status: historical snapshot (superseded by docs/hard-migration-batch-e-final-cleanup-report.md)

## Scope

- Generate removable-alias whitelist for Batch E without deleting any alias.
- Audit external impact using static references across the current workspace.
- Classify alias risk and define staged removal gates (E2/E3/E4).

## Inputs

- Alias map: skills/vibe/config/skill-alias-map.json
- Impact scan: outputs/routing-audit/batche-alias-impact-scan.json
- Whitelist output: skills/vibe/config/batch-e-alias-whitelist.json

## Summary

- Total aliases audited: 28
- Low-risk removable candidates (after gate): 15
- Medium-risk deferred: 11
- High-risk deferred: 2
- Candidate-remove-after-gate: 15
- Defer: 13

## Risk Tiering

| Risk | Count | Typical Pattern | Action |
|------|-------|-----------------|--------|
| Low | 15 | vibe/bundled/* aliases with zero external refs | Candidate for E2 delete after full verification gate |
| Medium | 11 | doc/config/dependency-map coupling | Defer to E3 after dependency/doc cleanup |
| High | 2 | verify-script and workflow-map coupling (code-review3, xlsx1) | Defer to E4; migrate tests and integration references first |

## Highest Impact Aliases (Top External References)

| Alias | Target | External Refs | Risk | Removal Phase |
|-------|--------|---------------|------|---------------|
| code-review3 | code-review | 10 | high | E4 |
| xlsx1 | xlsx | 7 | high | E4 |
| vibe/bundled/skills/vibe | vibe | 3 | medium | E3 |
| code-review1 | code-review | 3 | medium | E3 |
| superpowers/skills/writing-plans | writing-plans | 1 | medium | E3 |
| superpowers/skills/verification-before-completion | verification-before-completion | 1 | medium | E3 |

## Phase Plan (No Delete Yet)

- E2 candidate list (15): low-risk zero-ref bundled aliases.
  - Gate: keep >=2 release cycles + full verification suite pass immediately before delete.
- E3 deferred list (11): medium-risk aliases tied to docs/dependency-map/config references.
  - Gate: reference migration + install pipeline check + full regression pass.
- E4 deferred list (2): high-risk aliases currently used by verification and workflow mapping.
  - Gate: migrate verify scripts and explicit integration docs to canonical names first.

## Blockers Identified

- Verification coupling:
  - skills/vibe/scripts/verify/vibe-soft-migration-practice.ps1 references code-review3 and xlsx1.
  - skills/vibe/scripts/verify/vibe-pack-regression-matrix.ps1 references code-review3 and xlsx1.
- Workflow mapping/docs coupling:
  - skills/spec-kit-vibe-compat/command-map.json references code-review3.
  - skills/security-reviewer/SKILL.md and skills/think-harder/SKILL.md mention code-review3.
- Packaging/dependency coupling:
  - skills/vibe/config/dependency-map.json references superpowers/skills/* paths.

## Verification Gate for Future Deletion

Required before any actual alias deletion:

- scripts/verify/vibe-routing-smoke.ps1
- scripts/verify/vibe-pack-routing-smoke.ps1
- scripts/verify/vibe-skill-index-routing-audit.ps1
- scripts/verify/vibe-keyword-precision-audit.ps1
- scripts/verify/vibe-pack-regression-matrix.ps1

## Validation Executed (This Batch E Step)

Executed after whitelist/audit generation:

- scripts/verify/vibe-routing-smoke.ps1 -> 38/38
- scripts/verify/vibe-pack-routing-smoke.ps1 -> 104/104
- scripts/verify/vibe-skill-index-routing-audit.ps1 -> 93/93
- scripts/verify/vibe-keyword-precision-audit.ps1 -> 982/982
- scripts/verify/vibe-pack-regression-matrix.ps1 -> 24/24

Additional hardening applied during verification:

- Explicit UTF-8 config reads were added in:
  - skills/vibe/scripts/router/resolve-pack-route.ps1
  - skills/vibe/scripts/verify/vibe-pack-routing-smoke.ps1
  - skills/vibe/scripts/verify/vibe-routing-smoke.ps1
- Reason: avoid Windows PowerShell default-encoding misread on non-BOM UTF-8 keyword-index files.

## Files Added

- skills/vibe/config/batch-e-alias-whitelist.json
- skills/vibe/docs/hard-migration-batch-e-alias-whitelist-audit.md

## Outcome

Batch E whitelist generation and impact audit completed. No alias deletions were performed in this step.

