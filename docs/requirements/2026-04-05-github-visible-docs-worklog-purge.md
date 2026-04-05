# 2026-04-05 GitHub Visible Docs Worklog Purge

## Summary

清理 GitHub 可见 `docs/` 中带有明显个人执行痕迹、阶段日志属性、零消费者或纯互引属性的文档叶子，同时保留仍被脚本、配置、测试或公开运行契约直接消费的最小文档面。

## Goal

让 `docs/` 更像公开治理与运行说明面，而不是长期累积的个人工作日志面。

## Deliverable

- 精简后的 `docs/plans/`、`docs/requirements/`、`docs/status/`、`docs/archive/status/`、`docs/audits/`
- 修正后的 README / index / proof / contributor 导航
- 保留功能不退化所需的契约性文档叶子

## Constraints

- 不删除仍被脚本、配置、测试或稳定 reference 直接消费的文件，除非同步修复消费者
- 不破坏 `docs/status/current-state.md`、`docs/status/closure-audit.md`、`docs/status/non-regression-proof-bundle.md` 这组 live truth spine
- 不回滚用户已有未提交改动

## Acceptance Criteria

- `docs/audits/` 不再保留工作日志型叶子
- `docs/archive/status/` 不再保留整批 dated 叶子
- `docs/status/` 中零消费者或纯工作日志型 dated 页面被删除，只保留当前入口和少量 verify-retained 历史契约页
- `docs/plans/` 与 `docs/requirements/` 删除零消费者/纯互引叶子，仅保留当前治理入口与仍有活跃消费者的契约性材料
- `docs/README.md`、`docs/status/README.md`、`references/index.md`、`CONTRIBUTING.md` 等入口不再把个人工作日志当作主导航面
- `git diff --check` 通过

## Primary Objective

移除 GitHub 可见 docs 工作日志噪音，同时保住真实仍在运行中的文档契约。

## Non-Objective Proxy Signals

- 不是单纯追求删除文件数量
- 不是把所有历史文件机械地挪去 archive 继续暴露
- 不是为了“目录更空”而破坏 verify 或文档契约

## Validation Material Role

验证材料只用于证明公开 docs surface 已收缩且引用仍然成立，不用于重新制造新的日志堆积。

## Anti-Proxy-Goal-Drift Tier

Tight

## Intended Scope

`docs/**`、少量 `references/**` / `CONTRIBUTING.md` 的导航修补，以及必要的目录清理。

## Abstraction Layer Target

Public docs surface, documentation navigation, and repo-governance traceability.

## Completion State

当 GitHub 可见 `docs/` 不再公开堆放大批个人执行日志，同时保留的文档仍满足当前 verify / proof / contributor contract，即可视为完成。

## Generalization Evidence Bundle

- exact-path 引用检查
- `git diff --check`
- 必要的 targeted verification

## Non-Goals

- 不改写业务代码或运行时实现
- 不清理 `references/archive/**` 的全部历史叙事
- 不重构所有仍被消费的旧计划文件语义

## Autonomy Mode

interactive_governed

## Assumptions

- 用户优先关注 GitHub 可见 `docs/` 面的整洁度，而不是保留所有历史执行叙事
- 少量被脚本或测试消费的旧计划/需求文件可以暂时继续保留

## Evidence Inputs

- `docs/README.md`
- `docs/plans/README.md`
- `docs/requirements/README.md`
- `docs/status/README.md`
- `docs/status/history-index.md`
- `docs/status/path-dependency-census.md`
- `docs/proof/2026-04-04-owner-consumer-consistency-proof.md`
- `CONTRIBUTING.md`
