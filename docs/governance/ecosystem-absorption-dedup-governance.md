# VCO 生态吸收、融合与治理总纲

## 1. 文档目的

这份文档定义 VCO（Vibe Code Orchestrator）生态在 Codex 场景下的统一融合与治理方法，目标不是“把更多项目接进来”，而是把外部高价值项目的能力以**可控、可验证、可回退、可去冗余**的方式吸收进现有 VCO 体系。

本总纲回答 5 个问题：

1. 什么样的外部项目值得被吸收。
2. 应该吸收到 VCO 的哪一层，而不是重复造第二套系统。
3. 如何避免路由权、记忆真源、执行权、角色职责的冲突。
4. 如何从 shadow 到 soft/strict/promote 渐进落地，而不是一次性硬接线。
5. 如何把吸收工作沉淀为仓库内稳定可维护的文档、配置、脚本与验证门禁。

## 2. 适用范围

本总纲适用于以下两类资源：

### 2.1 已在 VCO 中形成治理边界的能力

- VCO 核心路由与协议：`SKILL.md`、`protocols/*`
- Pack/Skill 生态：`config/pack-manifest.json`、`bundled/skills/*`
- 后置治理层：OpenSpec、GSD-Lite、memory governance、prompt overlay、ML lifecycle、quality debt、framework interop、system design、cuda kernel、observability
- 外部 expert overlay：GitNexus、agency-agents、TuriX-CUA、RUC-NLPIR overlays

### 2.2 计划进一步深度吸收的高价值项目

- `mem0ai/mem0`
- `dair-ai/Prompt-Engineering-Guide`
- `browser-use/browser-use`
- `simular-ai/Agent-S`
- `letta-ai/letta`

## 3. 融合目标

VCO 的融合目标不是“功能越多越好”，而是同时增强以下 4 个维度：

1. **智能性**：更准地判断任务类型、上下文需要、执行路径与风险。
2. **稳定性**：任何外部资源失效时，核心 VCO 路由仍能工作。
3. **功能性**：在浏览器、GUI、记忆、Prompt、研究等关键场景补齐能力短板。
4. **治理性**：每一次吸收都能说明来源、边界、证据、门禁、回退与维护责任。

## 4. 核心治理原则

### 4.1 单一控制面原则

VCO 是唯一控制面。

这意味着：

- 路由权只属于 VCO pack router 与协议层。
- 外部项目不能成为第二个 orchestrator。
- 外部项目不能绕过 VCO 直接夺取默认执行权。
- 外部项目只能以 pack、overlay、provider、reference、policy contract 等明确定义的形态进入系统。

### 4.2 单层单责原则

每个外部项目进入系统前，必须先回答：

- 它属于哪一层。
- 它只解决哪一类问题。
- 它与现有哪一层最容易冲突。
- 它不应该做什么。

任何项目如果同时试图承担“路由 + 记忆 + 执行 + 规划”多重职责，必须拆分后再吸收，不能整体照搬。

### 4.3 后置治理优先原则

优先把外部资源吸收为：

- post-route advisory
- shadow evaluator
- prompt/contract/reference layer
- optional provider router

而不是直接进入：

- route mutation
- mandatory execution authority
- second workflow surface
- second memory truth source

### 4.4 去冗余优先原则

外部项目进入前，必须做重复性审计：

- 是否与现有 pack/overlay/provider 功能重叠。
- 是否只是在更换术语，但本质能力已经存在。
- 是否会让用户面对两个入口、两套决策树、两套责任边界。

结论只能有四类：

- **已吸收**：已经存在等价或更优实现，不再重复接入。
- **候选吸收**：有新增价值，但必须限定到特定平面。
- **局部吸收**：只吸收方法论、卡片、约束、模板，不吸收整套运行时。
- **明确不吸收**：会形成双轨、双真源、双执行面或维护负担过高。

### 4.5 渐进发布原则

任何新融合必须遵守：

`intake -> mapping -> shadow -> soft -> strict -> promote -> compatibility_materialize_if_needed`

默认不能直接 promote。

### 4.6 回退优先原则

凡是会扩大默认行为面的接入，都必须先有：

- 关闭开关
- 手动回退路径
- 产物级门禁
- 生成式兼容落地策略

## 5. VCO 融合分层模型

| 平面 | 作用 | VCO 当前 canonical owner | 可吸收外部资源形态 | 禁止事项 |
|---|---|---|---|---|
| 控制平面 | 任务分级、路由、协议选择 | `SKILL.md` + `scripts/router/resolve-pack-route.ps1` + `protocols/*` | 路由信号、路由建议、阈值参考 | 第二 orchestrator、第二命令面 |
| 能力平面 | 具体执行技能与 packs | `config/pack-manifest.json` + canonical skill trees | 技能包、角色包、能力 pack | 直接覆盖已有 pack 默认职责 |
| 治理平面 | 后置检查、分阶段约束、风险提示 | OpenSpec / GSD / memory governance / observability | overlay、policy、checklist、gate | 绕过 pack router 直接改路由 |
| Prompt 平面 | prompt 模板、结构模式、风险卡片 | prompts.chat overlay / prompt asset boost | pattern cards、prompt DSL、checklist、prompt contracts | 第二 prompt workflow surface |
| Memory 平面 | session / decision / vector / graph 记忆分工 | `state_store` / Serena / ruflo / Cognee | backend adapter、memory policy、tier router | 第二 canonical memory truth source |
| BrowserOps 平面 | 浏览器任务执行路径决策 | TuriX-CUA overlay + Playwright/Chrome 现有工具 | provider router、web task contract、session policy | 直接替代 VCO 对浏览器能力的选择权 |
| DesktopOps 平面 | GUI/open-world/桌面任务策略 | 当前无正式 desktop control plane，仅可 advisory 扩展 | ACI DSL、shadow advisor、DAG schema | 未经门禁获取默认 GUI 执行权 |
| 证据平面 | 代码理解、影响面、检索、研究证据 | GitNexus + RUC-NLPIR overlays | evidence provider、retrieval contract | 变成第二路由器 |
| 可观测性平面 | telemetry、门禁、推广/回退证据 | observability governance + verify scripts | metrics schema、promotion board | 自动学习后直接改生产配置 |

## 6. 吸收形态与准入规则

| 吸收形态 | 何时使用 | 典型例子 | 进入条件 | 不适用情况 |
|---|---|---|---|---|
| Pack / Skill | 外部项目提供明确且独立的任务执行能力 | AIOS-Core roles、bundled skills | 能形成稳定职责边界 | 与现有 pack 角色完全重叠 |
| Governance Overlay | 外部项目最有价值的是约束、检查、流程钩子 | OpenSpec、GSD-Lite、ML lifecycle | 不改 selected pack/skill 也能提供价值 | 项目本质要求接管控制面 |
| Prompt Asset Layer | 项目价值主要在 prompt 模式、模板、结构 | prompts.chat、Prompt-Engineering-Guide | 可作为 advice/template/checklist | 需要成为第二 prompt router |
| Provider Router | 外部项目适合被封装为某一执行面的 provider | BrowserOps provider | 可以在既有任务类型下作为 provider 候选 | 想直接替代控制面 |
| Memory Backend / Policy | 项目价值在记忆后端或记忆规则 | Mem0、Letta | 能明确区分 backend 与 truth-source | 试图成为第二 canonical memory plane |
| Reference / Contract | 仅吸收方法论、术语、DSL、卡片、规则 | Letta contracts、Agent-S ACI DSL | 方法论价值高但运行时冲突大 | 被误当作可直接执行系统 |
| MCP / Tool Layer | 项目本身是外部工具能力提供者 | GitNexus MCP | 明确工具接口、失败可回退 | 工具不可降级、失败会卡死主流程 |

## 7. 当前生态的总体策略

VCO 当前已经形成的总体策略可以概括为 4 句话：

1. **先收口，再扩张**：先巩固 VCO 控制面与质量门禁，再扩大吸收面。
2. **先运行化，再新增吸收面**：先把已有 overlay、policy、verify、bundled mirror 做稳，再接入更多来源。
3. **先 advisory，再 authority**：外部资源先以建议层存在，表现稳定后再考虑提高约束等级。
4. **先去冗余，再追求覆盖率**：能通过改造现有平面吸收的，不再新增平行平面。

## 8. 重点资源映射矩阵

### 8.1 已形成明确位置的资源

| 资源 | 在 VCO 中的角色 | 当前状态 | 说明 |
|---|---|---|---|
| OpenSpec | 后置治理层 | 已吸收 | 只做治理，不抢路由权 |
| GSD-Lite | planning 协议钩子 | 已吸收 | 只作为 L/XL planning hook |
| prompts.chat | prompt 资产增强层 | 已吸收 | 不做第二 orchestrator |
| Made-With-ML | ML 生命周期治理语义来源 | 已吸收 | 作为 advisory stage/evidence 框架 |
| GitNexus | 代码证据与影响面底座 | 已吸收 | overlay + optional MCP tool |
| agency-agents | 交付视角专家 overlay | 已吸收 | advice-only |
| TuriX-CUA | UI/网页自动化决策 overlay | 已吸收 | CUA vs Playwright vs API |
| RUC-NLPIR assets | retrieval / discovery / context 辅助层 | 已吸收 | 作为 overlay/reference，而非第二控制面 |

### 8.2 新一轮重点吸收资源

| 资源 | 推荐吸收位置 | 吸收状态 | 核心边界 |
|---|---|---|---|
| `mem0` | Memory backend adapter / preference memory | 候选吸收 | 不能成为新的 canonical memory truth source |
| `letta` | Memory/tool governance contract layer | 候选吸收 | 不能成为第二 orchestrator |
| `Prompt-Engineering-Guide` | Prompt pattern cards / risk checklist / chaining templates | 候选吸收 | 不能成为第二 prompt overlay provider |
| `browser-use` | BrowserOps provider router / async web task contract | 候选吸收 | 不能与 Playwright/Chrome/TuriX-CUA 重叠抢执行权 |
| `Agent-S` | DesktopOps shadow advisor / ACI DSL / DAG plan schema | 候选吸收 | 不能直接获得默认 GUI 执行权 |

## 9. 五个新项目的吸收决策

### 9.1 `mem0`

**应吸收的价值**：

- 用户偏好、长期习惯、重复约束的可持续记忆机制
- memory tiering / memory ranking 的思路
- 可作为外部可选 backend 的记忆写入与检索能力

**不应吸收的部分**：

- 把 `mem0` 变成 VCO 默认记忆真源
- 让 `mem0` 覆盖 `state_store / Serena / ruflo / Cognee` 的职责边界

**推荐落点**：

- `Memory Plane` 的 optional backend adapter
- 仅承接“用户偏好 / 长期非结构化偏好记忆”或“可选外部偏好存储”
- 由 memory governance 统一调度，而不是单独暴露为默认入口

**后续建议产物**：

- `docs/design/memory-runtime-v2-integration.md`
- `config/memory-tier-router.json`
- `scripts/verify/vibe-memory-tier-gate.ps1`

### 9.2 `letta`

**应吸收的价值**：

- memory blocks 的分层组织思想
- archival search contract
- tool rules / tool choice constraints
- token pressure / context budget policy

**不应吸收的部分**：

- Letta 自带 agent runtime / orchestration surface
- 让 Letta 成为第二任务编排器

**推荐落点**：

- `Memory Plane` 与 `Governance Plane` 的 contract source
- 输出 VCO 可消费的 policy contract，而不是直接运行 Letta agent

**后续建议产物**：

- `docs/design/letta-policy-integration.md`
- `config/letta-governance-contract.json`
- `references/memory-block-contract.md`

### 9.3 `Prompt-Engineering-Guide`

**应吸收的价值**：

- prompt 结构模式
- prompt chaining / decomposition 模板
- prompt safety / injection / leakage 审查框架
- few-shot / CoT / ReAct / PAL 等模式的 VCO 化卡片

**不应吸收的部分**：

- 原样复制大段上游提示词库
- 把它变成新的 overlay provider
- 在现有 prompts.chat 之外再开一套 prompt surface

**推荐落点**：

- `Prompt Plane` 的 pattern cards、risk checklist、template snippets
- 直接服务现有 `prompt-overlay` 与 `prompt-asset-boost`，而不是新增路由层

**后续建议产物**：

- `references/prompt-pattern-cards.md`
- `references/prompt-risk-checklist.md`
- `docs/governance/prompt-intelligence-governance.md`

### 9.4 `browser-use`

**应吸收的价值**：

- BrowserOps provider abstraction
- 会话、登录态、profile、sandbox、异步 web task 的管理能力
- 浏览器任务对象化与可观察性思路

**不应吸收的部分**：

- 与 Playwright / Chrome DevTools / TuriX-CUA 同时争夺默认浏览器执行权
- 在没有 VCO provider policy 的前提下直接暴露执行入口

**推荐落点**：

- `BrowserOps Plane` 的 provider router / async executor candidate
- 由 VCO 根据任务类型在 `API / Playwright / browser-use / TuriX-CUA` 之间选择

**后续建议产物**：

- `docs/design/browserops-provider-integration.md`
- `config/browserops-provider-policy.json`
- `scripts/verify/vibe-browserops-gate.ps1`

### 9.5 `Agent-S`

**应吸收的价值**：

- Manager/Worker 拆分
- ACI（action command interface）思路
- DAG 规划与失败后重规划
- open-world GUI task 的任务合约和状态推进模型

**不应吸收的部分**：

- 直接把 Agent-S runtime 作为 VCO 默认桌面执行引擎
- 无 shadow 验证即获得 GUI authority

**推荐落点**：

- `DesktopOps Plane` 的 shadow advisor
- `protocols/team.md` 的 DAG / scatter-gather 合约增强参考
- `references/aci-dsl.md` 作为统一动作 DSL 草案

**后续建议产物**：

- `docs/design/agent-s-shadow-integration.md`
- `references/aci-dsl.md`
- `config/desktopops-shadow-policy.json`

## 10. 冲突与去冗余治理规则

### 10.1 路由权冲突

以下情况一律判定为高风险冲突：

- 新项目试图决定 pack/skill 选择。
- 新项目引入 `/xxx` 第二命令面。
- 新项目绕过 `resolve-pack-route.ps1` 做任务编排。

**治理结论**：外部资源只能给 VCO 提供信号、合同、建议、provider 候选，不能替代控制面。

### 10.2 记忆真源冲突

以下情况一律判定为高风险冲突：

- `mem0` 或 `letta` 直接成为默认记忆面。
- 同一类信息允许被两个系统同时声明为 canonical。

**治理结论**：

- `state_store`：session state
- Serena：explicit project decisions
- ruflo：short-term vector cache
- Cognee：long-term graph memory
- `mem0`：optional backend / preference memory
- `letta`：policy / contract source

### 10.3 浏览器与 GUI 执行权冲突

以下情况一律判定为高风险冲突：

- `browser-use`、Playwright、Chrome、TuriX-CUA 同时被视为默认浏览器执行器。
- `Agent-S` 在没有 shadow / safety policy 的情况下直接执行 GUI/open-world 任务。

**治理结论**：

- 浏览器任务先由 `BrowserOps provider policy` 决策。
- GUI/open-world 任务先由 `DesktopOps shadow policy` 观测验证。
- 一个任务只允许一个 primary execution owner。

### 10.4 Prompt 平面冲突

以下情况一律判定为中高风险冲突：

- prompts.chat 与 Prompt-Engineering-Guide 同时作为“主动路由器”。
- 同一个任务同时注入多份相互重叠的 prompt framework。

**治理结论**：

- prompts.chat：资产搜索与 overlay 建议
- Prompt-Engineering-Guide：模式卡片与风险检查
- 两者共同服务现有 VCO prompt plane，不新增第二条 prompt 工作流

### 10.5 角色职责重叠

以下情况一律判定为治理失败：

- 同一任务既由 VCO XL team 编排，又被外部 agent runtime 再次编排。
- 同一职责存在两个默认 owner。

**治理结论**：

- 角色可借鉴，运行时不可叠加。
- 方法论可吸收，authority 必须唯一。

## 11. 标准落地流程

### Phase 0：Intake

输入：上游项目链接、项目摘要、许可证、核心价值假设。

输出：

- `项目 -> 平面` 初始映射
- 初步冲突等级
- 是否值得进入下一阶段

### Phase 1：Mapping

必须回答：

1. 它补的是哪一块空白。
2. VCO 当前是否已有等价能力。
3. 如果已存在，为什么还值得吸收。
4. 最小吸收形态是什么。

输出：

- overlap audit
- absorb / partial absorb / reject 结论
- 拟新增 doc/config/script 清单

### Phase 2：Shadow

要求：

- 不改 `selected pack/skill`
- 不扩大默认 authority
- 只输出 advisory / telemetry / contract artifacts

输出：

- shadow report
- false positive / false negative / override 统计

### Phase 3：Soft

要求：

- 只在明确场景下提升为 `confirm_required`
- 必须可人工拒绝
- 必须保留旧路径

输出：

- soft rollout config
- verify gate 结果

### Phase 4：Strict

要求：

- 只有在证据充分且回退路径明确时才能进入
- strict 也不能越过单一控制面原则

输出：

- promotion recommendation
- rollback command / rollback doc

### Phase 5：Promote + Mirror

要求：

- 文档、配置、脚本、bundled mirror 同步完成
- verify gate 与 config parity gate 通过
- release ledger / changelog 可追踪

## 12. 必要门禁与量化指标

| 指标 | 目标 | 说明 |
|---|---|---|
| `route_stability` | 不下降 | 吸收后不能破坏既有路由稳定性 |
| `fallback_rate` | 不上升或可解释 | 外部资源失效时不能拖累主流程 |
| `confirm_required_precision` | 持续提升 | 只有真正模糊时才升级确认 |
| `duplicate_surface_count` | 趋近于 0 | 同类入口与同类 authority 必须被收敛 |
| `verification_pass_rate` | 上升 | verify/gate 应能有效拦截风险 |
| `latency_cost_budget` | 可控 | 新平面不能显著拉高默认执行成本 |
| `manual_override_acceptance` | 可解释 | 用户经常拒绝说明 advisory 质量不够 |
| `rollback_readiness` | 100% | 每个 promoted 能力都必须可回退 |

## 13. 仓库落地约束

整体融合工作必须优先沉淀到以下位置：

- 文档：`docs/*.md`
- 配置：`config/*.json`
- 治理脚本：`scripts/governance/*.ps1`
- 验证脚本：`scripts/verify/*.ps1`
- 参考卡片：`references/*.md`
- 运行产物：`outputs/verify/*`、`outputs/telemetry/*`
- 兼容落地产物：install/runtime 边界按需生成的 `skills/vibe/bundled/skills/vibe/*`

任何新增融合如果只停留在口头规划，没有进入以上产物层，则视为“未真正吸收”。

## 14. 近期执行优先级

### P0：先收口

- 固化这份总纲为统一准入标准
- 统一 `docs/`、`references/`、`README` 的导航入口
- 以总纲为准校对后续 wave 文档

### P1：先运行化

优先把 5 个新项目吸收到“可治理的壳层”，而不是直接全功能落地：

- `mem0` -> memory backend policy
- `letta` -> memory/tool contract
- `Prompt-Engineering-Guide` -> prompt cards/checklist
- `browser-use` -> BrowserOps provider policy
- `Agent-S` -> DesktopOps shadow contract

### P2：再扩张

在 P1 产物形成后，再考虑：

- verify gates
- shadow/soft rollout
- bundled mirror
- release notes / promotion board

## 15. 决策口径

以后凡是讨论“某个项目是否值得吸收”，都统一用以下句式回答：

1. **它补哪个平面。**
2. **它不补哪个平面。**
3. **它与现有哪一层重叠。**
4. **最小吸收形态是什么。**
5. **进入 shadow 前必须补哪些产物。**

如果这 5 个问题回答不完整，则不允许进入落地阶段。

## 16. 总结

VCO 的正确扩张方式不是把外部高星项目“尽量多地接进来”，而是把它们拆成可治理的能力碎片，映射到 VCO 已经存在的控制平面、治理平面、Prompt 平面、Memory 平面、BrowserOps 平面与 DesktopOps 平面中。

最终目标是形成一个体系：

- 控制面只有一个：VCO
- 真源边界始终明确：路由、记忆、执行、证据各有 owner
- 外部资源优先以 advisory / contract / provider 的方式进入
- 每一次融合都能被验证、被回退、被镜像、被复用

这才是“榨取高价值项目价值”而不把 VCO 生态拖入冗余与冲突的正确方式。
