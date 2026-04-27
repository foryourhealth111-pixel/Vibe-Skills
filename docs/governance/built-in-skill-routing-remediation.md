# Built-In Skill Routing Remediation

## Why This Exists

当前内置 skill 库有一个治理断层：

- runtime 实际上已经由 router / canonical `vibe` 决定能力入口；
- 但不少 bundled `SKILL.md` 仍然自称“自动激活”“自动触发”“自动执行”；
- 还有一批 skill 元信息过于模板化，场景边界不清，导致多个 skill 在用户语义上互相重叠；
- 最终结果不是“每个 skill 都能被路由”，而是少数 metadata 更强的 skill 持续赢，其他 skill 长期处于假可用状态。

这不是单个 skill 的文案问题，而是 built-in skill 面没有被当成一个独立治理面。

## Current Findings

2026-04-18 的审计结论：

- bundled skills 总量为 `343`
- 静态路由三表同时接通的只有 `150`
- 部分接通 `125`
- 完全未接通 `68`
- 一批 built-in skills 仍然使用 “Auto-activating / 自动激活 / 自动触发” 等自我触发表述
- 已观察到的真实误差包括：
  - anomaly detector 语义曾难以稳定命中 dedicated anomaly helper；后续 ML 瘦身将该薄模板合并到 `scikit-learn`
  - visualization best practices 未稳定命中 `visualization-best-practices`
  - Obsidian 保存语义未稳定命中 `knowledge-steward`

因此问题可以拆成四层：

1. 语义层错位：skill 文案把“被路由选中”写成“自己会自动触发”
2. metadata 层缺口：并非所有 built-in skill 都在 pack / keyword / routing rule 三层同步定义
3. 场景层重叠：多个 skill 只写宽泛用途，没有写清楚不适用场景与相邻 skill 的分界
4. 验证层缺口：现有 gate 只验证 routed surface 存在性，未验证 built-in corpus 的语义治理质量

## Governance Principles

内置 skills 的整改遵循以下原则：

1. Router 才是运行时入口裁决者
   built-in skill 不能在 `SKILL.md` 中宣称自己会自动激活、自动派发、自动接管。

2. 技能文案与路由元数据分层
   `SKILL.md` 负责告诉人“这个 skill 适合什么问题、不适合什么问题”；真正的命中权重、负关键词、任务类型边界仍由路由配置负责。

3. 场景定义必须可区分
   一个 routed built-in skill 必须能回答三个问题：
   - 它解决哪类主问题
   - 它不解决哪类相邻问题
   - 它与最容易冲突的 1-3 个 skill 如何区分

4. overlap 不能只靠人工记忆
   重叠关系要落到可审计面，包括 `equivalent_group`、负关键词、场景回放案例和关键词冲突报告。

## Remediation Model

### Phase 1: Language Neutralization

目标：先把最危险的错误承诺删掉。

要求：

- bundled built-in skill 不得再出现 “auto-activates / 自动激活 / 自动触发” 一类表述
- 原来的“自动触发条件”统一改为：
  - `When to Use`
  - `Recommended request patterns`
  - `Relevant signals for router or explicit invocation`
- 文案必须明确：skill 是“适用于/适合于/通常在这些请求中被选中”，而不是“自己会启动”

当前波次已经把这个要求落成独立 gate。

### Phase 2: Scenario Contract

目标：把“模糊用途”收紧成可审计的场景边界。

对所有 routed built-in skills 新增 machine-readable scenario contract。推荐字段：

- `problem_domain`
- `primary_user_intents`
- `task_allow`
- `non_goals`
- `disambiguates_from`
- `canonical_examples`
- `negative_examples`

这层 contract 不替代 `SKILL.md`，而是补足 prose 无法稳定被审计的问题。

### Phase 2.5: Route Authority Split

目标：把“谁能抢主路线”和“谁只能当阶段助手”从同一个池子里拆开。

落点：

- 在 `pack-manifest` 上显式声明：
  - `route_authority_candidates`
  - `stage_assistant_candidates`
- `route_authority_candidates` 才参与主路线竞争
- `stage_assistant_candidates` 不再争抢主路线，但会保留在 `vibe` 的 specialist recommendation 面
- 既不在主路线也不在阶段助手名单里的成员，默认视为显式调用优先，而不是偷偷参与自动竞争

这样做的意义是：

- 不再让 `writing-plans`、`planning-with-files`、`aios-pm` 这类阶段/编排技能和领域技能抢同一条主线
- 不再让 `matplotlib`、`seaborn`、`plotly` 这类底层工具名词压过 `scientific-visualization` 这种场景 owner
- 保留 `vibe -> 阶段助手 -> 执行/验证` 这条治理链，不需要再造第二套路由器

### Phase 3: Overlap Closure

目标：处理“多个 skill 描述都像自己该命中”的情况。

治理动作：

- 为相邻 skill 建立 `equivalent_group` 或 canonical owner
- 对宽泛 skill 增加更强的 negative keywords
- 对 helper / utility / post-processing 类 skill 降级为 explicit-only 或 advisory
- 对完全模板化、没有独立场景 owner 的 skill 进行合并、退役或保留为 reference-only

优先治理以下类型：

- Data Analytics / ML Training 模板克隆技能
- 文件写入、结构化存储、自动报告等“广谱型辅助 skill”
- 与研究报告、科学绘图、知识沉淀相邻的宽泛工具 skill

### Phase 4: Verification Closure

目标：让这套治理长期可回归，而不是一次性清理。

验证面分成两类：

- hard fail
  - built-in skill 出现自称自动触发的表述
- audit report
  - routing coverage: full / partial / none
  - boilerplate prose candidates
  - keyword collisions in `skill-keyword-index`
  - overlap review backlog

再往后需要补的是真实 replay case：

- 机器学习批判讨论
- 科研绘图与 figure 产出
- 科研报告与 rebuttal
- 知识沉淀 / Obsidian 保存
- 文件写入失败诊断

## What Changes Now

本次整改先落最小闭环：

1. 新增 `config/bundled-skill-governance-policy.json`
   定义 built-in skills 的自治措辞禁区、boilerplate 审计模式和关键词冲突规则。

2. 新增 `scripts/verify/vibe-built-in-skill-governance-gate.ps1`
   负责：
   - 阻止 built-in skill 再写自动触发表述
   - 统计三表接线完整度
   - 输出 boilerplate / keyword collision backlog

3. 修正文档中存在的高风险 autonomous wording
   先把“错误运行机制描述”改成“路由中立的使用说明”。

## What Does Not Change

- 不引入第二套 router
- 不把测试方式写进产品运行链路
- 不要求 custom skill 立即与 built-in skill 同步整改

custom skill 仍走 `custom_admission.py`：

- `explicit_only` 和 `advisory` 本来就不是 built-in 这个问题
- `auto` 是用户自定义 admission 的显式 opt-in 机制，不等于 bundled built-in skill 可以随意自称自动触发

换句话说：

- built-in skill 的默认运行权来自 repo 治理配置
- custom skill 的运行权来自用户目标根目录里的自定义 admission 配置

两者要分开治理，不能混成一个口径。

## Recommended Next Wave

下一波应优先做三件事：

1. 为 fully routed built-in skills 补 scenario contract sidecar
2. 对 Data Analytics / ML Training 这类模板克隆 skill 做 owner 合并与退役清单
3. 把高价值场景纳入 replay route corpus，锁住实际命中行为

只有这样，built-in skills 才会从“目录里很多，但路由时只赢少数几个”变成“每个被保留的 skill 都有明确 owner、明确边界、明确验证”。
