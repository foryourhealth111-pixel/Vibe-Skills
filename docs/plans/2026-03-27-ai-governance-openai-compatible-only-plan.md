# Plan: Restrict the Built-In AI Governance Layer to OpenAI-Compatible Integration

## Internal Grade

`L`

## Intent

Close the remaining Ark-specific branches on the active built-in governance path so shipped runtime, install UX, and verification all tell one OpenAI-compatible story.

## Execution Steps

1. Freeze the requirement and plan for the OpenAI-compatible-only restriction.
2. Update active governance defaults and provider authority:
   - `config/llm-acceleration-policy.json`
   - `config/router-provider-registry.json`
   - active runtime/overlay scripts
3. Update active bootstrap/setup and doctor surfaces so they no longer seed or recommend Ark-specific settings.
4. Update public install/setup docs and prompts to remove Ark-compatible guidance from the built-in path.
5. Update active fixtures/templates that still advertise Ark as a built-in lane.
6. Sync the changed source assets into both bundled mirrors.
7. Run verification for diff hygiene, mirror parity, and probe behavior.

## Verification

- `git diff --check`
- `python3 ./scripts/verify/runtime_neutral/router_ai_connectivity_probe.py --target-root "$(mktemp -d)" --prefix-detected`
- `cmp -s` between changed source assets and both bundled mirrors
- `rg -n "ARK_API_KEY|ARK_BASE_URL|VOLC_ARK_BASE_URL|ark-compatible|volc_ark" docs/install docs/one-shot-setup.md config scripts/bootstrap scripts/verify/runtime_neutral scripts/router/modules/48-llm-acceleration-overlay.ps1 config/router-provider-registry.json config/llm-acceleration-policy.json config/settings.template.codex.json adapters/codex/settings-map.json`

## Rollback Rule

If the active built-in path still advertises a second provider family after the change, keep tightening before completion.

## Cleanup Expectation

Leave only the requirement/plan docs, the OpenAI-compatible-only source changes, the synced bundled mirrors, and the verification evidence.
