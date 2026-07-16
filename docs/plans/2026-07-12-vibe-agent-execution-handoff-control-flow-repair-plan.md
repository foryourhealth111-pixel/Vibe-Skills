# Vibe Agent 执行交接控制流修复计划

## 结论

本次修复不增加 Skill 读取证明、哈希证明、隐藏执行器或第二套使用账本。
根因是控制顺序错误：Vibe 将本应交给当前 Agent 执行的 Skill 工作记录为一个
瞬时成功的调度结果，随后直接进入 `phase_cleanup`。正确行为是让
`plan_execute` 产出一份可直接执行的 Agent 工作清单并停下；Agent 完成模块后，
再沿同一 canonical `vibe` 入口回流到验收和清理。

## 用户结果

计划获批后，用户应看到 Agent 立即开始按模块使用已选 Skills，而不是看到内核
先完成一轮空执行和清理。Vibe 只负责组织、交接、验收和收尾，不模拟说明型
Skill 的独立进程。

## 保持不变

1. canonical `vibe` 仍是唯一运行时入口。
2. 六阶段名称保持不变。
3. `agent_skill_organization` 仍负责模块和 Skill 分工。
4. `module-work-plan.json` 仍是计划批准后的唯一工作 authority。
5. 必需模块未完成、失败或阻塞时，任务不得宣称完成。
6. L 仍为串行执行；XL 只在依赖和写入范围允许时并行。

## 删除的错误语义

1. `direct_current_session_route` 不再生成 `completed`、`exit_code = 0`、
   `verification_passed = true` 的伪执行结果。
2. 当前 Agent 尚未完成模块时，不再进入 `phase_cleanup`。
3. 不再以 `skill-usage.json`、Skill 文件哈希或独立 artifact-impact 账本决定
   模块是否完成。
4. 不再把“已路由”算作“已执行”或“已解决”。

## 目标控制流

```text
requirement_doc
-> xl_plan
-> plan_execute: 编译 Agent 执行交接
-> 当前 Agent 按交接使用 Skills 并完成模块
-> canonical re-entry: 接收 module-execution.json
-> phase_cleanup: 模块验收、任务验收、收尾
```

`plan_execute` 是执行交接边界，不是新的用户审批边界。计划已经批准后，宿主
Agent 应在同一轮继续执行交接，不再向用户索要一次批准。

## Agent 执行交接合同

运行时在 `plan_execute` 生成 `agent-execution-handoff.json` 和
`host-user-briefing.md`。每个可执行工作单元必须包含：

- `unit_id`
- `module_id`
- `skill_id`
- `skill_entrypoint`
- `responsibility`
- `expected_outputs`
- `verification`
- `depends_on_unit_ids`
- `write_scope`

交接必须用行动语言告诉 Agent：读取哪个 `SKILL.md`、完成什么模块、应产生什么
结果，以及完成后把整份 `module-execution.json` 交回哪个命令。交接状态为
`agent_action_required`，控制所有者为 `agent`。

同一 Skill 覆盖多个模块时，不能把一份职责、角色、输出和写入范围复制到所有
模块。`agent_skill_organization` 必须为每个模块提供独立的
`module_assignments` 条目，角色只能是 `owner`、`support` 或 `verifier`。
XL 单个并行波次最多包含两个依赖已满足的单元；相同、父子或其他重叠写入范围
必须拆到不同波次。

## 回流合同

Agent 完成工作后，通过 canonical `vibe` 提交一份完整的
`module_execution_v1`。运行时必须验证：

1. `source_run_id` 指向产生交接的运行。
2. `module_work_plan_digest` 与批准计划一致。
3. 工作单元和模块集合与计划一致，不允许静默增删。
4. 单元状态只能是 `completed`、`failed` 或 `blocked`。
5. `completed` 单元有非空结果说明；证据路径仅在计划或验收确实要求时必需。
6. 只在所有必需模块均已终结后进入清理；未终结则再次返回 Agent 交接。

回流不是新的需求或计划审批，也不重新搜索或选择 Skills。

## 最小状态模型

计划层：

```text
selected
```

执行层：

```text
pending -> working -> completed | failed | blocked
```

Skill 使用从模块工作直接推导：绑定 `skill_id` 的工作单元进入 `completed`，即表示
该 Skill 已用于该模块。运行时不需要另一份真假可能冲突的使用账本。

## 公开测试接缝

本计划只在以下公开行为接缝测试，不锁定私有函数：

1. canonical `vibe` 在计划批准后的 `runtime-summary.json`、阶段谱系和交接产物。
2. canonical re-entry 接收 Agent 模块结果后的阶段谱系、验收报告和清理收据。
3. `delivery-acceptance-report.json` 对模块结果和 Skill 使用的推导。
4. L 串行与 XL 有界并行的交接顺序。

这些接缝已由用户批准的修复目标确定，不新增实现细节测试。

## TDD 垂直切片

### Slice 1：交接而非伪执行

RED：计划批准后，测试期望 terminal stage 为 `plan_execute`，存在
`agent-execution-handoff.json`，状态为 `agent_action_required`；不存在清理收据，
也不存在空的成功 Skill 执行结果。

GREEN：把当前会话 Skill 工作编译成交接单元，并在清理前返回 Agent。

### Slice 2：交接内容可直接执行

RED：测试逐项要求 Skill 入口、模块目标、职责、预期产物、验证方式、依赖和
写入范围；用户简报必须按 L/XL 顺序列出下一步工作。

GREEN：由 `module-work-plan.json` 直接生成交接，不复制另一套计划逻辑。

### Slice 3：模块结果回流

RED：提交匹配批准计划的完整 `module-execution.json` 后，测试期望运行时复用
原计划进入 `phase_cleanup`，不重新选择 Skills，也不重复执行工作单元。

GREEN：增加严格的 Agent 模块结果输入，并沿同一 canonical 入口恢复收尾。

### Slice 4：未完成不得清理

RED：缺少工作单元、状态仍为 pending/working、计划摘要不匹配时，测试期望明确
拒绝或重新交接，且没有清理收据。

GREEN：在阶段推进前验证模块执行合同。

### Slice 5：从模块推导 Skill 使用

RED：一个绑定 Skill 的 completed 工作单元应在验收报告中显示为已使用；无需
`skill-usage.json`、Skill 哈希或 artifact-impact 记录。未完成工作单元不得显示为
已使用。

GREEN：验收器从 `module-work-plan.json` 与 `module-execution.json` 聚合使用情况，
删除旧账本的完成决定权。

### Slice 6：L / XL 行为

RED：L 交接保持依赖顺序；XL 只把依赖就绪、写入范围不冲突的单元放入同一波次。

GREEN：复用现有模块拓扑，只改变宿主执行方式，不增加调度器。

### Slice 7：真实任务回放

RED/GREEN：使用代码诊断与 TDD、缺失输入阻塞、研究与 Word、XL 数据分析以及
纯检索负向控制任务回放。第一次 canonical 运行停在 Agent 执行交接；当前 Agent
完成模块并提交结果后，第二次运行进入验收和清理，报告从真实模块结果推导所用
Skills。研究与 XL 场景必须各用全新任务连续通过两次。

### Slice 8：角色顺序必须可执行

RED：真实代码计划把“最小改动检查”标成 `support`，导致它在 TDD owner 之前获得
源码写入范围；研究计划也让写作审阅 support 在完整草稿之前运行。

GREEN：公开合同明确 `support` 在 owner 之前提供输入，`verifier` 在 owner 之后
复核；所有后置审阅、最小性检查和 QA 必须使用 `verifier`。运行时在需求停止合同
中公开同一顺序语义。

### Slice 9：Agent 直接模块也要冻结真实工作合同

RED：`agent_direct` 模块被降成 `module:M2`，预期输出只是复述模块目标，无法约束
唯一 cleaned 数据写入者或只读渲染 QA。

GREEN：`agent_direct` 模块必须显式提交具体 `write_scope`、`expected_outputs` 和
`verification`；运行时拒绝缺少任一字段的组织，并原样写入模块工作单。

### Slice 10：可见计划与结构化派工一致

RED：XL 的 `module-work-plan.json` 已有六个任务波次，但 Markdown `Wave Plan` 仍
显示三条通用治理阶段，用户看到的计划与执行权威互相矛盾。

GREEN：可见 Wave Plan 与交接单复用同一个波次生成逻辑，直接列出真实模块、角色、
顺序和有界并行分组。

### Slice 11：结构性计划修订必须替换组织

RED：只提交 `revision_delta` 时，修订文字进入计划说明，但旧
`agent_skill_organization` 和旧派工原封不动。

GREEN：计划停止合同和 Skill 入口明确：凡修改模块、Skills、角色、依赖、写入范围、
输出、验证或级别，必须随 `revision_delta` 提交完整更新后的组织；文字修订本身不
暗中改写结构化计划。

### Slice 12：任务写入范围不能占用运行时结果文件

RED：真实缺失输入计划把两个只读分析单元的 `write_scope` 指向上一轮
`outputs/runtime/vibe-sessions/<run-id>/module-execution.json`，随后又把相同
`stage_order` 误判为 L 级并行风险，导致一份本可批准的计划被无故阻塞。

GREEN：运行时拒绝把 canonical 运行时目录或 `module-execution.json` 声明为模块
写入范围；只读模块使用稳定的任务范围或 `no task-file writes`。入口合同同时说明
`stage_order` 只表示依赖深度，真正的执行分组以可见 Wave Plan 和后续 handoff
波次为准；L 即使有同层独立单元，也仍生成单单元串行波次。

### Slice 13：被读取文档的主题词不能覆盖明确的只读边界

RED：纯本地只读检索任务明确排除代码和 TDD，但目标文件名包含
`agent-execution-handoff-control-flow-repair-plan.md`，运行时把其中的 `repair` / `修复`
当成用户要执行缺陷修复，错误分类为 `debug` 并要求代码 TDD。

GREEN：当任务同时声明只读检索和不做代码时，运行时仍可从目标文档中提取职责、
控制流或策略内容，但不会把被引用标题中的修复主题当成代码动作。PowerShell 与
Python 的任务意图入口都返回 `research`，TDD 为 `not_applicable`，需求说明不再出现
代码 TDD 章节或 `tdd` Skill。

### Slice 14：模块验收不得依赖回流后的成功表述

RED：真实缺失输入计划把 `successful cleanup statement` 和普通的
`completion language` 写进模块验收标准。两者只有在模块结果回流、交付验收和
canonical 清理之后才可能成立，却被计划冻结错误接受。

GREEN：计划冻结拒绝成功清理状态、成功清理声明、完成语言或完成表述等回流后
条件，并继续允许模块在提交结果前删除自己创建的临时文件。错误必须明确说明该
标准应在 canonical 模块结果回流前即可满足。

### Slice 15：Codex 插件 Skill 必须从真实缓存路径直接可用

RED：`documents` 已由 Codex 插件安装并启用，真实入口位于
`~/.codex/plugins/cache/.../skills/documents/SKILL.md`，但 Vibe 只声明普通 Skills
目录，导致计划冻结失败；测试 Agent 只能通过在 `~/.agents/skills` 创建目录链接
绕过问题。

GREEN：Codex 运行时在插件缓存存在时把它纳入本地 Skill 根和
`skill_search_guide`，按包含 `SKILL.md` 的真实目录解析精确 Skill ID，不复制、
包装或链接插件内容。同一缓存中出现多个相同 Skill ID 时必须明确报歧义，不得
静默选择其中一个；非 Codex 主机和不存在的缓存不受影响。

### Slice 16：模块结果合同必须可直接填写并在清理前完整校验

RED：纯本地检索任务完成五个模块后，Agent 仍需猜测
`module-execution.json`。交接虽然列出模块绑定，却没有把 `required`、
`execution_mode`、`gap_reason` 纳入完整提交模板，也没有声明
`criterion_results` 的对象形状和终态词汇。Agent 先遗漏绑定字段，随后提交
`passed=true`、`state=passed` 等猜测格式。canonical re-entry 把不受支持的标准
状态放进 `phase_cleanup`，交付验收失败后，同一运行又因已停在清理阶段而不能
修正重提，最终产生多个新的执行交接运行。

GREEN：`agent-execution-handoff.json.result_contract` 提供一份可复制后直接填写的
`module_execution_v1` 提交模板，冻结全部单元和模块绑定，并明确模块终态为
`completed`、`failed`、`blocked`，标准终态为 `passing`、`failing`、`blocked`。
Python canonical 入口和 PowerShell 直达入口都在进入 `phase_cleanup` 前校验完整模块
绑定、标准集合、标准对象字段和标准终态。格式错误时原运行仍停在
`plan_execute`，Agent 修改同一 `module-execution.json` 后复用原交接命令即可重提，
不重新规划、不重新选 Skill、不生成第二份交接。只有结构完整的结果才能进入交付
验收；验收失败时可以写明未获准的清理收据，但不得执行或宣称成功清理。

### Slice 17：代码 TDD 证据必须随同一模块结果回流

RED：真实代码任务已在 `module-execution.json` 中记录红灯、绿灯、测试命令和最终
差异，但交付验收仍只查找独立 `tdd-evidence.json`。Agent 在 canonical 已进入
`phase_cleanup` 后才发现缺口，只能补写侧车并单独刷新验收；刷新后的
`runtime-summary.json` 宣称 `PASS` 和 `completed`，原清理收据却仍记录
`cleanup_admitted=false`，最终沟通因此错误宣称完整收尾。

GREEN：代码任务的 `agent-execution-handoff.json.result_contract` 在同一
`submission_template` 中提供结构化 `tdd_evidence`，冻结所需红绿证据和覆盖合同。
canonical re-entry 在进入清理前校验该对象；缺失或格式错误时仍停在
`plan_execute`，Agent 修正同一 `module-execution.json` 后重提。交付验收直接读取
该模块结果，不再要求 Agent 创建独立 TDD 侧车。运行时摘要只有在清理收据明确
`cleanup_admitted=true` 后才允许刷新为完成，避免验收报告与清理真值互相矛盾。

### Slice 18：明确排除代码的分析任务不得被否定语句反向分类

RED：真实 XL 数据分析请求明确写明“不要把写代码 TDD、UI 或响应式布局要求注入
这个数据分析任务”，同时又在禁用 MCP 的约束中出现“禁止安装”。运行时只按词面
累计 `工作流` 和 `安装` 等代码标记，因而把数据分析错误分类为 `coding`，并冻结
代码 TDD 要求。

GREEN：Python 与 PowerShell 的公开任务分类入口识别该明确的非代码边界。在任务
已有分析或研究信号时，这个边界压过否定语句内部的代码词，不删除真实代码任务所需
的 `安装`、`工作流` 或其他分类标记。精确黑盒原始请求必须分类为 `research`，代码
TDD 为 `not_applicable`。

### Slice 19：单模块 Skill 必须继承模块已经冻结的工作合同

RED：纯检索计划中的模块已经冻结 `no task-file writes`、具体内存输出和具体核对步骤，
但唯一负责该模块的 Skill 没有重复填写这些可选字段时，工作单被降成通用
`module:<id>`、职责复述和“验收模块标准”的空泛检查，导致交接内容弱于用户批准的计划。

GREEN：当一个 Skill 只负责一个模块且未显式覆盖工作字段时，直接继承该模块的
`write_scope`、`expected_outputs` 和 `verification`，并把相同值带入
`module-work-plan.json` 与 `agent-execution-handoff.json`。Skill 显式填写的字段仍优先；
多模块 Skill 仍必须逐模块提交完整 `module_assignments`，不得把一个通用合同复制到
多个模块。

### Slice 20：引用中的中文“修复”不得被当成真实调试动作

RED：新安装后的纯本地检索任务只允许读取 `路由修复说明.md`，并再次明确“文件名里的
修复只是主题，不是代码开发要求”。运行时虽然识别了非代码边界，却把反引号文件名和
中文引号中的 `修复` 当成肯定式调试动作，再次分类为 `debug` 并注入代码 TDD。

GREEN：非代码边界下的肯定式动作扫描忽略反引号字面量和中文引号字面量；这些内容仍
保留在原始任务、需求文档和普通研究信号中，只是不再充当代码或调试动作。引用之外的
`请修复`、`修改代码` 等真实动作仍照常生效。

### Slice 21：L/XL 选择问句不得把小任务自动升级为 XL

RED：小型串行任务要求 Agent “讲清 L 级和 XL 级分别怎样工作”，运行时把选择问句里的
`XL` 当成用户已经指定的复杂度，错误推荐 XL。直接忽略全部 `XL` 又会掩盖同一请求中
真正的“XL 候选”声明。

GREEN：复杂度判断只从任务文本中移除 L/XL 选择短语，再检查剩余内容。只有选择问句时，
小型研究或代码任务保持 L；另有独立 `XL 候选` 声明时仍保持 XL。

### Slice 22：缺失输入门不得因“已安装”和禁止代码注入而误判为代码任务

RED：digest `ff16c39...` 的全新缺失输入黑盒任务只要求读取需求文件并检查必需 CSV 是否
存在，同时明确“不要注入代码 TDD”。运行时仍把“本机刚安装的 Vibe”中的 `安装` 当成
代码动作；因为任务尚未包含正向研究动作，而且“不要注入代码”不在非代码边界词表中，
已有的肯定动作过滤根本没有运行，最终错误冻结 `task_type=coding` 和 TDD `required`。

GREEN：Python 与 PowerShell 两个公开分类入口都把“不要注入代码”识别为明确非代码边界，
并且不再要求先命中研究词才应用边界内的肯定动作判断。该阻塞门现在分类为 `planning`、
保持 L 且不注入 TDD；真正位于非代码分句之外的实现或修复动作仍分别保持 `coding` 和
`debug`。

### Slice 23：非代码边界不能吞掉真实动作或制造跨入口漂移

RED：进一步审计发现，整分句删除会吞掉同一句边界之前的真实代码动作，并让 PowerShell
在过滤结果为空时中止；肯定动作门禁通过后又使用原始词频，会把否定的安装、修改等词重新
计入代码分数；单一的 `实现`、`添加单元测试`、`修改代码` 会与泛化的“分析”平票并被误判
为研究；支持性的更新与回归测试还会把修复任务从 `debug` 推成 `coding`。PowerShell 另外
遗漏 `refactor`，两个入口都遗漏中文 `调试`，且“不得擅自安装”“不要再修改”和
`don't install` 不会被识别为否定动作。复核还发现 PowerShell 未屏蔽中文智能单引号中的
主题词，原测试因命令引用截断而假绿；Python 的普通 `diagnos` 标记也无法匹配 `diagnose`。

GREEN：显式非代码处理只移除边界短语，不再删除整句；代码与调试分数直接来自边界外的
肯定动作，不再使用含否定词的原始计数。强代码短语只在与泛化研究信号平票时提升代码，
明确调试动作保持对支持性代码动作的优先级。Python 与 PowerShell 同步补齐 `refactor`、
中文 `调试`、`添加单元测试`、`修改代码` 和带修饰词或英文缩写的否定模式。纯非代码文本
稳定返回 `planning`，真实实现、重构、测试添加、代码修改与调试仍注入 TDD。PowerShell
使用 Unicode 正则转义屏蔽中文智能单引号字面量，测试通过临时文件传递完整任务并断言原文
保真；Python 明确覆盖 `diagnose` 等诊断词形。

### Slice 24：canonical 入口不能把已安装 Skill 根当成任务 workspace

RED：五个互不相关的 projectless 黑盒任务虽然把 run 产物写入各自任务目录，但
`runtime-summary.json` 都把 `C:\Users\羽裳\.codex\skills\vibe` 记录为
`workspace_root`，并共同写入该安装根下的 `.vibeskills` 和同一个 workspace memory。

GREEN：canonical 入口继续把 `--repo-root` 作为运行时代码根，但把公开合同中已经作为
`<workspace_root>` 传入的 `--artifact-root` 同步传播为 canonical workspace identity。
任务摘要、输入包、项目描述符和 memory backend 都使用任务目录；运行时代码根的项目描述符
保持不变。直接 PowerShell canonical 入口执行同一映射：只传 artifact 时该目录也是 workspace，
只传 workspace 时 artifact 默认落在它的 `.vibeskills`，同时传入时继续保留两个独立绝对根。
PowerShell runtime 的相对 artifact 解析、真实 session 写入和 storage 报告都使用同一个 workspace，
不再一边报告任务目录、一边把实际文件写回运行时代码根。

### Slice 25：XL 说明不得发明不存在的协调 Skill

RED：需求停点的通用 XL 文案固定声称会使用 `subagent-driven-development`，但没有检查本地
Skill 是否存在，也违背“Vibe 组织、当前 Agent 按冻结计划协调”的执行交接职责。

GREEN：XL 文案只承诺按模块组织更完整的本地 Skills；确需多代理时，由当前 Agent 依据冻结
计划分波次协调，不再假定一个额外协调 Skill。任务 Skill 仍必须由 Agent 搜索并读取真实
`SKILL.md` 后才能进入冻结组织结果。

### Slice 26：没有固定“非代码口令”时，治理词也不能制造代码任务

RED：新的缺失输入任务没有写“不做代码”，但包含“本机已安装的 Vibe”“L 和 XL 的工作流”
以及“禁止安装 MCP”。原分类器只有命中固定非代码短语后才启用肯定动作判断，因此把
`安装` 和 `工作流` 计为代码分，错误冻结 `coding` 与 TDD `required`。

GREEN：Python 与 PowerShell 默认都用现有的肯定式、否定感知动作检测计算代码分，不再先用
原始代码词频。`已安装的`、`禁止安装`、`禁止修改 fixture`、路径和治理名词不会形成代码
动作；真实的实现、安装、重构和修改代码仍保持 `coding`。完整分类文件和公开 runtime 入口
共同保护该行为。强实现动作和明确修复动作的优先级不再依赖“不做代码”口令；支持性的更新
文档和添加测试不会把修复任务改成普通 coding。`Create a Word report`、`Build Excel workbook`、
`Add slides` 和 `Modify report` 不再被通用动词注入 TDD。中文引号里的真实执行要求会保留，
而只读文件名和主题引用仍不会触发代码或调试。

### Slice 27：真实多产物研究应推荐 XL，路径中的 `xl` 不能充当复杂度声明

RED：社区培训分析要求质量审计、清洗数据、脚本、汇总表、PNG 图表、报告和验证证据，
却因不含英文 `parallel/wave/batch` 而自然推荐 L。反过来，简单分析只因输入路径包含
`02-xl-workshops` 就被 PowerShell 推荐为 XL；Python 还无法保留独立的“XL 候选”声明。

GREEN：Python 与 PowerShell 对研究任务使用同一条高置信规则：至少三个相互独立的交付
类别才自然推荐 XL。裸 `xl` 只在脱离 L/XL 选择问句、`xl_plan` 阶段名和路径分隔符时才算
明确等级声明。双向的 `L 或 XL`、`L and XL`、`L vs XL`、`XL 还是 L` 只表示待选择；
明确“不要升级到 XL”、被否定的 script/chart/report 和同名文件不会形成 XL。小型研究仍为 L，
独立 `XL 候选` 仍为 XL，Python 与 PowerShell 对无人值守、并行、波次、批次、跨主机、
端到端、front/back 和 install/runtime 等单一 XL 信号保持一致。

### Slice 28：Windows PowerShell 5.1 必须能加载包含中文的运行时

RED：`VibeRuntime.Common.ps1` 在编辑中丢失 UTF-8 BOM。PowerShell 7 仍能运行，因此普通
测试全部假绿；明确调用 `powershell.exe` 时，中文字符串按本地代码页解码并产生多处
`ParserError`，整个后备运行时无法加载。

GREEN：恢复该中文 PowerShell 运行时文件的 UTF-8 BOM，并增加显式调用 Windows
PowerShell 5.1 的加载和中文分类冒烟测试。PowerShell 7 解析门和 Windows PowerShell 5.1
兼容门必须同时通过，后续编辑不得再次静默去掉 BOM。

### Slice 29：Agent 结果回流后必须保留冻结的业务任务

RED：`agent-execution-handoff.json` 的返回命令使用固定续接句。模块结果回流后，
`cleanup-receipt.json`、memory 写入和最终 `runtime-summary.json` 会把任务改成这句控制文本，
不再表示本次真正获批的业务任务。

GREEN：Python canonical 入口和直接 PowerShell 回流都从原运行的
`runtime-input-packet.json` 读取冻结任务。控制性续接句只负责触发回流，不得覆盖任务真相；
最终摘要、清理收据和运行时 memory 使用同一个冻结任务。

### Slice 30：可选模块失败不得阻断必需模块已经通过的交付

RED：交付验收只要求必需模块完成，但 canonical 回流把任意可选单元或可选模块失败都计入
`completed_with_failures`，使整个任务无法通过，和已经批准的 required/optional 合同冲突。

GREEN：执行清单中的完成、失败和阻塞计数只反映必需模块。可选模块的结果仍完整保留在
`module-execution.json` 中供审计，但不会改变必需工作已经通过的完成状态。

### Slice 31：Agent 已选择的 Skill 不能同时出现在 rejected 审计子集

RED：`skill_routing.rejected` 会复制全部候选，包括已经被 Agent 组织结果正式选择并绑定到
模块的 Skill，导致同一个 Skill 同时显示为 selected 和 rejected。

GREEN：`candidates` 继续保留完整候选审计集合，`rejected` 只保留其中没有被 Agent 选择的
候选子集。两者都保持 audit-only 元数据；真正的执行权限仍只来自
`agent_skill_organization` 和 `module_assignments`。

## 清理范围

在新链路测试通过后，删除或降为非权威调试信息：

- 当前会话路由产生的空 stdout/stderr 和伪成功结果；
- `approved_dispatch_fully_resolved` 将路由视为执行闭环的语义；
- `selected_but_no_artifact_impact` 对任务完成的影响；
- `skill_usage_truth` 对模块完成和任务完成的独立门禁；
- 文档中 `selected -> loaded -> invoked -> contributed` 作为必需执行状态的描述。

若旧字段仍被安装或兼容检查读取，应在同一变更中删除其活跃消费者，不保留静默
兼容回退。

## 验证清单

1. 每个切片先运行目标测试并记录 RED，再做最小 GREEN。
2. 运行 Agent 组织、模块调度、阶段重入和交付验收聚焦测试。
3. 运行 PowerShell 语法解析和 Python `compileall`。
4. 运行仓库完整 pytest 回归。
5. 运行模块调度、根子层级和 canonical truth gates。
6. 安装到两个真实 Skill 根并执行代码/TDD、XL、缺失输入、研究/Word 和纯检索回放。
7. 检查已安装收据无 missing、无 drift。
8. 运行 `git diff --check`，并扫描退役活跃字段和脚本。

## 完成标准

只有以下条件同时成立，计划才算完成：

1. 计划批准后的 canonical 运行在 Agent 执行交接处停止。
2. 当前会话 Skill 工作不再产生伪成功执行记录。
3. Agent 能从交接单直接完成每个模块，不需要猜测下一步。
4. 模块结果通过同一 canonical 入口回流并触发验收、清理。
5. 必需模块未完成时不存在清理和完成语言。
6. Skill 使用由完成的模块工作推导，不依赖独立证明账本。
7. 支持、owner、verifier 的实际顺序与职责一致，Agent 直接模块也有具体工作合同。
8. 用户可见波次与结构化模块波次一致，结构性修订不会只改文字。
9. 任务写入范围不占用 canonical 运行时结果文件，L 的依赖层不会被误解为并行授权。
10. 已启用的 Codex 插件 Skill 可从真实缓存入口直接进入计划，且缓存内同名歧义
    不会被静默解析。
11. 代码 TDD 证据通过同一 `module-execution.json` 回流，完成摘要不会越过未获准的清理。
12. 明确排除代码的任务不会因否定约束中的 `安装`、`工作流` 等词被注入代码 TDD；即使
    缺失输入门没有正向研究词，“不要注入代码”也必须得到同样处理，而边界之外真正的
    代码实现与调试动作仍分别保持 `coding`、`debug` 和 TDD 要求。
13. 单模块 Skill 的最终工作单与模块冻结的写入范围、输出和验证合同一致。
14. 被引用文件名或主题词中的 `修复` 不会被当成肯定式调试动作。
15. L/XL 选择措辞不会自动升级复杂度，同时真正的 XL 声明仍会保留。
16. L、XL、失败路径和真实安装回放全部通过。
17. 显式非代码边界只约束其自身短语，不吞掉同句真实动作；Python 与 PowerShell 对空边界、
    否定动作、实现、重构、单元测试、代码修改、中文调试、英文诊断和智能引号字面量给出
    一致分类与 TDD 决策，测试必须证明完整原始任务实际进入运行时。
18. projectless canonical 任务的 workspace identity、项目描述符和 memory 均落在各自任务
    目录，安装 Skill 根不再承载共享任务状态。
19. 通用 L/XL 说明不再引用未验证存在的协调 Skill。
20. 即使没有固定“非代码口令”，治理词、已安装描述和禁止性约束也不会制造代码 TDD。
21. 多产物研究能自然推荐 XL；路径片段、选择问句和治理阶段名不会伪造 XL 声明。
22. 直接 PowerShell canonical 和 runtime 调用与 Python CLI 使用同一 workspace/artifact
    隔离语义，真实 session 路径与 storage 报告一致。
23. 普通实现、修复、办公文档动作和中文引号动作在没有额外口令时仍得到正确任务类型。
24. Windows PowerShell 5.1 能加载中文运行时文件并执行分类函数。
25. Agent 结果回流后的任务字段、清理收据和最终摘要继续表示冻结的业务任务，而不是控制性
    续接句。
26. 可选模块失败只作为审计信息保留，不阻断已经完成并通过验收的必需模块。
27. Agent 已选择的 Skill 可以继续保留在候选审计集合中，但不得同时出现在 rejected 子集。
