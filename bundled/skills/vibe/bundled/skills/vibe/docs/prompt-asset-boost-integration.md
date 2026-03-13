# Prompt Asset Boost (GPT‑5.2 × prompts.chat 协作增强层)

## Goal

在不引入第二路由器/第二编排器的前提下，让 VCO 在 **显式 `$vibe` / `/vibe`** 场景中：

1. 自动生成 `prompts.chat` 的**搜索策略**（query / tag / type hints）
2. 自动给出少量**可注入的 prompt overlay 候选**
3. 以 **advice-only + 你确认后注入** 的方式增强后续任务执行（更快、更稳、更少来回改 prompt）

## Design Boundary

- **单一路由权威**：Pack Router 仍是控制面。
- **不改 selected pack/skill**：本层只输出 `prompt_asset_boost_advice`。
- **显式 vibe 才启用**：默认 `explicit_vibe_only=true`（prefix 触发）。
- **可降级**：缺 API key / HTTP 错误时直接 `abstain`，不阻断主路由。

## Config Surface

- 主配置：`config/prompt-asset-boost.json`
- bundled 镜像：`bundled/skills/vibe/config/prompt-asset-boost.json`

关键字段：

- `enabled`, `mode`（`off|shadow|soft|strict`）
- `activation.explicit_vibe_only`
- `scope.{grade_allow, task_allow, route_mode_allow}`
- `trigger.{require_prompt_signal, require_explicit_intent, max_queries, max_candidates}`
- `provider`（OpenAI Responses/ChatCompletions：`model/base_url/timeout/max_output_tokens`）
- `output.max_prompt_chars_per_candidate`（避免上下文腐烂）

## Router Injection Point

- module：`scripts/router/modules/49-prompt-asset-boost.ps1`
- route entry：`scripts/router/resolve-pack-route.ps1`
- output field：`prompt_asset_boost_advice`

Probe + heartbeat：

- probe stage：`overlay.prompt_asset_boost`
- heartbeat：`overlay.prompt_asset_boost`

## Advice Contract

`prompt_asset_boost_advice` 主要字段：

- scope/enforcement：
  - `enabled`, `mode`, `scope_applicable`, `enforcement`, `reason`
  - `should_apply_hook`（告诉上层：此时可以执行 prompts.chat 的检索/改写）
- prompt 信号：
  - `prompt_signal_hit`, `explicit_intent`
  - `recommended_skill`（默认 `prompt-lookup`）
- prompts.chat 搜索策略：
  - `search_plan.queries[]`
  - `search_plan.{category_hints, tag_hints, type_hints, limit}`（可选）
- 注入候选：
  - `overlay_candidates[]`（`role=system|user`, `prompt`, `when_to_use`, `variables`）
  - `confirm_required=true` 时表示 **需要你确认** 再注入
- provider 诊断：
  - `provider.{ok, abstained, reason, api, latency_ms, error}`

## How It Collaborates With prompts.chat

推荐消费方式（上层执行器 / 你手动）：

1. 取 `search_plan.queries[0..]` 作为 `search_prompts.query`
2. 取 `overlay_candidates[0]` 作为“立即可注入”的默认候选
3. 如需更贴合项目语境，可把候选 prompt 交给 `improve_prompt` 二次优化

## Verification

新 gate：

```powershell
pwsh -File .\scripts\verify\vibe-prompt-asset-boost-gate.ps1
```

同时应通过：

- `pwsh -File .\scripts\verify\vibe-config-parity-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-version-packaging-gate.ps1`

