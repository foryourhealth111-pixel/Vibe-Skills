# VCO Changelog

## v2.0.10 (2026-02-24)

- 将决策提问接口从 `AskUserQuestion` 重构为 runtime-neutral `user_confirm interface`
- 将状态记录从 `TodoWrite` 重构为 runtime-neutral `state_store` 抽象
- 同步更新核心文档与 bundled 副本（SKILL / protocols / references / hooks）
- 新增自动化快速自测脚本，覆盖 M/L/XL 三个 `/vibe` 路由场景与关键约束断言

## v2.0.9 (2026-02-24)

- 删除 XL 设计中的 legacy compatibility orchestration 描述，统一为 Codex native agent runtime + ruflo 协作
- team.md 移除 compatibility orchestration option，仅保留 Native+ruflo 与 Native-only 路径
- fallback-chains.md 移除 compatibility Level，XL 仅保留 Native+ruflo -> Native-only -> L-grade sequential
- conflict-rules.md Rule 1 移除 compatibility agent system 条目
- tool-registry.md 移除 compatibility orchestration 集成描述，聚焦 ruflo 与 native team runtime

## v2.0.8 (2026-02-24)

- XL 标准路径明确为 `spawn_agent` / `send_input` / `wait` / `close_agent` 与 ruflo 协作（workflow/memory/consensus）
- team.md orchestration options 调整为：A=Native+ruflo（首选），B=Native-only（ruflo 不可用）
- fallback-chains.md 的 XL 链路更新为 Native+ruflo 优先，并补充 ruflo 不可用时的 native-only 降级
- conflict-rules.md Rule 1 更新为 XL=Native+ruflo 主路径，补充 native-only 分支
- team-templates.md 全量迁移为 native agent type (`default`/`explorer`/`worker`) 与 `send_input` 通信语义
- review.md 移除 `Task tool + subagent_type` 的旧表述，改为单代理直接调用 code-reviewer

## v2.0.7 (2026-02-24)

- XL execution primary path switched to Codex native agent orchestration (`spawn_agent` / `send_input` / `wait` / `close_agent`)
- Legacy compatibility fallback path downgraded from primary XL design
- Added explicit `build-error-resolver -> error-resolver` compatibility mapping in fallback and tool-detection guidance
- Updated team protocol role mapping to native agent types (`default`, `explorer`, `worker`)

## v2.0.6 (2026-02-22)

- C1 修复 conflict-rules.md Rule 1 与 Tool Selection 矩阵矛盾——M 级从"Everything-CC agents"改为"single-agent tools（允许 sc:design/systematic-debugging 等 skill commands，禁止 subagent spawning）"
- C2 修复 L 级 Dialectic Mode 使用只读 Plan agent 的问题——改为 general-purpose agent
- C3 在 SKILL.md Section 2 Tool Selection 矩阵下方添加 Excluded tools 说明（sc:implement 禁令）

## v2.0.5 (2026-02-22)

- Quick Probe 补充中文关键词（设计/架构/重构/迁移/前后端/并行/多智能体）
- index.md 模板数量 5→6
- do.md 术语 "Fallback exception" → "Fallback provision" 与 conflict-rules.md 统一
- retro.md Phase 2 各步骤补充显式 fallback 路径

## v2.0.4 (2026-02-22)

- 新增 dialectic-design 到 specialized agents 列表
- M 级补充 Behavioral Tone 引用
- team-templates 更新为 6 模板
- team.md 新增 Dialectic Mode 完整章节

## v2.0.3 (2026-02-22)

- M 级 stage sequence 移至概览行
- scope check 改为定性+定量 OR 条件
- conflict-rules.md 补充 fallback provision
- 补充探测失败默认行为
- low-friction rule 补充分类反馈格式
- Grade Definitions 增加 Key Signal 列和冲突裁决规则

## v2.0.2 (2026-02-22)

- 修复 do.md L 级 fallback exception 与 conflict rule 的矛盾
- P3/V1 补充内联定义
- team.md 补充 ToolSearch 前置步骤
- SKILL.md M 级补充阶段顺序和影响范围超预期暂停规则

## v2.0.1 (2026-02-22)

- S grade removed (implicit), 4→3 grades, 8→5 protocols, 6→3 conflict rules
- Quick probe + user decision gate added
- Team templates added
