# Plan: Clarify AI Governance Install-Time API Configuration

## Internal Grade

`L`

## Intent

Unify the install-time wording, runtime hints, and quick-check guidance so the latest repo tells users one concrete story about how to bring the AI governance advice path online.

## Execution Steps

1. Freeze the requirement and plan for issue `#57`.
2. Rewrite `docs/install/configuration-guide.*` around the actual probe/runtime key resolution path.
3. Tighten the single install entry and install prompts so they tell users exactly which local keys to set after install.
4. Update install rules and supporting install docs that still present `VCO_AI_PROVIDER_*` as the primary local guidance.
5. Patch runtime-facing bootstrap/probe messages so install-time output matches the docs.
6. Sync updated install docs into both bundled install-doc mirrors.
7. Run diff/parity/keyword verification and confirm no stale primary guidance remains on the public install path.

## Verification

- `git diff --check -- docs/requirements/2026-03-27-ai-governance-install-clarity.md docs/plans/2026-03-27-ai-governance-install-clarity-plan.md docs/requirements/README.md docs/plans/README.md docs/install scripts/bootstrap scripts/verify/runtime_neutral/router_ai_connectivity_probe.py bundled/skills/vibe/docs/install bundled/skills/vibe/bundled/skills/vibe/docs/install`
- `cmp -s` between each updated source install doc and both bundled mirrors
- `rg -n "VCO_AI_PROVIDER_URL|VCO_AI_PROVIDER_API_KEY" docs/install/one-click-install-release-copy.md docs/install/one-click-install-release-copy.en.md docs/install/configuration-guide.md docs/install/configuration-guide.en.md docs/install/prompts/full-version-install.md docs/install/prompts/full-version-install.en.md docs/install/prompts/framework-only-install.md docs/install/prompts/framework-only-install.en.md docs/install/installation-rules.md docs/install/installation-rules.en.md`
- `python3 ./scripts/verify/runtime_neutral/router_ai_connectivity_probe.py --help`

## Rollback Rule

If the changes weaken truthfulness around install vs online readiness, or if source and bundled docs diverge, fix that before completion.

## Cleanup Expectation

Leave only the new requirement/plan docs, the clarified install/runtime guidance, mirrored bundled docs, and verification evidence.
