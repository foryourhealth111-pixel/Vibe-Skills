# External Resource Admission Matrix

## Scope

这份矩阵记录 15 个 upstream 项目如何进入 VCO，而不制造第二控制面、第二 canonical truth-source、第二默认执行 owner，或重复的 prompt / memory / execution surface。

## 15 项逐仓审计矩阵

| Project | Primary Value | 已吸收 | 候选吸收 | 明确不吸收 | 原因 | 下一步动作 |
|---|---|---|---|---|---|---|
| `docling-project/docling` | 文档解析 contract、结构化输出规范 | document-plane canonical contract、`docling-output-spec`、provider policy | provider benchmark / page provenance 细化 | 第二 document runtime / 第二默认解析入口 | 只要 contract，不要新的控制面 | 继续把 canonical contract 同步到 bundled/runtime 并维持 gate |
| `punkpeye/awesome-mcp-servers` | MCP server 目录与发现层 | connector discovery catalog、connector admission matrix | allowlist snapshot / risk tag 扩展 | 自动安装、自动接管 routing | 目录价值高，但 catalog 不能成为执行 authority | 持续把高价值 server 映射进 connector risk classes |
| `ComposioHQ/composio` | 连接器模板、动作面、secret profile 范式 | connector provider contract、action risk classes | provider adapter、confirm-gated write actions | 第二 route owner、第二 workflow runtime | 连接器要受 VCO admission policy 约束 | 扩充 capability matrix 与 admission allow/deny 规则 |
| `activepieces/activepieces` | workflow piece 分类与 automation action surface | connector workflow reference、piece taxonomy | bounded workflow templates | 自动执行 write-heavy automation runtime | 只能吸收 taxonomy / bounded patterns，不能让 piece runtime 进主路由 | 补齐 piece category -> risk class 映射 |
| `Jeffallan/claude-skills` | skill authoring heuristics、quality gates | skill distillation rules、role-pack reference | 技能模板质量规则 | 第二 skill runtime、第二 installer 语义 | 只吸收“怎么写好 skill”，不吸收新 runtime | 继续沉淀进 `references/skill-distillation-rules.md` |
| `VoltAgent/awesome-agent-skills` | 角色卡、技能覆盖图谱 | role-card catalog、capability taxonomy | domain specialist role overlays | 直接 raw catalog 装进 runtime | catalog 适合做治理索引，不适合作为默认执行面 | 继续把高信号角色映射到 role-pack policy |
| `VoltAgent/awesome-claude-code-subagents` | implementer / reviewer / analyst archetype | subagent responsibility patterns、review-board seed | 更细粒度 team-template 提示边界 | 新会话框架、新 subagent owner | VCO 已有 Codex native team runtime，不能再并列一套 | 继续抽象 archetype 到 VCO-native role pack |
| `sickn33/antigravity-awesome-skills` | skill taxonomy、质量 exemplar | skill quality reference、naming / packaging 启发 | selective skill harvest | marketplace 直接进入默认技能面 | 只能挑 proven fragment，不能整包进 runtime | 持续 selective harvest + quality review |
| `awslabs/agent-squad` | supervisor scatter/gather、多 agent handoff 语义 | role-pack / team-template reference | delegation pattern / milestone handoff 细化 | 第二 orchestrator、第二 execution owner | 编排权仍归 VCO / Codex native runtime | 继续把有效 handoff 语义映射到 team templates |
| `filipecalegario/awesome-vibe-coding` | workflow discovery corpus | discovery / eval corpus | workflow benchmark / discovery cards | runtime route takeover | 价值在发现层，不在执行层 | 继续转写为 capability / eval 素材 |
| `mahseema/awesome-ai-tools` | AI tools discovery corpus | discovery / eval corpus | tool scouting notes | 直接作为 runtime tool registry | discovery list 不应直接成为执行 authority | 继续做 coverage gap / capability notes |
| `tukuaiai/vibe-coding-cn` | 中文 vibe coding discovery corpus | multilingual discovery / eval corpus | 中文 workflow / eval 样例 | 第二 prompt/router surface | 保留多语言发现价值，避免新增 runtime 入口 | 继续沉淀成 multilingual discovery notes |
| `ComposioHQ/awesome-claude-skills` | 技能与连接器交叉目录 | selective skill/connector reference | curated pattern cards | 动态技能安装面 | 目录价值高，但必须经过 canonical distillation | 继续映射高信号条目到 capability catalog |
| `dair-ai/Prompt-Engineering-Guide` | prompt patterns、风险审视 heuristics | prompt pattern cards、risk checklist、prompt governance | pattern clustering / review rubric 扩展 | 第二 prompt router、mass keyword routing takeover | 只吸收 prompt intelligence 资产层 | 继续扩展 cards / checklist，不改变 route owner |
| `e2b-dev/awesome-ai-agents` | discovery/eval corpus、agent 案例集合 | discovery / eval corpus | benchmark scenarios / capability cards | 第二 agent runtime | 作为能力发现素材最有价值 | 继续喂给 capability catalog 与 pilot scenario |

## Admission Summary

- `docling` 已经被 productize 为 document-plane canonical contract。
- connector 生态 (`awesome-mcp-servers` / `composio` / `activepieces`) 已进入 connector admission layer，但仍保持 `advice-first / confirm-gated / rollback-first`。
- role-pack 生态 (`agent-squad` / `claude-skills` / `awesome-agent-skills` / `awesome-claude-code-subagents` / `antigravity-awesome-skills`) 只进入 role-pack / skill-distillation governance，不形成第二 orchestrator。
- discovery/eval 生态 (`awesome-vibe-coding` / `awesome-ai-tools` / `vibe-coding-cn` / `awesome-ai-agents-e2b`) 只进入 capability discovery / pilot corpus，不直接接管 runtime。
- Prompt-Engineering-Guide 延续 Wave23 路线：只增强 prompt intelligence 资产层，不改变 route owner。

## Promotion Rule

任何 upstream 资源要从“已登记”推进到更高成熟度，至少需要：

- 对应 governance doc
- 对应 config policy / contract
- 对应 verify gate
- 对应 rollback 说明
- promotion board item
- pilot fixture / eval 入口（若当前 stage ≥ `soft`）
- bundled / runtime freshness 不出现新的 runtime-only authority

换言之，Wave39 之后的准入门槛已经不是旧的“四件套”，而是 **docs + config + gate + board + pilot + rollback + release evidence** 的完整闭环。
