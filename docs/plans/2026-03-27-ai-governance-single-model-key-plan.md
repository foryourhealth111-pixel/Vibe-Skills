# Plan: Converge the Built-In AI Governance Layer to One Model Key

## Internal Grade

`L`

## Intent

Finish the install-clarity tightening by removing the remaining multi-key model guidance from the active built-in governance path and standardizing on `VCO_RUCNLPIR_MODEL`.

## Wave Structure

### Wave 1: Freeze

1. Freeze the requirement and plan for the single-model-key convergence.
2. Record the active surfaces that still mention retired secondary model-key wording.

### Wave 2: Runtime and Setup

1. Update the runtime-neutral AI connectivity probe to read and recommend `VCO_RUCNLPIR_MODEL` only.
2. Update bootstrap/setup guidance so the built-in governance path recommends one model key only.
3. Update active settings templates so the built-in governance model slot uses the same key.

### Wave 3: Public Docs

1. Update active Chinese and English install docs to document only `VCO_RUCNLPIR_MODEL`.
2. Update install/update prompt templates to use the same one-key wording.
3. Remove active wording that still presents a retired fallback model key on the public path.

### Wave 4: Mirrors and Proof

1. Sync the changed active source assets into both bundled mirrors.
2. Run verification for diff hygiene, runtime behavior, text references, and mirror parity.
3. Emit cleanup receipts and leave the worktree free of temporary artifacts.

## Ownership Boundaries

- Runtime and verification behavior: `scripts/verify/runtime_neutral/router_ai_connectivity_probe.py`
- Bootstrap/setup guidance: `scripts/bootstrap/one-shot-setup.sh`, `scripts/bootstrap/one-shot-setup.ps1`
- Active shipped templates: `config/settings.template.claude.json`, related source assets
- Public install docs and prompts: `docs/install/**`
- Bundled shipped mirrors: `bundled/skills/vibe/**` and `bundled/skills/vibe/bundled/skills/vibe/**`

## Verification

- `git diff --check`
- `python3 ./scripts/verify/runtime_neutral/router_ai_connectivity_probe.py --target-root "$(mktemp -d)" --prefix-detected`
- `rg -n "<retired-secondary-model-key-pattern>" docs/install docs/one-shot-setup.md scripts/bootstrap scripts/verify/runtime_neutral scripts/verify/vibe-bootstrap-doctor-gate.ps1 config adapters/codex`
- `cmp -s` between changed source assets and both bundled mirrors

## Rollback Rule

If the active shipped path still exposes a second model-key lane after the change, keep tightening before claiming completion.

## Cleanup Expectation

Leave only:

- the frozen requirement and plan docs
- the active source changes for the one-key contract
- synchronized bundled mirrors
- verification evidence and cleanup receipts
