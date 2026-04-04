# TuriX‑CUA overlay（Computer Use Agent，advice-only）接入 VCO

## 目标

把 `TuriX‑CUA` 作为 **真实 UI / 浏览器操作** 的可选执行路径，以 **BrowserOps provider plane** + prompt overlay 的方式接入 VCO：

- VCO 仍负责：Grade 路由、协议（think/do/review/team/retro）、工具链与质量闸门。
- BrowserOps provider plane 负责：在 `API / Playwright / Chrome / TuriX‑CUA / browser-use` 间做受治理的 provider 建议。
- overlay 负责：帮助你在“必须操作 UI”的任务里快速做出 `CUA vs Playwright vs API` 的选择，并约束交付物与回退策略。

## 设计原则（避免冲突）

- **advice-only**：不改变 VCO 的控制面与 Pack 路由，只输出 provider 建议与交付物格式。
- **组合上限**：默认最多选 2 个 overlay（典型：`turix-cua` + `agency-testing`）。
- **不阻塞**：CUA 不可用时必须自动回退（Playwright / API / 人工 SOP），不影响交付推进。
- **不独立升格**：TuriX‑CUA 不是第二编排器，也不是默认执行 owner。

## BrowserOps 治理锚点

Wave24 将 BrowserOps 统一收口到以下资产：

- `docs/design/browserops-provider-integration.md`
- `config/browserops-provider-policy.json`
- `references/browser-task-contract.md`
- `scripts/overlay/suggest-browserops-provider.ps1`
- `scripts/verify/vibe-browserops-gate.ps1`

TuriX‑CUA 在该平面中的定位：
- 适合真实 GUI / 浏览器工作流、弱结构页面、交互式网页流程。
- 默认不是首选 deterministic baseline。
- 在 provider policy 中必须服从 `confirm_required`、fallback 与 rollout stage 约束。

## 上游来源（reference）

- `https://github.com/TurixAI/TuriX-CUA`（MIT）

> 本仓库不 vendoring 上游代码；只保留“可注入的 overlay 模板 + 自动建议脚本 + provider governance”。

## overlay 定义位置

- 配置：`config/turix-cua-overlays.json`
- 模板：`references/overlays/turix-cua/*.md`

当前包含两个 overlay：
- `turix-cua-foundation`：决策树 + 交付物格式 + 回退策略
- `turix-cua-runbook`：最小运行步骤（建议外置执行）+ artifacts 要求

## 自动建议 → 确认 → 注入：如何使用

### 1) 单独建议（只看 TuriX‑CUA）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-turix-cua-overlays.ps1 `
  -Task "写你的任务描述" `
  -Stage do
```

### 2) 统一入口（与 BrowserOps provider plane 协同）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-vco-overlays.ps1 `
  -Task "写你的任务描述" `
  -Stage do

powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-browserops-provider.ps1 `
  -Task "写你的任务描述"
```

推荐顺序：
1. 先用 `suggest-browserops-provider.ps1` 选 provider 候选
2. 再决定是否叠加 `turix-cua` overlay 作为交付视角增强

## 已知限制（重要）

- 上游 `TuriX‑CUA` 当前偏 `mac_agent_env`（屏幕录制权限 + `pyobjc/pycocoa` 等）。
- 在 Windows 环境建议把它当作“可选外部执行器”（或用 Mac runner），默认仍以 Playwright 作为确定性基线。
- 若 provider gate / policy 未通过，不得将 TuriX‑CUA 提升为默认执行路径。

## BrowserOps Provider Governance Extension

Wave24 在既有 `API / Playwright / Chrome / TuriX-CUA` 面之外，引入 **BrowserOps provider governance**，用于治理 `browser-use` 这类 provider candidate。

关联资产：
- `docs/design/browserops-provider-integration.md`
- `config/browserops-provider-policy.json`
- `references/browser-task-contract.md`
- `scripts/overlay/suggest-browserops-provider.ps1`
- `scripts/verify/vibe-browserops-gate.ps1`

边界要求：
1. `browser-use` 只能是 provider candidate，不是 orchestrator。
2. Provider selection 只能给出建议，不得绕过 `confirm_required` 与 VCO 路由。
3. TuriX-CUA 仍保留为现有 UI/browser overlay 参考面，不被新 provider 平面替代。
