# 2026-03-20 README EN Detail And GitHub Branding Copy

## Goal

在不改动中文 README 主结构的前提下，把 `README.en.md` 提升到与中文版接近的细节层级，同时补一份可直接用于 GitHub 仓库设置的品牌文案，包括 `About`、`Topics` 和社交预览文案建议。

## Deliverables

- 重写 `README.en.md`，使其结构和信息密度接近当前中文 README
- 新增 1 份 GitHub 品牌文案文档，覆盖：
  - `About` 简介候选
  - `Topics` 推荐列表
  - social preview title / subtitle / copy 候选
- 更新 governed requirement / plan 索引

## Constraints

- 英文版不能只是中文 README 的机械直译，必须保持英文可读性
- 仍然采用 capability-first 叙事，不退回成抽象简介页
- 不新增海报或视觉资产范围
- 不更改中文 README 的现有正文内容

## Acceptance Criteria

- `README.en.md` 具备与中文 README 对应的详细能力矩阵、子领域展开、资源整合、痛点说明和理念收束
- 英文表达自然，适合作为公开仓库首页
- 新增品牌文案文档可直接被用于 GitHub repo settings
- `git diff --check` 通过

## Frozen User Intent

用户明确要求：

- “更能力展示型：像 integrated skills / MCP / agent stack”
- “我希望英文和中文一样详细”

## Evidence Strategy

- 对比 `README.en.md` 与当前中文 README 的结构层级
- 检查品牌文案文档是否覆盖 `About / Topics / social preview`
- 用 `git diff --check` 验证 markdown 与索引更新
