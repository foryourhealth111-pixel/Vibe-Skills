# Plan: Consolidate Built-In AI Governance to a Stable Single-Path Contract

## Internal Grade

`L`

## Intent

Finish the built-in AI governance tightening by aligning runtime behavior, doctor/reporting surfaces, helper scripts, and install entry docs to one active OpenAI-compatible contract.

## Execution Steps

1. Freeze the requirement and plan for the consolidation pass.
2. Update bootstrap doctor implementations to report both API key state and governance model state.
3. Update one-shot and related active install entry docs so the follow-up guidance explicitly includes `VCO_RUCNLPIR_MODEL`.
4. Remove Ark-specific built-in governance helper scripts from the active shipped path.
5. Update active verification helpers so they no longer test Ark-specific built-in governance branches.
6. Sync all changed active assets into both bundled mirrors.
7. Run verification for diff hygiene, runtime behavior, residual legacy active-path matches, and mirror parity.

## Verification

- `git diff --check`
- `python3 ./scripts/verify/runtime_neutral/bootstrap_doctor.py --target-root "$(mktemp -d)"`
- `python3 ./scripts/verify/runtime_neutral/router_ai_connectivity_probe.py --target-root "$(mktemp -d)" --prefix-detected`
- `rg -n "ARK_API_KEY|ARK_BASE_URL|VOLC_ARK_BASE_URL|02-volc-ark|persist-codex-ark-env|Invoke-VolcArkEmbeddingsCreate" config docs/install docs/one-shot-setup.md scripts/bootstrap scripts/verify scripts/router adapters/codex`
- `cmp -s` between changed source assets and both bundled mirrors

## Rollback Rule

If any consolidation step makes readiness reporting less accurate or breaks the active OpenAI-compatible path, repair that regression before completion.

## Cleanup Expectation

Leave only the consolidated active source changes, synchronized bundled mirrors, verification evidence, and cleanup receipts.
