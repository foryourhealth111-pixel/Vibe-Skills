# Vibe Agent 主导 Skills 检索切换执行文档

## Internal Grade

XL

这不是一个局部补丁，而是一次运行时职责重分配：

- canonical `vibe` 入口要改公开合同
- requirement / plan / execute 三段都要改 truth source
- 旧路由、旧 gate、旧字段都要降级或退役
- 最终还要在真实安装面验证没有把 governed runtime 本身弄坏

所以实现应按分波次推进，但每一波都要保持可回归、可验证。

## 目标

把 `vibe` 从“程序先路由、Agent 再照着执行”的模式，切换成“程序只提供操作指南，Agent 自己拆任务、找 skills、选 skills、组织 skills”的模式。

切换完成后，canonical runtime 的职责应当是：

1. 固定治理流程和停点。
2. 在 requirement 阶段给 Agent 一份明确的 skills 检索与组织说明。
3. 要求 Agent 公开说明模块、候选、最终选择、未覆盖模块。
4. 只在 Agent 明确选定之后，才进入 skills 加载和执行。

canonical runtime 不再承担：

- 公开 shortlist
- 公开 selected task skills
- 用程序分数决定最终技能入选
- 把程序路由结果当成 requirement 阶段的主真相

## 为什么要切

当前方案的结构病已经反复暴露：

- 近义词一变，路由就漂
- 本地 skill 写法一变，owner 就丢
- 复合任务常被压成单 skill 叙事
- 程序 shortlist 和真实可执行组织方案并不是一回事
- 为了兜这些问题，系统开始堆越来越多的桥接词、阈值、排序和补丁

这说明问题不在某个 prompt，也不在某个阈值，而在职责分配本身：

- 程序不擅长在广泛、异构、本地化 skill 库里稳定决定“谁该上”
- Agent 本来就更适合做任务拆分、候选阅读、边界判断和最终组织

因此，这次切换不是“把旧路由再修好一点”，而是直接收缩程序职责。

## 新的目标状态

### 一、runtime authority 仍然是 `vibe`

治理主线不变：

- `skeleton_check`
- `deep_interview`
- `requirement_doc`
- `xl_plan`
- `plan_execute`
- `phase_cleanup`

要变的是 `vibe` 在这些阶段里如何处理 skills。

### 二、route 不再是结果，而是操作说明

“路由”在 canonical path 里不再输出：

- 谁入选了
- 谁排名第一
- shortlist 有多大
- 为什么程序推荐某个 skill

它只输出一份供 Agent 执行的操作说明，暂定为：

- `skill_search_guide`

这份 guide 要告诉 Agent：

1. 先拆任务，再拆模块。
2. 每个模块单独去找相关 skills。
3. 先看本地 skills 根目录，再读候选 `SKILL.md`。
4. 最终按模块覆盖和真实适配度来选，不按全局最高分来选。
5. 找不到 owner 的模块必须诚实报缺口。

### 三、Agent 成为 skills 选择者

Agent 在新模型里承担三层责任：

1. 模块识别
   把任务拆成少量、可操作、可覆盖的模块。

2. 候选筛选
   对每个模块搜索候选 skills，读 `SKILL.md`，辨别谁是 owner，谁只是沾边。

3. 最终组织
   组合出 `L` 和 `XL` 两套执行方案，并说明每个 skill 为什么入选。

### 四、执行只吃 Agent 明确确认后的选择

进入执行阶段时，runtime 只接受 Agent 明确组织出来的技能集合，不再接受程序预选的 `skill_selection` 作为主 authority。

## 非目标

这次切换不做下面这些事：

1. 不追求保留旧的程序 shortlist 语义。
2. 不保留“程序发现候选，然后再偷偷决定谁入选”的半切换状态。
3. 不继续扩写能力桥接词表来修近义词问题。
4. 不把旧 router 继续包装成“只是建议”，但实际上仍控制公开行为。
5. 不为了兼容旧测试继续保留 `selected task skills` 这一公开叙事。

## 核心设计决定

1. canonical runtime 不再把 `route_prompt` / `resolve-pack-route.ps1` 的结果当作 requirement 阶段的技能真相。
2. requirement 阶段的 host-facing surface 要从“路由结果说明”改成“Agent 检索操作说明”。
3. runtime packet 中移除 `skill_selection` 的主 authority 地位，改为记录 `skill_search_guide`。
4. Agent 必须先拆模块，再按模块搜索和阅读 skills。
5. 一个 skill 可以覆盖多个模块，但任何模块都不能被程序暗中判定为“已覆盖”。
6. `explicit_only`、负边界、适用限制仍然保留，但只作为 Agent 选择约束，不再作为程序强路由分数的一部分。
7. 执行阶段只加载 Agent 最终选中的 skills。
8. requirement / xl_plan / execute / cleanup 里的用户公开语言，必须围绕“模块、选择理由、未覆盖模块”组织，而不是围绕“shortlist / rank / selected by router”组织。

## 新公开合同

## Requirement 阶段

### 旧行为

- 公开 shortlist size
- 公开 L / XL selected task skills
- 公开 why these skills
- 当无人覆盖时，仍然容易把任务说成单主线单 skill

### 新行为

Requirement 阶段必须只做四件事：

1. 冻结任务理解
2. 解释 `L` 和 `XL` 的执行深度差异
3. 说明 Agent 接下来会如何找和组织 skills
4. 要求用户确认任务级别

在请求用户确认级别之前，Agent 还必须把选择所需的信息说完整：分别列出 `L` 与 `XL` 的任务级工作流、候选 skill 名称和各自职责。这里公开的是 Agent 阅读 `SKILL.md` 后形成的候选方案，不是程序 shortlist，也不代表已经正式选定或使用；正式选择仍在 requirement 获批后写入 `agent_skill_organization`。

Requirement 阶段的公开话术里，必须出现：

- 会先拆模块
- 会按模块搜索本地 skills
- 会阅读候选 `SKILL.md`
- 会给出 `L` / `XL` 两套组织方案
- 若有缺口会明确说出

Requirement 阶段的公开话术里，不应再出现：

- `Screened task-skill shortlist size`
- `L selected task skills`
- `XL selected task skills`
- `route reason`
- 任何程序排序结果

## XL Plan 阶段

Agent 必须在这里产出：

1. 任务模块清单
2. 每个模块的候选 skills
3. 最终采用的 skills 组合
4. 每个 skill 的职责
5. 未覆盖模块
6. `L` 与 `XL` 的差异说明

这里的“计划”要变成真正的组织方案，而不是程序路由结果的转述。

## Execute 阶段

执行前的技能 truth source 改为：

- Agent 明确确认的 skills 组合

而不是：

- runtime packet 里预生成的 `skill_selection`

## 建议新增的数据合同

为避免运行时重新长出新的隐性真相，canonical packet 只保留最小合同。

建议新增：

### `skill_search_guide`

建议字段：

- `schema_version`
- `skill_roots`
- `search_protocol`
- `selection_rules`
- `disclosure_rules`
- `workflow_level_contract`

其中：

#### `search_protocol`

至少包含：

1. 先拆任务，再拆模块
2. 每个模块单独搜索
3. 先看 skill 名、短描述，再打开 `SKILL.md`
4. 对每个模块最多保留有限候选，避免上下文污染
5. 以 `SKILL.md` 真实用途为准，不以词面碰撞为准

#### `selection_rules`

至少包含：

- 优先选真 owner，不选只沾边的 helper
- 一个 skill 可覆盖多个模块
- `explicit_only` 不默认入选
- 负边界不可跨越
- 没有 owner 时要报缺口，不准伪装覆盖

#### `disclosure_rules`

至少包含：

- requirement 阶段公开搜索办法，不公开程序 shortlist
- xl_plan 阶段公开模块、候选、最终采用和缺口
- execute 阶段公开本次实际启用的 skills

## 影响文件面

### A. canonical instruction 与 requirement-stop 合同

重点文件：

- `core/skills/vibe/instruction.md`
- `scripts/runtime/Write-RequirementDoc.ps1`
- `scripts/runtime/VibeRuntime.Common.ps1`
- `scripts/runtime/invoke-vibe-runtime.ps1`

要做的事：

- 改 `requirement_doc` 的 host-facing contract
- 删除 requirement 阶段对 shortlist / selected skills 的公开依赖
- 改成公开 `skill_search_guide`

### B. runtime packet 真相切换

重点文件：

- `scripts/runtime/Freeze-RuntimeInputPacket.ps1`
- `packages/runtime-core/src/vgo_runtime/runtime_bridge.py`
- `packages/runtime-core/src/vgo_runtime/router_contract_runtime.py`
- `scripts/router/resolve-pack-route.ps1`

要做的事：

- canonical path 不再依赖 `route_prompt`
- canonical packet 不再把 `skill_selection` 作为主真相
- 把 route 降级为 guide 生成或完全退出 canonical path

### C. execute path 重绑

重点文件：

- `scripts/runtime/VibeSkillRouting.Common.ps1`
- `scripts/runtime/Invoke-PlanExecute.ps1`
- `scripts/runtime/Write-XlPlan.ps1`

要做的事：

- 执行阶段改为读取 Agent 最终组织结果
- 计划文档改为真实的技能组织说明
- specialist dispatch 只对 Agent 明确选中的 skills 生效

### D. tests / gate / docs 清理

重点文件面：

- `tests/runtime_neutral/*routing*`
- `tests/unit/*routing*`
- `tests/runtime_neutral/test_governed_runtime_bridge.py`
- `tests/runtime_neutral/test_l_xl_native_execution_topology.py`
- `tests/unit/test_vibe_skill_entry_contract.py`
- `scripts/verify/*routing*`
- `docs/governance/*routing*`

要做的事：

- 删掉或降级“程序 shortlist 必须怎样”的 gate
- 新增“Agent-led guide contract”测试
- 新增“未覆盖模块必须公开”测试
- 更新文档宣称，避免 README 和治理文档继续讲旧故事

## 分阶段执行

## Phase 1: 公开合同切换

### Goal

先让 requirement 阶段不再对用户讲“程序已经选好了哪些 skills”。

### Tasks

- 改 `instruction.md`
- 改 requirement doc writer
- 改 host briefing projection
- 改 requirement-stop 契约测试

### Acceptance

- requirement 阶段不再出现 shortlist / selected skill 公开字段
- requirement 阶段明确说明 Agent 将如何找 skills
- requirement 阶段在请求用户选择前，明确列出 L / XL 的任务级工作流、候选 skill 名称和职责，并标明尚未正式选定或使用
- L / XL 的说明改成“组织方式差异”，不是“程序筛中的 skills 差异”

### Verification

- requirement-stop 合同测试通过
- live installed runtime 在 `requirement_doc` 停点的公开行为符合新合同

## Phase 2: runtime truth 切换

### Goal

把 canonical runtime 的技能真相从 `skill_selection` 切到 `skill_search_guide`。

### Tasks

- 停止在 freeze packet 中构建 canonical `skill_selection`
- route 退出 canonical authority path
- packet 中新增 `skill_search_guide`
- 更新 Python / PowerShell bridge 契约

### Acceptance

- canonical runtime packet 不再依赖程序选 skill
- requirement 和 xl_plan 的公开内容不再从 `skill_selection` 投影
- route 就算保留，也只作为兼容或审计，不再控制主叙事

### Verification

- packet 合同测试通过
- governed runtime bridge 测试通过
- installed runtime smoke 通过

## Phase 3: Agent 组织 truth 接管 execute

### Goal

让执行阶段吃 Agent 明确组织出的 skill 组合，而不是吃程序预选结果。

### Tasks

- 定义 Agent 组织结果的最小结构
- execute 阶段只加载该结构中明确选中的 skills
- skill usage / dispatch / lifecycle disclosure 全部跟随新 truth

### Acceptance

- execute 的 loaded skills 与 Agent 组织结果一致
- skill usage 不再依赖旧 selection projection
- 多模块任务的真实组织结果能穿过 plan -> execute -> cleanup

### Verification

- binary skill usage 相关测试改绿
- plan_execute 的聚焦回归通过

## Phase 4: 旧债清理

### Goal

把旧 router 的公开叙事、旧 gate 和旧字段一起退干净，防止双真相长期共存。

### Tasks

- 删除 requirement / xl_plan 里的旧 wording
- 降级或删除旧 routing gate
- 把保留下来的 router 标注为非 canonical
- 清理 README / governance / release 说明中的旧路由话术

### Acceptance

- 仓库里不再存在“canonical 靠程序 shortlist 选 skill”的公开宣称
- 旧 router 只剩兼容桥或审计工具身份
- 默认回归集不再把程序分数当产品合同

## 新测试框架

默认回归不再测“这个 prompt 必须路由到 skill X”，而改测以下不变量：

1. requirement 阶段是否公开了正确的技能搜索办法
2. Agent 是否先拆模块再找 skills
3. xl_plan 是否把模块、候选、最终选择、未覆盖模块说清楚
4. execute 是否只加载 Agent 明确选中的 skills
5. 缺口是否被诚实暴露

建议测试层：

### Layer A: contract tests

- requirement-stop contract
- packet guide contract
- execute truth-source contract

### Layer B: synthetic corpus tests

用小型假 skill 库测：

- 模块拆分
- 候选搜索
- owner / helper 区分
- 缺口公开

### Layer C: installed host smoke

在真实 `.agents` 安装面测：

- `codex`
- `claude-code`
- `openclaw`
- `opencode`

至少要验证：

- requirement 停点
- xl_plan 组织说明
- execute 不读旧 selection

## 风险与约束

1. 不能让“删除旧路由”意外删除 governed runtime 本身。
2. 不能让 requirement-stop 失去对 `L` / `XL` 的清晰说明。
3. 不能让 execute 在没有 Agent 明确组织结果时静默继续。
4. 不能让“退化成 guide”变成“什么都不约束、全靠模型即兴发挥”。

因此必须保留三类硬边界：

- 阶段停点
- guide 合同
- execute 前必须已有明确组织结果

## 退出标准

只有同时满足下面这些条件，才算切换完成：

1. requirement 阶段不再公开程序 shortlist / selected skills
2. canonical packet 已以 `skill_search_guide` 替代 `skill_selection` 主 authority
3. xl_plan 已变成 Agent 主导的 skills 组织文档
4. execute 已只消费 Agent 明确选中的 skills
5. 旧 routing gate 已不再作为默认产品合同
6. 至少一个真实 installed-host smoke 证明新模型在 live 面可运行

## 当前建议的起手顺序

先做 Phase 1，不要一上来就删 runtime bridge。

原因很简单：

- 先改公开合同，用户立刻就能看到行为变化
- 先把 requirement 叙事切干净，后面再切真相源时更不容易双写
- 先把“程序已经选好了 skill”这层误导拿掉，能最快止损

也就是说，第一波代码不该追求“彻底删光旧路由”，而应追求：

**先把 requirement-stop 变成一份真正的 Agent 技能检索操作说明。**
