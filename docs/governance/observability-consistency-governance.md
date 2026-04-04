# VCO Observability & Consistency Governance (Strict, Lean, Manual-Rollback)

## Design Goals

1. Strict: route and overlay behavior must be measurable and gateable.
2. Lean: avoid LLM-heavy monitoring by default; keep runtime context pressure minimal.
3. Adaptive: learn from real usage by environment/user profile, but never auto-apply risky changes.
4. Safe operations: rollback is notify-only, requires explicit user confirmation.
5. Promotion-aware: new absorption planes can only move beyond `shadow` when evidence is captured on the promotion board.

## Runtime Model

VCO keeps the existing routing pipeline unchanged and adds a post-route telemetry write:

- Config: `config/observability-policy.json`
- Writer: `scripts/router/resolve-pack-route.ps1` (`Write-ObservabilityRouteEvent`)
- Sink: `outputs/telemetry/route-events-YYYYMMDD.jsonl`

Telemetry is sampled by mode (`shadow/soft/strict`) and force-captures high-risk routes:

- `route_mode in {confirm_required, legacy_fallback}`
- any overlay requesting `confirm_required`
- any plane entering promotion evaluation (`memory`, `prompt`, `browserops`, `desktopops`)

## Privacy and Context Budget

Default policy is low-context and privacy-safe:

1. Store `prompt_hash`, not raw prompt.
2. `prompt_excerpt` disabled by default (`prompt_excerpt_max_chars=0`).
3. Persist compact route fields only (grade/task/pack/skill/confidence/gap/route_mode + overlay flags).
4. Use profile IDs (`environment_profile_id`, `user_profile_id`) via hash, not raw identifiers.

## Failure Taxonomy (Deterministic)

`P0 hard_fail`:
- command-priority violation
- task boundary violation
- malformed router output
- second control plane / second execution owner conflict

`P1 functional_fail`:
- selected candidate outside allowed contract
- expected `confirm_required` not raised
- out-of-scope overlay/provider triggered as active
- promotion board missing required evidence fields

`P2 stability_fail`:
- gate threshold regression (`route_stability`, `top1_top2_gap`, `fallback_rate`, `misroute_rate`)
- pilot scenarios fail for a promoted or soft-rolled plane

`P3 outcome_proxy_fail`:
- route appears valid, but downstream acceptance degrades significantly

## Learning Model (Offline, Manual Apply)

- Script: `scripts/learn/vibe-adaptive-train.ps1`
- Input: telemetry JSONL + current router thresholds
- Output: `outputs/learn/vibe-adaptive-suggestions.json` + markdown report
- Policy: bounded threshold deltas, manual review required

Suggested changes are advisory only. No automatic config mutation.

## Promotion Board Integration

Wave27–30 将 observability 与 promotion board 绑定：

- Promotion board: `docs/promotion-board-governance.md` + `config/promotion-board.json`
- Soft rollout helper: `scripts/governance/publish-absorption-soft-rollout.ps1`
- Gates:
  - `scripts/verify/vibe-promotion-board-gate.ps1`
  - `scripts/verify/vibe-pilot-scenarios.ps1`

每个待推广平面都必须记录：
- current stage (`off/shadow/soft/strict/promoted`)
- evidence summary
- required gates
- rollback command
- owner / review timestamp

## Rollback Policy

Rollback policy is explicit and manual:

1. Publish script reports failure and emits rollback command.
2. Operator confirms with user.
3. Operator runs rollback command explicitly.

Automatic rollback execution is disabled by governance policy.

## Recommended Gate Chain

1. `scripts/verify/vibe-pack-routing-smoke.ps1`
2. `scripts/verify/vibe-config-parity-gate.ps1`
3. `scripts/verify/vibe-routing-stability-gate.ps1 -Strict`
4. `scripts/verify/vibe-observability-gate.ps1`
5. `scripts/verify/vibe-promotion-board-gate.ps1`
6. `scripts/verify/vibe-pilot-scenarios.ps1`

`vibe-config-parity-gate.ps1` keeps its historical name. In the current
canonical-only contract it validates config closure and compatibility-topology
assumptions, not repo-tracked bundled sync.

Only after all required gates pass should rollout stage be advanced.

## Wave27-30 Promotion Evidence Layer

Wave27-30 为 observability / consistency 增加了 promotion board 与 pilot 证据层。

关联资产：
- `docs/promotion-board-governance.md`
- `config/promotion-board.json`
- `scripts/governance/publish-absorption-soft-rollout.ps1`
- `docs/archive/root-docs/pilot-scenarios-and-eval.md`
- `scripts/verify/vibe-promotion-board-gate.ps1`
- `scripts/verify/vibe-pilot-scenarios.ps1`

新增治理要求：
1. rollout 必须有 evidence score、blocking findings、rollback command。
2. soft rollout 只允许 advice-first，不允许无证据 promote。
3. pilot fixtures 是 promotion 的先决条件，而不是发布后的补充材料。
