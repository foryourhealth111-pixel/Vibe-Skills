# Vibe 模块驱动编排内核切换执行计划

> **Status: Superseded for execution control.** 本文保留模块主键设计和 TDD
> 迁移记录，但执行交接与完成判定以
> `2026-07-12-vibe-agent-execution-handoff-control-flow-repair-plan.md` 为准。
> 当前合同是：Vibe 冻结模块计划并生成 Agent 交接单，current Agent 阅读已分配的
> `SKILL.md`、完成工作并写入 `module-execution.json`，canonical Vibe 只负责验收和
> 收尾。下文的 `loaded` / `invoked` 状态机不再是活跃运行时合同。

## Internal Grade

XL

这次改动会改变计划、执行、回执和验收的共同主键，并最终删除一批仍以
skill 列表为中心的运行时字段。它涉及 `SKILL.md`、`protocols/**`、
PowerShell 运行时、Python 验收内核、测试和真实安装面，必须按受保护运行时
变更处理。

## 目标

把 canonical `vibe` 从“组织一组 skills，然后证明这些 skills 被执行过”切换为：

1. 冻结用户任务和验收标准。
2. 把任务拆成可执行、可依赖、可验收的模块。
3. 按模块搜索和选择本地 skills。
4. 将确认后的模块、skill 分工和验收要求编译成工作单元。
5. 指导 Agent 按模块依赖执行工作单元。
6. 先验收模块，再根据必要模块的状态验收整个任务。

切换完成后，模块是计划、执行和验收的共同主键；skill 是绑定到模块上的
执行能力，不是任务完成状态的主键。

## 核心职责

canonical `vibe` 必须完整承担以下职责：

1. **需求治理**：与用户澄清并冻结目标、交付物、约束和验收标准。
2. **模块拆分**：形成少量、可执行、可验收的模块及其依赖关系。
3. **Skill 组织**：逐模块检索本地 skills，阅读候选 `SKILL.md`，冻结分工和能力缺口。
4. **执行编排**：把批准后的分工编译为工作单元，按依赖和 L / XL 拓扑指导 Agent 执行。
5. **完成控制**：根据工作单元结果验收模块，根据必要模块状态决定任务是否完成。

## 非目标

本计划不做以下事情：

1. 不为论文、研究、文档、代码或任何具体领域建立专用编排内核。
2. 不修改具体本地 skill 来迁就 Vibe。
3. 不要求所有本地 skills 增加统一的重型 schema。
4. 不通过关键词补丁推断模块完成状态。
5. 不把“已选择、已加载或已调度”升级为“已贡献或已验收”。
6. 不保留新旧两套执行真相的长期兼容回退。

## 必须保持的运行时边界

canonical 六阶段保持不变：

1. `skeleton_check`
2. `deep_interview`
3. `requirement_doc`
4. `xl_plan`
5. `plan_execute`
6. `phase_cleanup`

本次切换改变各阶段之间传递的执行真相，不新增第二套入口、第二份需求或第二份
计划。

## 目标状态模型

以下状态互不等价，也不得自动升级：

```text
candidate
-> selected
-> loaded
-> invoked
-> contributed
-> module_accepted
-> task_accepted
```

- `candidate`：Agent 阅读过并保留为模块候选。
- `selected`：进入用户批准的模块分工。
- `loaded`：对应 `SKILL.md` 已加载。
- `invoked`：Agent 已按工作单元进入该 skill 的原生工作流。
- `contributed`：产生了可观察的模块结果。
- `module_accepted`：模块验收标准已经满足。
- `task_accepted`：所有必要模块已经通过，任务级验收成立。

任何通用执行清单、计划文档、dispatch 记录或 Agent 自述都不能跨级替代后续状态。

## 真相层级

运行时只保留四层有明确生命周期边界的真相：

### 1. 冻结需求

来源：requirement document。

负责用户目标、交付物、约束、任务级验收和人工检查要求。

### 2. Agent 组织结果

来源：`agent_skill_organization_v1`。

负责模块草案、逐模块候选、最终 skill 选择、职责、理由和未覆盖模块。它是
`xl_plan` 的输入，不直接证明执行或完成。

### 3. 批准后的模块工作计划

来源：`module-work-plan.json`，schema 为 `module_work_plan_v1`。

负责批准后的模块依赖、执行方式、skill 分工、工作单元和模块验收标准。它是
`plan_execute` 的唯一调度 authority。

### 4. 模块执行与验收

来源：`module-execution.json` 和 `delivery-acceptance-report.json`。

前者记录工作单元的调用、结果和证据；后者先聚合模块验收，再聚合任务验收。

## 数据合同

### `module_work_plan_v1`

最小结构：

```json
{
  "schema_version": "module_work_plan_v1",
  "source_run_id": "run-id",
  "requirement_digest": "sha256",
  "organization_digest": "sha256",
  "workflow_level": "L",
  "modules": [
    {
      "module_id": "module-a",
      "goal": "完成一个可验收的用户目标",
      "required": true,
      "depends_on": [],
      "execution_mode": "skill_assigned",
      "acceptance_criteria": [
        {
          "criterion_id": "criterion-a",
          "description": "模块结果满足冻结要求",
          "verification_mode": "automated"
        }
      ]
    }
  ],
  "work_units": [
    {
      "unit_id": "module-a--skill-a--owner",
      "module_id": "module-a",
      "skill_id": "skill-a",
      "role": "owner",
      "responsibility": "负责模块主要结果",
      "depends_on_unit_ids": [],
      "expected_outputs": ["模块结果"],
      "verification": ["执行模块验证"]
    }
  ]
}
```

模块执行方式只允许：

- `skill_assigned`：由一个或多个本地 skills 承担。
- `agent_direct`：用户批准的计划明确允许 Agent 直接完成。
- `blocked_gap`：必要能力缺失；不得进入正常完成状态。

`blocked_gap` 模块必须把 Agent 组织中的缺口说明保存在 `gap_reason`，并在
cleanup 中同时向用户说明阻塞模块和原因。

工作单元角色只表达当前模块中的职责：

- `owner`：负责主要模块结果。
- `support`：产生被 owner 使用的局部结果。
- `verifier`：验证模块结果。

第一轮不增加更多角色。

### `module_execution_v1`

最小结构：

```json
{
  "schema_version": "module_execution_v1",
  "source_run_id": "run-id",
  "module_work_plan_digest": "sha256",
  "units": [
    {
      "unit_id": "module-a--skill-a--owner",
      "module_id": "module-a",
      "skill_id": "skill-a",
      "role": "owner",
      "state": "contributed",
      "result_summary": "产生了模块主要结果",
      "evidence_paths": ["path/to/module-result"],
      "verification_results": []
    }
  ],
  "modules": [
    {
      "module_id": "module-a",
      "state": "accepted",
      "criterion_results": []
    }
  ]
}
```

工作单元状态只允许：

- `pending`
- `ready`
- `invoked`
- `contributed`
- `failed`
- `blocked`

模块状态只允许：

- `pending`
- `in_progress`
- `accepted`
- `failed`
- `blocked`
- `manual_review_required`

## 用户体验合同

### Requirement 阶段

- 说明 Agent 会如何拆模块和按模块寻找本地 skills。
- 在用户选择 L / XL 前，分别说明两种任务级工作流和候选分工。
- 候选不得表述为已经调用或已经产生贡献。

### Plan 阶段

- 按模块说明目标、依赖、skill 分工、执行方式、验收标准和缺口。
- L / XL 的差异是执行拓扑和协调深度，不是简单的 skill 数量差异。
- 用户批准的是可执行模块计划，不是一个 skill 名单。

### Execute 阶段

- 按模块报告进度、阻塞和下一步。
- 不向普通用户倾倒内部 schema、摘要或状态码。
- 只有对应工作单元产生可观察结果时，才报告 skill 对模块产生了贡献。

### Cleanup 阶段

- 先说明用户任务是否完成。
- 再说明必要模块、人工检查和能力缺口。
- 所有必要模块未通过时，禁止完整完成语言。

## TDD 测试边界

用户已确认以下公共边界。测试必须观察行为和产物，不锁死私有函数调用：

1. **组织结果 -> 模块计划**：观察 `module-work-plan.json`。
2. **模块计划 -> 执行调度**：观察工作单元、依赖顺序和实际 skill 绑定。
3. **执行回执 -> 模块状态**：观察模块是否 accepted、failed、blocked 或等待人工检查。
4. **模块状态 -> 任务验收**：观察完整完成语言是否允许。
5. **运行状态 -> 用户沟通**：观察信息是否完整、诚实、以模块为中心。

测试不得用以下方式代替行为证明：

- 检查某个私有函数调用次数。
- 只扫描某句固定提示词。
- 通过最终报告中出现 skill 名称证明该 skill 产生过贡献。
- 通过通用 execution manifest 证明所有已选 skills 都已执行。

## TDD 纵向切片

每个切片严格执行：一条公共边界测试 RED -> 最小实现 GREEN -> 下一条 RED。
不先批量写出所有测试。

### Slice 1：单模块、单 skill、L 级贯通

RED：

- 冻结组织结果无法生成 `module_work_plan_v1`。
- 仅 selected / loaded 不能让模块 accepted。
- `plan_execute` 必须产生带 `module_id` 的工作单元。
- 有效工作单元结果通过后，必要模块和任务才通过。

GREEN：

- 从现有 `agent_skill_organization_v1` 编译最小模块计划。
- L 级按一个工作单元串行推进。
- 用模块状态驱动任务验收。

### Slice 2：一个模块、多个 skills

RED：

- `support` 完成不能替代 `owner`。
- 计划要求 verifier 时，owner 完成但 verifier 未完成不能验收模块。
- 多个 skills 不能只引用同一通用最终产物就全部 contributed。

GREEN：

- 实现 `owner`、`support`、`verifier` 三种角色的最小完成规则。

### Slice 3：模块依赖和 L / XL 拓扑

RED：

- 前置模块未 accepted 时不得调度下游模块。
- L 必须按拓扑顺序串行。
- XL 只能并行无依赖且写入范围不冲突的工作单元。
- 一个并行工作单元失败时不得把整个波次写成成功。

GREEN：

- 从模块依赖计算 ready 单元。
- 复用现有 L / XL 执行设施，但调度输入切换为模块工作单元。

### Slice 4：缺口、失败和计划修订

RED：

- 必要模块为 `blocked_gap` 时任务不能通过。
- `agent_direct` 未在批准计划中声明时不得作为静默回退。
- skill 调用失败不得自动改写成 contributed。
- 计划摘要变化后，旧执行回执必须失效。
- 新 skill 未经计划修订和用户批准不得进入执行。

GREEN：

- 实现计划摘要绑定、失败传播和显式重入修订。

### Slice 5：模块验收

RED：

- 必要模块没有验收项时不得直接 accepted。
- 自动验证失败时模块 failed。
- 必需人工检查未完成时模块和任务进入 `manual_review_required`。
- 可选模块失败不得伪装成功，但不自动阻断必要模块完成。

GREEN：

- 让 delivery acceptance 先汇总模块标准，再汇总任务级结果。

### Slice 6：用户协作体验

RED：

- 计划只列 skills、不解释模块目标和职责时不满足公开合同。
- 进度只报告 skill 状态、不报告模块影响时不满足公开合同。
- 必要模块未通过却使用完整完成语言时失败。

GREEN：

- requirement、plan、execute、cleanup 的公开投影统一切换为模块叙事。

### Slice 7：旧真相删除

只有新路径已经通过前六个切片后，才删除旧路径。

目标删除：

- `work_binding`
- `selected_skill_execution`
- `frozen_selected_skill_execution`
- `specialist-execution.json`
- 只按 skill ID 聚合完成状态的逻辑
- generic execution manifest 作为 skill 使用或贡献证据的逻辑
- 对应旧测试、fixture、文档和安装清单字段

不得保留读取回退、双写或静默转换器。旧字段输入应 fail fast，直到旧输入面完全删除。

## 通用评估集

使用仓库内临时 fixture skills，不依赖用户真实 skill 库：

1. 单模块代码修复。
2. 多模块代码加文档。
3. 资料检索加结构化总结。
4. 数据检查加统计分析。
5. 产物生成后独立验证。
6. 一个必要模块没有可用 skill。
7. 一个 skill 覆盖两个模块。
8. XL 中两个独立模块并行，第三个等待它们。
9. 用户修订计划导致旧回执失效。
10. 所有脚本退出成功，但必要模块验收失败。

测试 skill 使用中性名称，例如 `module-owner-a`、`module-support-b`、
`module-verifier-c`，以证明内核不依赖论文、代码或文档场景。

## 主要代码面

- `scripts/runtime/VibeRuntime.Common.ps1`
  - 验证和编译模块工作计划。
  - 计算计划摘要和模块状态。
- `scripts/runtime/Write-XlPlan.ps1`
  - 输出机器可读 `module-work-plan.json` 和用户可读模块计划。
- `scripts/runtime/Invoke-PlanExecute.ps1`
  - 从模块工作计划读取工作单元并按依赖调度。
- `packages/verification-core/src/vgo_verify/runtime_delivery_acceptance_runtime.py`
  - 从模块执行结果计算模块和任务验收。
- `scripts/runtime/invoke-vibe-runtime.ps1`
  - 在 canonical 阶段之间投影新产物。
- `SKILL.md`、`core/skills/vibe/instruction.md`、`protocols/runtime.md`
  - 在行为稳定后更新最终公开合同。

## 迁移纪律

1. 当前工作区包含已完成的 Agent-led skill discovery cutover，不得回退。
2. 本计划批准前产生的实验性“贡献证据”改动不算正式完成；只有被本计划的
   RED 测试覆盖并符合模块主键后才保留。
3. 新旧执行真相可以在单个 TDD 切片内部短暂共存用于比较，但不得作为切片完成状态。
4. 每个切片结束时只能有一个正式 authority。
5. 不添加兼容猜测、默认模块、默认 skill 或 silent fallback。

## 验证顺序

每个切片：

1. 运行单条 RED 测试并保存预期失败。
2. 实现最小 GREEN。
3. 运行当前文件和最近相关测试。
4. 更新 `work/thread_state.md` 的证据和下一步。

阶段性验证：

1. 模块计划和执行聚焦测试。
2. `tests/runtime_neutral`。
3. 完整 `py -3 -m pytest -q`。
4. `git diff --check`。
5. 旧字段、脚本、fixture 和文档主动扫描。

真实安装验证：

1. 安装当前本地 checkout 到真实 Codex skills 目录。
2. 运行 installed check，确认无 missing 和 drift。
3. 执行一个 L 级单模块 smoke。
4. 执行一个 XL 级多模块依赖 smoke。
5. 故意缺失一个必要工作单元，确认安装版不会假成功。
6. 确认 requirement 和 plan 两个用户停点仍然有效。

## 完成标准

只有同时满足以下条件，模块驱动切换才算完成：

- canonical 六阶段和两个用户确认停点保持有效。
- 模块工作计划是 plan_execute 的唯一调度 authority。
- 每个 skill 调用都属于明确模块和工作单元。
- selected、loaded、invoked、contributed、module accepted、task accepted 不再混用。
- L 和 XL 使用同一模块计划模型，只改变执行拓扑。
- 必要模块存在缺口、失败或人工检查时，完整完成语言被阻止。
- 旧 skill 中心字段、脚本、fixture、测试和公开文档已删除。
- 聚焦测试、runtime-neutral、完整回归和真实安装 smoke 全部通过。

## 当前基线

计划编写前最近一次完整回归：

```text
1246 passed, 6 skipped, 1 failed
```

唯一失败是 `SKILL.md` 超过现有 245 行限制。该失败来自计划批准前的实验性
公开合同扩写，不能通过放宽测试解决；应在对应行为由测试保护后压缩公开说明。

## 执行结果

状态：**已完成（1-10 全部完成）**

完成后的正式主链为：

```text
agent_skill_organization
-> module-work-plan.json
-> module-execution.json
-> module acceptance
-> task acceptance
```

最终验证：

- 聚焦组织测试：`18 passed`。
- 聚焦交付验收测试：`18 passed`。
- 完整回归：`1255 passed, 6 skipped`。
- PowerShell：`275` 个脚本解析通过。
- Python `compileall`：通过。
- 模块调度闭环、子级 skill 升级和根子层级门禁分别通过 `27`、`39`、`42` 条断言。
- 活跃面旧字段和旧脚本扫描：`0` 个命中。
- 真实 Codex 安装检查：无 missing，无 drift。
- 安装版 requirement 与 plan 两个用户停点保持有效。
- 安装版 L 单模块 smoke：串行执行，只有贡献和模块验收成立后才允许 `PASS`。
- 安装版 XL smoke：两个独立模块有限并行，依赖模块等待上游；全部模块验收后才允许 `PASS`。
- 安装版故意失败 smoke：必要模块保持 `blocked`，交付为 `FAIL`，禁止完整完成语言，并同时报告模块和 `gap_reason`。

最终安装证据根目录：

```text
C:/Users/羽裳/AppData/Local/Temp/vibe-module-kernel-installed-smoke-mrhfgds0-270cf848/final-package
```
