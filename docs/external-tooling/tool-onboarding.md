# Tool Onboarding

本文件定义 VCO 对外部工具、MCP server、automation platform 与 parser runtime 的统一准入流程。目标不是“更快接更多工具”，而是**把每一个外部能力变成可审计、可回滚、可降级的受管资产**。

## 1. 准入状态

| 状态 | 含义 | 是否默认进入运行面 |
|---|---|---|
| `reference-only` | 仅保留研究材料、catalog snapshot、对比信息 | 否 |
| `candidate-template` | 已形成草案，但尚未通过治理 gate | 否 |
| `approved-template` | 模板已通过审查，可作为项目级启用基线 | 否 |
| `project-enabled` | 某个项目显式启用并完成本地配置 | 是（仅该项目） |

默认原则：**没有 `project-enabled` 就没有运行权限**。

## 2. 必备资产

每一个拟接入工具至少需要以下资产：

- `config/tool-registry.json` 中的一条 registry entry；
- 风险等级：`config/tool-risk-tiers.json`；
- 出网策略：`config/egress-allowlist.json`；
- 密钥策略：`config/secrets-policy.json`；
- 必要时的 output / contract reference；
- 至少一个 verify gate 能证明上述配置彼此一致；
- 对写操作工具给出人工确认与 unattended 边界。

缺任一项时，工具只能停留在 `reference-only` / `candidate-template`。

## 3. Onboarding 流程

### Step 0 — 价值判断

先回答三个问题：

1. 这是 VCO 现有能力缺失，还是只是另一个同类实现？
2. 它进入后会扩大哪一类副作用面：写外部系统、删除资源、开放式联网、密钥暴露？
3. 它应该落在 `manual reference`、`skill`、还是 `MCP`？

如果只是“另一个 catalog / 另一个 connector 列表 / 另一个 orchestration platform”，默认不进入运行面。

### Step 1 — 建 registry entry

在 `tool-registry.json` 中记录：

- `tool_id`
- `integration_surface`
- `approval_state`
- `risk_tier`
- `action_types`
- `data_classes`
- `secret_refs`
- `egress_profile`
- `runtime_profile`
- `human_confirmation`
- `upstream`
- `contract_reference`

要求：字段必须面向治理，不面向营销。

### Step 2 — 定风险边界

按最坏副作用决定 `risk_tier`，而不是按“最常见操作”决定：

- 只读查询 → `tier0_read_only`
- 本地/用户文件变换 → `tier1_bounded_transform`
- 项目/账户范围外写操作 → `tier2_guarded_write`
- 开放世界或高影响控制面 → `tier3_open_world_or_high_impact`

只要存在删除外部资源或开放式第三方写入入口，默认至少 `tier3`。

### Step 3 — 配置 egress / secrets

- 未注册的域名一律拒绝；
- 未注册的密钥引用一律拒绝；
- session 级 endpoint / token 不进入 repo；
- 文档示例中不出现真实 token 或 secret value。

### Step 4 — 建 contract / probe

对 parser、transformer 或高风险 control plane，优先补：

- output contract reference
- catalog snapshot
- contract test / smoke probe
- 失败降级说明

### Step 5 — 跑 gate

最小要求：

```powershell
& ".\scripts\verify\tool-governance-gate.ps1" -WriteArtifacts
```

如果 gate 不通过，不允许把模板提升为 `approved-template`。

### Step 6 — 项目级启用

只有在具体项目中完成以下动作，才允许进入执行面：

- host / token / vault ref 配置齐全；
- 风险告知已写清；
- 写操作需要的确认节点已经接线；
- 回滚 / fallback 路径存在；
- 项目 owner 明确承担控制面责任。

## 4. Runtime 规则

### 写操作

- `tier2` / `tier3` 一律要求 `per_action_required = true`；
- `tier3` 一律 `unattended_allowed = false`；
- 任何 delete/open-world 动作不得默认自动执行。

### 文档解析

- 默认隔离执行，不进入主会话常驻依赖；
- 先产出 artifact，再把精简结果送回主上下文；
- 对大文件和扫描件保留 warning / provenance。

### Catalog

- 外部 catalog 只进入 `references/`；
- snapshot 不得自动写回 `tool-registry.json`；
- 引入 catalog 的目的，是帮助研究与筛选，而不是默认扩大运行面。

## 5. 明确禁止

以下行为在 onboarding 中应被明确拒绝：

- 把 `awesome-mcp-servers` 直接当可信 registry；
- 把 Activepieces / Composio 平台代码并入 VCO 默认 runtime；
- 未分级就开放写外部系统的工具；
- 未定义 egress / secrets / contract 就启用项目模板；
- 用“高星项目”替代治理材料与验证证据。

## 6. 最小检查清单

- [ ] registry entry 完整且字段语义明确
- [ ] risk tier 与 action types 一致
- [ ] egress profile 已注册
- [ ] secret refs 已注册
- [ ] contract / probe / snapshot 已补齐（按工具类型）
- [ ] verify gate 通过
- [ ] 项目级 enablement 文档齐全

只要以上一项未满足，就不应提升到默认执行面。
