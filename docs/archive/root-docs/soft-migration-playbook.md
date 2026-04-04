# Soft Migration Playbook (Before Hard Migration)

## Purpose

Validate consolidated routing in production-like practice without deleting legacy skills.

## Rules

- Keep all legacy skill folders intact.
- Prefer alias resolution and pack overlay routing.
- If confidence is low, fallback to legacy Grade×Type matrix.
- Do not remove or rewrite third-party plugin skill sources in this phase.

## Execution Steps

1. Baseline verify:
   - `scripts/verify/vibe-routing-smoke.ps1`
   - `scripts/verify/vibe-pack-routing-smoke.ps1`
2. Practice verify:
   - `scripts/verify/vibe-soft-migration-practice.ps1`
3. Route observation:
   - use `scripts/router/resolve-pack-route.ps1` with real prompts
   - confirm alias hits and selected packs are expected
4. Defect triage:
   - false pack selection -> adjust trigger keywords/candidates
   - over-eager routing -> raise fallback threshold
   - under-routing -> lower confirm threshold or improve intent signals

## Exit Criteria for Hard Migration

- All three verify scripts pass.
- No critical misroute in sampled high-frequency workflows.
- Alias map covers all duplicate legacy names in current inventory.
- Batch A report approved (duplicate fast-wins complete under soft mode).
