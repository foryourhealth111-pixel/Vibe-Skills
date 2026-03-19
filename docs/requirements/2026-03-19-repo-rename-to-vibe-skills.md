# 2026-03-19 Repo Rename To Vibe-Skills

## Goal

为将 GitHub 仓库从 `vco-skills-codex` 更名为 `Vibe-Skills` 提供一份安全、可执行的更名方案，并明确判断更名是否会引起项目内路径或集成崩溃。

## Deliverables

- 给出 GitHub 仓库更名的风险评估
- 给出更名前、中、后的分阶段执行计划
- 标出仓库内需要在更名后清理或同步的文件类别
- 明确哪些内容只是文档/证明残留，哪些内容可能影响真实运行

## Constraints

- 本轮只做规划，不直接执行仓库更名
- 结论需要同时基于 GitHub 官方行为与仓库本地扫描
- 计划必须考虑当前本地工作区为 dirty 状态
- 计划需要覆盖 GitHub 页面、git remote、Issue 模板、文档、历史 proof 与自动化集成

## Acceptance Criteria

- 明确回答“是否会引起项目内路径崩溃”
- 指出更名的最高风险项
- 给出用户可以直接照着做的 rename checklist
- 指出仓库里已发现的硬编码旧仓库名位置类别

## Frozen User Intent

用户要求：

- 把仓库名字改为 `Vibe-Skills`
- 希望知道怎样安全更改
- 希望知道是否会引起项目内路径崩溃
- 希望先拿到一份更名计划

## Evidence Strategy

- 引用 GitHub 官方关于 rename 的行为说明
- 扫描仓库内旧仓库名 `vco-skills-codex` 和 `foryourhealth111-pixel/vco-skills-codex` 的引用位置
- 区分运行时代码依赖、GitHub 配置依赖、文档叙事依赖、历史 proof 依赖
