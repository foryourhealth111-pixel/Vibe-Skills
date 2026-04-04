# BrowserOps Provider Scorecard Governance

Wave67 不直接改 BrowserOps 的 canonical routing，而是补一层 **provider scorecard v2**，把 `api` / `playwright` / `chrome-devtools` / `turix-cua` / `browser-use` 的 route evidence 固定成可审计资产。

## Scorecard Role

scorecard 只回答三件事：

- 哪个 provider 属于 baseline，哪个只属于 candidate；
- 哪些维度决定 provider recommendation 的可信度；
- 哪些 provider 必须保留 `confirm_required`、`fallback_provider` 与 takeover ban。

它不负责：

- 改写 `config/browserops-provider-policy.json`；
- 覆盖 `VCO` 主路由；
- 把 `browser-use` 升格为第二 orchestrator。

## Fixed Dimensions

Wave67 固定以下五个维度：

- `determinism`：是否适合作为默认稳定执行面；
- `fallback_readiness`：失败时是否存在 canonical fallback；
- `telemetry_readiness`：是否能稳定留下 route evidence；
- `confirm_bias`：是否必须默认保留人工确认偏置；
- `takeover_safety`：是否明确禁止 second orchestrator / provider takeover。

## Governance Invariants

- `control_plane_owner = vco`
- scorecard 是 evidence，不是 router
- `browser-use` 与 `turix-cua` 仍属于 `candidate_soft_only`
- 所有 candidate provider 都必须带 `fallback_provider`
- `browser-use` 永远不能脱离 `candidate_only` posture

## Usage Rule

`config/browserops-scorecard.json` 是可执行视图；`references/browser-provider-scorecard.md` 是运营视图。两者必须与 `config/browserops-provider-policy.json` 的 provider posture 保持一致。

scorecard 可用于：

- route evidence 审计；
- soft rollout 候选说明；
- fallback / confirm bias 是否接线完成的检查。

scorecard 不可用于：

- 自动翻转 provider 优先级；
- 让 `browser-use` 绕过 `playwright` baseline；
- 取消高风险网页动作的 `confirm_required`。

## Gate Coverage

`scripts/verify/vibe-browserops-scorecard-gate.ps1` 必须验证：

- governance doc / scorecard config / reference scorecard 同时存在；
- provider 列表与 canonical BrowserOps policy 一致；
- `browser-use` 仍是 `candidate_soft_only` 且 `takeover_forbidden = true`；
- scorecard 文本中显式保留 `route evidence`、`fallback_provider`、`confirm bias` 与 `browser-use` 的治理边界。
