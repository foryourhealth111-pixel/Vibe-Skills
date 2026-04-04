# XL Operator Playbook

## 1. Goal

Wave17 的目标不是再“发明一种 XL 工作法”，而是把已经从 `awesome-vibe-coding`、`vibe-coding-cn`、`awesome-agent-skills` 里提炼出来的高价值执行纪律，固化成 VCO 自己的 **operator playbook**。

因此，本 playbook 只做三件事：

- 规范 XL 任务在无人值守条件下如何起步；
- 规范高并发时如何避免文件竞争和思绪发散；
- 规范在 board handoff 之前必须具备哪些验证与 rollback 条件。

---

## 2. Intake Priority

Wave17 把 intake 拆成四个优先带：

1. `bridge-core-gap`：只有明确 gap，且 active lane 无法满足时，才立即 triage；
2. `operator-lift`：优先提炼成 playbook / docs / policy，不直接进入 runtime；
3. `niche-pilot`：只能以 pilot 形式存在，且必须 project-scoped；
4. `hold-until-gap`：价值仍在，但现在继续吸收会带来更多 overlap 和噪声。

这意味着：

- `awesome-vibe-coding` 的剩余价值主要进入 `operator-lift`；
- `vibe-coding-cn` 的中文 operator 价值仍服务于 bridge / playbook，而非独立 command surface；
- `awesome-agent-skills` 只在出现真实 gap 时才重新打开 intake。

---

## 3. XL Checkpoints

### 3.1 `xl-intake-probe`

开始前必须明确：

- 这是在解决 active lane 还是 watch lane 问题；
- 预期影响哪些 artifact family；
- 默认面边界有没有被明确写出。

### 3.2 `wave-contract`

并发前必须做到：

- 按文件集合切 ownership；
- 先定义 wave 成功标准，再扇出 agent；
- 让所有 worker 都知道自己不是独自工作，不能回退别人改动。

### 3.3 `mid-wave-sync`

高并发并不意味着“放着不管”。中途至少要核查：

- 是否出现文件竞争；
- 是否有人在做重复吸收；
- 是否已经偏离“先收口、再扩张”的主线。

### 3.4 `verification-gate`

没有 gate，就没有“已完成”。

本轮至少要求：

- artifact builder 可运行；
- portfolio / consistency gate 有输出；
- promotion 相关文档已和 policy 对齐。

### 3.5 `board-handoff`

最终 handoff 不是“代码写完”，而是：

- review-ready / pilot / hold 分界清楚；
- degraded mode 与 rollback 写清楚；
- 没有 silent promotion 路径。

---

## 4. Explicit Non-Goals

本 playbook 明确不做：

- 不把 XL 运行方式固化成新的 router 默认行为；
- 不因为 agent 并发，就降低验证门槛；
- 不把 workflow 社区项目直接等同于 VCO 的核心编排协议。

---

## 5. Expected Artifacts

Wave17 完成后，应至少具备：

- `config/skill-intake-priority.json`
- `config/xl-operator-checkpoints.json`
- `outputs/governance/xl-operator/xl-operator-checklist.json|md`
- 本 playbook 文档

这些资产共同构成“先运行化，再新增吸收面”的执行底座。
