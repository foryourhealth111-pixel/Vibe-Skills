# Gate Reliability and Keyword Alias Governance

## Purpose

Wave83 hardens governance gates so that keyword aliases, shell entrypoints, UTF-8 BOM handling, and release registration stay deterministic under the single VCO control plane.
This wave consolidates reliability rules for gate authoring instead of creating a second verifier or a self-healing controller.

## Governance Scope

- Canonical gate scripts must run from the outer repo root and keep `Write-VgoUtf8NoBomText` as the file-writing primitive.
- Keyword aliases are evidence inputs only; they cannot rewrite routing, promotion, or execution ownership.
- Every new release-facing gate must be listed in `docs/releases/README.md` and `scripts/governance/release-cut.ps1`.

## Required Invariants

- `utf8_no_bom_required = true` for `SKILL.md`, governance docs, config JSON, and verify artifacts that can be parsed by frontmatter-aware loaders.
- `yaml_frontmatter_byte0_rule = true` for any frontmatter-bearing markdown so byte 0 sees the first `---` delimiter.
- `powershell_5_1_compatible = true` and `no_pwsh_requirement = true` for all Wave83-100 gate scripts.
- No auto-fix mode may mutate pack routing, board state, or thresholds without an explicit manual flag.

## Non-Goals

- No new gate runner may bypass `vibe-governance-helpers.ps1` execution-context lock.
- No keyword alias registry may become a hidden second router.

Validation is performed by `scripts/verify/vibe-gate-reliability-gate.ps1`.
