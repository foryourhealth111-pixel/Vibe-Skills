# 2026-04-05 GitHub Visible Docs Worklog Purge Plan

## Execution Summary

按“先冻结、再删叶子、后修导航、最后验证清理”的顺序，收缩 GitHub 可见 `docs/` 工作日志面。

## Frozen Inputs

- `docs/requirements/2026-04-05-github-visible-docs-worklog-purge.md`
- current repo state on branch `chore/non-bundled-surface-slimming`

## Anti-Proxy-Goal-Drift Controls

### Primary Objective

删除公开 docs 中的日志噪音，同时保留真实活跃的文档契约。

### Non-Objective Proxy Signals

- 不以删除总数代替有效精简
- 不把日志简单平移到另一个仍可见目录
- 不为了整洁破坏脚本、配置、测试或 proof 消费链

### Validation Material Role

验证用于证明保留面正确、引用未断、清理未引入回归。

### Declared Tier

Tight

### Intended Scope

`docs/**` 导航与日志叶子；少量 `references/**` / `CONTRIBUTING.md` 修补。

### Abstraction Layer Target

Repository documentation and governance surface.

### Completion State Target

仅保留当前入口与契约性文档，公开 docs 面不再堆放大批工作日志叶子。

### Generalization Evidence Plan

- exact-path reference checks
- `git diff --check`
- targeted verification after deletion

## Internal Grade Decision

L

## Wave Plan

1. 新增当前 requirement / plan，并重写 `docs/plans/README.md`、`docs/requirements/README.md` 的保留边界。
2. 删除 `docs/audits/`、`docs/archive/status/`、`docs/status/` 中零消费者或工作日志型叶子。
3. 删除 `docs/plans/`、`docs/requirements/` 中零消费者或纯互引叶子，只保留契约性文件。
4. 修补 `docs/README.md`、`docs/status/README.md`、`docs/status/history-index.md`、`docs/status/path-dependency-census.md`、proof 与 contributor/index 导航。
5. 运行校验，清理临时文件与 repo-owned node 残留。

## Ownership Boundaries

- root lane: 决定删除清单、改 README / proof / status spine、执行验证
- retained surfaces: 任何仍被脚本、配置、测试或 reference 直接消费的 plan/requirement 文件不做破坏性改写

## Verification Commands

```bash
git diff --check
rg -n "docs/audits/" docs references scripts config tests README.md CONTRIBUTING.md
rg -n "docs/archive/status/" docs references scripts config tests README.md CONTRIBUTING.md
```

## Rollback Plan

- 若发现 live consumer 仍指向被删路径，优先恢复该文件或改正消费者，不做半完成提交
- 若 README / proof 叙事与实际保留面不一致，先修正文档再宣称完成

## Phase Cleanup Contract

- 清理 `.pytest_cache/`
- 清理 `.tmp/` 下本轮临时产物
- 审计并结束 repo-owned zombie node 进程
