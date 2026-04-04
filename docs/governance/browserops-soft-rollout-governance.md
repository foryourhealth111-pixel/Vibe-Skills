# BrowserOps Soft Rollout Governance

Wave68 把 BrowserOps provider plane 推进到 **soft candidate**，但 soft candidate 只表示“证据与回滚闭环已就绪”，不表示默认 takeover 或默认路由翻转。

## Soft Candidate Means

- promotion board 可以把 `browserops-provider` 记录为 `current_stage = soft`；
- canonical policy 仍保持 `allow_provider_suggestion_only = true`；
- `browser-use` 与 `turix-cua` 仍保留 `confirm_required = true`；
- 所有开放式浏览路径仍必须显式携带 `fallback_provider`。

## Required Wiring

soft rollout 最少要接通以下证据面：

- `telemetry`：记录 `provider`、`reason`、`confidence`、`confirm_required`、`fallback_provider`；
- `fallback`：任何 `candidate_soft_only` provider 都必须可回退到 `playwright`；
- `confirm bias`：高风险关键词命中后不得取消 `confirm_required`；
- `pilot fixture`：`scripts/verify/fixtures/pilot-browserops.json` 作为最小演练样例。

## Non-goals

- 不把 `browser-use` 升格为第二 orchestrator；
- 不让 scorecard 覆盖 `config/browserops-provider-policy.json`；
- 不允许无 fallback 的开放式浏览成为默认执行面。

## Rollback

soft rollout 的 rollback 命令必须保持为：`set browserops mode to shadow/off and keep playwright baseline`。

换言之，BrowserOps soft candidate 的失败处理永远回到既有 `playwright` baseline，而不是把 `browser-use` 留在默认路径上。

## Gate Coverage

`scripts/verify/vibe-browserops-softrollout-gate.ps1` 必须验证：

- baseline `vibe-browserops-gate.ps1` 仍通过；
- promotion board 中 `browserops-provider` 维持 `soft` 阶段与 rollback 约束；
- governance doc 明确保留 `telemetry`、`fallback_provider`、`confirm bias` 与 `browser-use` 边界；
- `pilot-browserops.json` 仍是 canonical soft rollout fixture。
