# Ecosystem Remaining-Value Roadmap

本文件回答一个更具体的问题：在 `P0` 级生态吸收已经完成后，**外部高价值项目还有哪些“剩余价值”值得继续榨取**，以及这些价值应该如何以 **不重复、不失控、可验证** 的方式进入 VCO/vibe。

本路线图是 `docs/governance/ecosystem-absorption-dedup-governance.md` 的后续执行层文档：前者定义 intake / dedup / admission 规则；本文件定义 **下一阶段还能吸什么、为什么现在还没吸、应该落到哪一层、何时进入核心运行面**。

---

## 0. 当前判断

`P0` 已完成的重点是：

- 明确了 `MCP vs skill vs manual` 的准入边界；
- 吸收了 `Agent Squad` 的 supervisor / scatter-gather / task contract；
- 吸收了 `Prompt Engineering Guide` 的 pattern cards + risk checklist；
- 吸收了 `Awesome AI Tools` 的 taxonomy + risk tiers；
- 为 `Docling / Activepieces / Composio` 建立了 `opt-in` 模板与 reference 落点。

因此，下一阶段不应再继续“收集更多名字”，而应转向四类更稀缺的价值：

1. **治理能力**：工具不是越多越好，而是越可控越好；
2. **角色能力**：不是再增加 skill 数量，而是优化 skill/subagent 的元数据、边界和触发质量；
3. **协作能力**：不是再造第二套编排器，而是增强 VCO 现有 XL 协作协议；
4. **验证能力**：不是再加 prompt 资产，而是建立 regression / drift / eval 机制。

---

## 1. 剩余价值的四条主线

### A. Tool Governance / Automation Plane

对应项目：

- `docling-project/docling`
- `punkpeye/awesome-mcp-servers`
- `activepieces/activepieces`
- `ComposioHQ/composio`

剩余价值不是“多接几个 server”，而是把外部工具接入变成一个受管系统：

- 统一工具资产模型：来源、版本、风险、动作类型、密钥要求、egress、quota；
- 准入与运行时双门禁：admission policy + runtime policy；
- 契约测试：关键动作的 schema snapshot、回归用例、破坏性变更检测；
- 文件/文档输入治理：对解析链路建立资源、隔离、输出规范、恶意载荷防线；
- 审计追踪：谁批准了写操作、何时调用、是否发生降级/补偿。

**为什么现在还没吸完**

- `P0` 只解决“怎么接”，没有解决“接了之后如何治理”；
- 当前 `mcp/servers.template.json` 仍偏模板，不是完整的 automation control plane；
- 这类增强一旦做错，会直接扩大运行面风险，因此必须放在 `P1` 谨慎推进。

**推荐落点**

- `config/`：`tool-registry`、`tool-risk-tiers`、`egress-allowlist`、`quotas`、`secrets-policy`
- `scripts/`：catalog sync、contract tests、SBOM/license scan、doc ingest probe
- `references/`：snapshot、schema subset、output spec
- `docs/`：tool onboarding、incident runbooks、automation-plane architecture
- `mcp/`：只保留经过批准的最小执行面

**明确不吸收**

- 不把整个 connector 生态直接拉进默认运行面；
- 不把 `awesome-mcp-servers` 当成可信 registry；
- 不把 Activepieces/Composio 平台逻辑内嵌进 VCO 核心。

---

### B. Skill / Subagent Metadata Hardening

对应项目：

- `Jeffallan/claude-skills`
- `VoltAgent/awesome-agent-skills`
- `VoltAgent/awesome-claude-code-subagents`
- `sickn33/antigravity-awesome-skills`
- `ComposioHQ/awesome-claude-skills`

剩余价值不是“导入更多 skill”，而是提炼 skill/subagent 的元数据与质量规范：

- 更强的 `capability signature` 与触发语义；
- 更细的角色类型与工具权限配置；
- 更严格的 skill spec / review checklist / validator；
- 更清晰的 ownership、handoff、tool-permission 分层；
- 更可靠的 progressive disclosure 和 activation contract。

**为什么现在还没吸完**

- 这些仓库高度重叠，直接导入只会制造路由污染；
- 当前 VCO 已有 skill 生态，但对“skill 本身质量”的治理还可以更细；
- 真正值得吸收的是“元规范”，不是 skill 数量。

**推荐落点**

- `references/skill-spec-delta.md`：对比现有 VCO skill spec 与外部最佳实践的增量清单
- `references/subagent-role-taxonomy.md`：角色 archetypes、permission bundles、handoff pattern
- `config/skill-metadata-policy.json`：描述字段、触发词、tool permission、quality gate 最小要求
- `scripts/verify/skill-metadata-gate.ps1`：检查 frontmatter、trigger、permission bundle、重复能力
- `docs/governance/skill-admission-hardening.md`：为何不导入 awesome skills，只吸 skill spec / archetype

**明确不吸收**

- 不批量导入社区 skills；
- 不引入第二套 subagent runtime；
- 不把 `CLAUDE.md` / 社区 agent prompt 原文作为 VCO 协议的一部分。

---

### C. Session Discipline / Team Execution Discipline

对应项目：

- `filipecalegario/awesome-vibe-coding`
- `tukuaiai/vibe-coding-cn`
- `awslabs/agent-squad`

`P0` 已吸收了 scatter-gather、closure-first、task contract，但还有剩余价值：

- 失败恢复节奏：重试预算、升级条件、回退条件；
- 团队节奏控制：何时允许 follow-up、何时必须 freeze scope；
- 会话卫生：artifact/contract/progress 的最小留痕；
- 任务板/波次（waves）与阶段性验收；
- 长任务的 stall detection、status heartbeat、delta-only communication。

**为什么现在还没吸完**

- 当前 XL 协议已经能用，但对“团队如何不跑偏”约束还可以更细；
- 这些价值更多是执行纪律，不适合一次性进核心，需要渐进注入；
- 如果过早写死为强制协议，会伤害 M/L 级任务的轻量性。

**推荐落点**

- `protocols/team.md`：retry budget、escalation path、freeze-scope rules、delta-only updates
- `protocols/think.md`：planning preflight、failure pre-mortem、closure-first extended contract
- `references/team-templates.md`：wave-based template、recovery template、owner-isolation template
- `config/heartbeat-policy.json` / `config/team-execution-policy.json`：heartbeat、stall、escalation 门槛
- `scripts/verify/team-contract-gate.ps1`：检查 Task Contract 的 owner/output/verify 字段完整性

**明确不吸收**

- 不引入第二 orchestration layer；
- 不把 tmux swarm / canvas UI / 外部任务板当成必需运行依赖；
- 不让 M 级任务承担 XL 协议的复杂度。

---

### D. Prompt / Taxonomy / Eval / Drift Control

对应项目：

- `mahseema/awesome-ai-tools`
- `dair-ai/Prompt-Engineering-Guide`
- `e2b-dev/awesome-ai-agents`

当前 prompt/taxonomy 的剩余价值主要在“验证层”而不是“内容层”：

- prompt regression：某个 pattern/overlay 是否仍能正确触发路由和确认逻辑；
- route drift detection：外部语料更新后，关键词和分类是否污染路由；
- execution/eval taxonomy：不同 agent/execution substrate 的能力维度与风险维度；
- candidate curation：哪些外部项目值得继续镜像与跟踪；
- 评估闭环：不是评估模型，而是评估 VCO 的 route / protocol / outcome 稳定性。

**为什么现在还没吸完**

- `P0` 已经有 prompt cards 和 risk checklist，但尚未形成 regression suite；
- `awesome-ai-agents` 的目录信息已入语料，但没有转成正式的“evaluation axis”；
- taxonomy 已可用于 advice，但仍缺少 drift / mutation 监测。

**推荐落点**

- `references/eval-axes.md`：execution substrate、tooling plane、memory plane、confirmation mode、risk tier
- `config/prompt-regression-cases.json`：template/refine/chaining/PAL 与 ambiguous prompt/doc collision cases
- `config/candidate-curation-policy.json`：镜像项目的纳入、冻结、淘汰规则
- `scripts/verify/prompt-regression-gate.ps1`：回归 overlay / confirm_required / ambiguity behavior
- `scripts/research/score-ecosystem-candidates.ps1`：给镜像仓库打价值/重叠/风险分数
- `docs/evaluation-and-drift-governance.md`：route drift、prompt drift、taxonomy drift 的治理说明

**明确不吸收**

- 不把外部 awesome 列表当作运行时推荐引擎；
- 不复制 Prompt Engineering Guide 的原始 prompt 素材库；
- 不把 agent landscape 目录误当成 VCO 已集成能力。

---

## 2. 项目簇 → 下一阶段榨取重点

### 簇 1：工具治理簇（优先级最高）

包含：`Docling` / `Awesome MCP Servers` / `Activepieces` / `Composio`

优先榨取：

- `tool-registry policy`
- `risk tiers`
- `contract tests`
- `egress/quota/secrets gates`
- `doc ingest isolation`

理由：

- 这是最接近真实副作用与安全风险的层；
- 投入少量治理文件和 gate，就能显著提升可控性；
- 与现有 `mcp/servers.template.json` 高度互补，不会重复。

### 簇 2：skill/subagent 元规范簇（优先级高）

包含：`claude-skills` / `awesome-agent-skills` / `awesome-claude-code-subagents` / `antigravity-awesome-skills` / `awesome-claude-skills`

优先榨取：

- `skill metadata policy`
- `role taxonomy`
- `permission bundles`
- `skill validator gate`

理由：

- 能改善整个 skill 生态的质量，而不增加路由噪音；
- 对 VCO 的长期维护价值高于新增单个 skill；
- 适合通过 `references/config/scripts` 渐进接入。

### 簇 3：协作纪律簇（优先级中高）

包含：`awesome-vibe-coding` / `vibe-coding-cn` / `agent-squad`

优先榨取：

- `retry/escalation budget`
- `heartbeat + stall detection`
- `delta-only updates`
- `wave contract`

理由：

- 直接提升 XL 任务的稳定性；
- 但要谨防把轻量任务复杂化，因此排在工具治理与 skill 元规范之后。

### 簇 4：评测与漂移治理簇（优先级中）

包含：`awesome-ai-tools` / `Prompt-Engineering-Guide` / `awesome-ai-agents-e2b`

优先榨取：

- `prompt regression gate`
- `candidate scoring`
- `eval axes`
- `taxonomy drift detection`

理由：

- 它能提升“长期不变形”的能力；
- 但短期收益低于工具治理与协议硬化，因此适合放在 `P2/P3`。

---

## 3. 分阶段路线图

## P1 — Tool Governance Hardening

目标：把“外部工具接入”从模板状态提升到治理状态。

建议新增/增强：

- `config/tool-registry.json`
- `config/tool-risk-tiers.json`
- `config/egress-allowlist.json`
- `config/secrets-policy.json`
- `scripts/verify/tool-governance-gate.ps1`
- `scripts/research/sync-mcp-catalog.ps1`
- `docs/external-tooling/tool-onboarding.md`
- `docs/architecture/automation-plane.md`

验收：

- 至少 1 个 gate 能验证 registry、risk tier、egress、secrets policy 的一致性；
- 至少 1 个外部 catalog 可被同步到 `references/`，但不会自动进入默认运行面；
- 对写操作型工具能给出强制确认/降级说明。

## P2 — Skill Metadata Hardening

目标：提升 skill/subagent 质量，而不是增加 skill 数量。

建议新增/增强：

- `references/subagent-role-taxonomy.md`
- `references/skill-spec-delta.md`
- `config/skill-metadata-policy.json`
- `scripts/verify/skill-metadata-gate.ps1`
- `docs/governance/skill-admission-hardening.md`

验收：

- 可以自动发现 frontmatter 缺失、permission bundle 不规范、能力重复度过高的 skill；
- 新增 role taxonomy 不改变现有 routing control plane；
- 不引入新的默认 pack。

## P3 — Team Execution Discipline Hardening

目标：让 XL 协作更稳定，而不让 M/L 级变重。

建议新增/增强：

- `config/team-execution-policy.json`
- `scripts/verify/team-contract-gate.ps1`
- `protocols/team.md` 增加 retry / escalation / freeze-scope / heartbeat 条款
- `references/team-templates.md` 增加 wave-based 与 recovery 模板

验收：

- Task Contract 可被 gate 校验；
- XL 长任务出现 stall 时有明确升级/降级策略；
- M 级任务不受额外强制流程影响。

## P4 — Prompt / Taxonomy / Drift Governance

目标：把已有 prompt/taxonomy 资产变成可回归、可监控的系统。

建议新增/增强：

- `config/prompt-regression-cases.json`
- `config/candidate-curation-policy.json`
- `references/eval-axes.md`
- `scripts/verify/prompt-regression-gate.ps1`
- `scripts/research/score-ecosystem-candidates.ps1`
- `docs/evaluation-and-drift-governance.md`

验收：

- overlay/ambiguity/confirm_required 的关键行为可回归；
- 镜像仓库可被打分和排序；
- 不把 candidate list 直接升格为运行面能力。

---

## 4. 反模式（必须避免）

1. **把 awesome list 变成默认 skill 清单**
2. **把 connector 平台变成 VCO 核心运行时依赖**
3. **把社区 prompt 原文复制进协议**
4. **为了“覆盖更多项目”而引入第二路由器或第二编排器**
5. **把 eval/candidate 目录误写成“VCO 已支持能力”**

---

## 5. 最重要的取舍

如果只能继续做一件事，应优先做：

> **P1 Tool Governance Hardening**

因为当前剩余价值里，收益最大、风险最现实、且与现有成果最互补的，不是再加 skill，也不是再扩 prompt，而是把外部工具接入升级为：

- 有 registry，
- 有 risk tier，
- 有 contract tests，
- 有 egress/secrets/quota policy，
- 有文档解析隔离规范。

如果只能继续做两件事，则第二优先是：

> **P2 Skill Metadata Hardening**

因为它能让后续所有生态吸收都变得更干净，不再依赖人工判断“这个 skill 是不是重复”。

---

## 6. 与现有文档的关系

- 本文件不替代 `docs/governance/ecosystem-absorption-dedup-governance.md`，而是其 `P1-P4` 执行路线图。
- 本文件的建议默认是 **advice-only / opt-in / gated rollout**。
- 任何会改变 routing、grade、default pack 的动作，仍需走结构性变更确认门。
