# GitNexus 基底 overlay（advice-only）接入 VCO

## 目标

把 GitNexus 作为 VCO 生态的**通用底层能力**：让“理解代码/感知变更/评估影响面”更可靠、更可复用。

- VCO 仍负责：Grade 路由、协议（think/do/review/team/retro）、工具链与质量闸门（P5/V2/V3）。
- GitNexus overlay 只负责：提供“如何用 GitNexus 产出证据与范围”的方法与交付物模板（advice-only）。

## 角色定位：为什么它比部门专家更“底层”

- `agency-agents`：补齐**部门/岗位视角**（工程/设计/产品/市场/PM/测试/XR），输出检查清单与交付物模板。
- `GitNexus`：补齐**代码感知底座**（knowledge graph + context/impact/diff→process），把“范围判断”从经验变成证据。

一句话：**agency-agents 是“怎么做得像一个部门”，GitNexus 是“怎么知道自己在改什么”。**

## 设计原则（避免冲突）

- **advice-only**：overlay 不改变 VCO 路由/协议/工具选择。
- **冲突优先级**：用户显式指令 > VCO 协议/质量闸门 > overlay 建议。
- **组合上限**：全局最多选择 2 个 overlay（典型：GitNexus 基底 + 测试门禁 / 工程部）。
- **不强依赖外部工具**：GitNexus 不可用时必须有 fallback（`rg`/`git diff`/入口点追踪）。

## 上游来源与许可证注意

上游仓库（参考/更新）：

- `https://github.com/abhigyanpatwari/GitNexus`

许可证：

- GitNexus 使用 **PolyForm Noncommercial**（见上游仓库 LICENSE）。
- 如果你的 VCO 生态用于商业场景，请先确认该许可证是否符合你的使用方式（必要时替换为自研/可商用方案）。

## overlay 定义位置

GitNexus overlay 模板位于：

- `references/overlays/gitnexus/`

当前提供 4 类可注入 overlay：

- `foundation.md`：底座（context/impact/detect_changes 的最小工作流）
- `impact.md`：影响面分析（blast radius）
- `detect-changes.md`：变更感知（diff → processes）
- `architecture-map.md`：架构地图（clusters/processes + mermaid）

配置文件：

- `config/gitnexus-overlays.json`

## 自动建议 → 确认 → 注入：如何使用

### A) 只用 GitNexus overlay（单独建议）

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-gitnexus-overlays.ps1 `
  -Task "写你的任务描述" `
  -Stage think
```

选择并渲染注入片段（默认最多选 1 个）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-gitnexus-overlays.ps1 `
  -Task "写你的任务描述" `
  -Stage think `
  -Select "1"
```

### B) GitNexus + 部门专家（统一建议，推荐）

统一入口（GitNexus 优先级更高，且支持组合）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-vco-overlays.ps1 `
  -Task "写你的任务描述" `
  -Stage do
```

选择 2 个并渲染注入片段（典型：GitNexus + Testing/Engineering）：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/overlay/suggest-vco-overlays.ps1 `
  -Task "写你的任务描述" `
  -Stage do `
  -Select "1,2"
```

统一建议配置文件：

- `config/vco-overlays.json`

常见调整：

- `top_k`：候选数量
- `max_select`：最多可选 overlay 数（建议保持 2）
- `providers[].priority_boost`：体现 GitNexus 的“底层优先级”
- `stage_fallbacks`：无关键词命中时的兜底候选（跨 provider）

## MCP（工具层）接入草案

如果你希望 GitNexus 从“提示词层”升级为“运行时可调用工具（MCP）”，见：

- `../external-tooling/gitnexus-mcp-integration-draft.md`

如果你希望直接照着命令跑通一遍（Codex CLI + 索引 + 验证 + overlay 注入），见：

- `../external-tooling/gitnexus-execution-checklist.md`
