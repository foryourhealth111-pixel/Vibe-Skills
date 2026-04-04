# Operator Preview Contract Governance

## Purpose

Wave122 establishes a single operator contract for write-capable governance scripts. The contract is:

`Precheck -> Preview -> Apply -> Postcheck`

The goal is to remove silent write behavior from the operator surface while keeping execution fast for canonical maintainers.

## Covered Operators

- `scripts/governance/release-cut.ps1`

The active write-capable governance operator must expose a machine-readable preview summary before any non-trivial write flow is applied.

## Required Contract

1. **Precheck**
   - validate execution-context lock;
   - identify canonical root and any declared generated-compatibility scope;
   - enumerate governed write scope.
2. **Preview**
   - support `-Preview` and `-PreviewOutputPath`;
   - emit a machine-readable preview summary to the configured preview root;
   - list planned file writes and post-apply verification expectations.
3. **Apply**
   - only run after preview review;
   - reuse the same operator inputs, never a hidden alternate write path.
   - if the operator runs governed gates after apply, the canonical gate list must come from the operator preview contract instead of an inline script-local inventory.
4. **Postcheck**
   - name the gates or hygiene checks expected after apply;
   - keep the preview/apply boundary auditable.

## Governance Rules

- Preview mode never mutates canonical content.
- Preview receipts are evidence, not a second control plane.
- Apply mode must stay within the canonical repo tree and declared compatibility contract.
- Operator preview receipts are stored under the governed preview output root.

## Audit Surface

The preview contract is governed by:

- `config/operator-preview-contract.json`
- `references/operator-preview-contract.md`
- `scripts/verify/vibe-operator-preview-contract-gate.ps1`
