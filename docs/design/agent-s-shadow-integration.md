# Agent-S Shadow 集成（VCO DesktopOps）

## 目标

Wave25 的目标不是把 `Agent-S` 引入为新的桌面执行框架，而是把它在 **open-world / ACI / DAG / 长任务分解** 上的高价值经验，压缩吸收到 VCO 的 **DesktopOps shadow advisor 合同层**。

**核心结论：`Agent-S` 在 VCO 中仅作为 shadow / advisory / contract source。**

它不能成为：
- 第二执行面
- 第二编排器
- 第二默认执行 owner
- 默认 GUI takeover 来源

## 吸收边界

### 吸收什么

VCO 只吸收以下能力，并将其转译为合同与治理资产：
- open-world 任务识别与风险建模
- ACI（Action / Checkpoint / Invariant）表达能力
- DAG（节点 / 依赖 / 回退边）拆解方法
- DesktopOps shadow plan 的观察点、确认点、交接边界

### 不吸收什么

以下能力明确 **不进入** VCO：
- `Agent-S` runtime 作为独立执行器
- 默认桌面控制权
- 自动提升为主执行 owner
- 绕过 VCO 的路由、review、gate、rollback

## DesktopOps Shadow 合同层定位

DesktopOps 在 VCO 中只允许产出：
- `shadow_plan`
- `aci_contract`
- `dag_contract`
- `openworld_task_contract`
- `handoff_boundary`
- `risk_advisory`

DesktopOps 在 VCO 中明确禁止：
- `default_gui_owner`
- `implicit_execution_takeover`
- `implicit_promotion`
- `owner_reassignment`
- `route_override`
- `browser_provider_override`

换言之，DesktopOps plane 的职责是：**把原本开放式、跨应用、跨状态的桌面任务，压缩成可审查、可验证、可确认的 shadow 合同。**

## 阶段策略（off / shadow / soft）

| 阶段 | 含义 | 允许内容 | 禁止内容 |
|---|---|---|---|
| `off` | 完全关闭 DesktopOps shadow | 不产出任何 DesktopOps 合同 | 任意桌面 advisory / 合同输出 |
| `shadow` | 默认阶段，仅 advisory / contract | 计划、合同、风险提示、交接边界 | 执行接管、默认 owner、隐式 promote |
| `soft` | 人工确认后可给出更完整分解 | 更细粒度 ACI / DAG / checklist | 仍不得成为默认执行 owner |

**`soft` 不是 promoted，也不是 takeover。** 进入 `soft` 后仍然必须保留：
- `owner = vco_control_plane`
- `confirm_required = true`
- `shadow_only = true`

## 人工确认边界

以下场景必须人工确认，不能由 DesktopOps 默认推进：
- 使用真实账号或本地保存凭证
- 修改系统设置、应用设置、权限或网络状态
- 删除、移动、覆盖本地文件
- 从 BrowserOps 主路径切换到 DesktopOps 跨应用路径
- 触发真实外部提交、发送、付款、发布、同步

## ACI / DAG / Open-World 的 VCO 吸收方式

### ACI 吸收
- 将“动作”变成可审查的 `action node`
- 将“观察点”变成 `checkpoint`
- 将“不可违反约束”变成 `invariant`
- 将“失败后收敛动作”变成 `fallback`

### DAG 吸收
- 将开放式长任务拆成 `node -> depends_on -> fallback_edge`
- 把高风险节点标记为 `manual_confirm_edge`
- 把跨浏览器/桌面切换显式写成 `handoff_boundary`

### Open-World 吸收
- 不再把环境不确定性直接交给外部 agent 执行
- 先收口成 `openworld_task_contract`
- 优先退化到 `BrowserOps` 或人工 SOP
- 只有在合同完备、风险被显式标记后，才允许进入 `soft` shadow 分解

## 与 BrowserOps 的关系

- `browser_only` 任务优先回落到 BrowserOps provider plane。
- `browser_plus_desktop` 任务中，浏览器部分仍由 BrowserOps 主导，DesktopOps 只补合同层。
- `desktop_only` / `multi_app_openworld` 场景下，DesktopOps 也只提供 shadow 合同，而不是接管执行权。

## 关键资产

- `config/desktopops-shadow-policy.json`
- `references/aci-dsl.md`
- `references/openworld-task-contract.md`
- `scripts/verify/vibe-desktopops-shadow-gate.ps1`

## 验证

```powershell
pwsh -File .\scripts\verify\vibe-desktopops-shadow-gate.ps1
```

## Definition of Done

- Agent-S 的价值已被吸收到 DesktopOps **shadow advisor 合同层**
- 文档与 policy 明确声明：Agent-S 不是第二执行面
- `off / shadow / soft` 三阶段与人工确认边界清晰
- gate 能验证：不存在第二默认执行 owner，且不存在隐式 promote
