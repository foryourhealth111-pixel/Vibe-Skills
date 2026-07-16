# Browser Provider Scorecard

| Provider | Status | Determinism | Fallback Readiness | Telemetry Readiness | Confirm Bias | Takeover Safety |
|---|---|---|---|---|---|---|
| `api` | `baseline` | `high` | `browser_host_native_available` | `structured_high` | `not_required` | `hard_forbid_takeover` |
| `browser-host-native` | `baseline` | `high` | `api_available` | `structured_high` | `not_required` | `hard_forbid_takeover` |
| `turix-cua` | `candidate_soft_only` | `medium` | `browser_host_native_required` | `shadow_evidence_required` | `required` | `hard_forbid_takeover` |
| `browser-use` | `candidate_soft_only` | `medium` | `browser_host_native_required` | `shadow_evidence_required` | `required` | `hard_forbid_takeover` |

## Interpretation

- `api` 与 `browser-host-native` 是 BrowserOps baseline；
- `browser-host-native` 只表示宿主已经允许的能力，不绑定外部 MCP；
- `turix-cua` 与 `browser-use` 只能以 `candidate_soft_only` 身份进入 scorecard；
- `browser-use` 的治理含义是 route evidence 补充，而不是第二 orchestrator；
- 任何 `candidate_soft_only` provider 都必须带 `fallback_provider` 与 `confirm_required`。
- provider、fallback 与 considered 均不得包含 forbidden MCP id。
