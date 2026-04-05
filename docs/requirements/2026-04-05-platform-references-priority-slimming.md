# 2026-04-05 Platform And References Priority Slimming

## Summary

按用户指定优先级处理 `platform/` 与 `references/` 的四个子家族，在不破坏当前脚本、测试、replay、manifest 与治理契约的前提下，删除低信号空壳与历史残留，收缩仓库根部与 reference surface。

## Goal

用“先删空壳、再删零消费者 archive、最后审慎冻结 live contract families”的方式，完成一次高收益但低回归风险的精简。

## Deliverable

- 删除后的 `platform/` 空壳目录
- 精简后的 `references/archive/**`
- 审计结论明确后的 `references/proof-bundles/**`、`references/overlays/**`、`references/fixtures/**`
- 同步修正后的 README / archive navigation / plan references

## Constraints

- 不删除仍被 scripts、tests、replay、config 或 manifest 直接消费的 live proof bundle artifacts
- 不删除 `references/overlays/**` 下仍被 overlay config 直接指向的文档
- 不删除 `references/fixtures/**` 下仍承担 governed baseline、migration-map 或 boundary gate 角色的 fixture
- 不回滚用户未要求撤销的已有改动

## Acceptance Criteria

- `platform/` 若仅为空壳占位，则被安全移除
- `references/archive/**` 中零消费者、仅承担历史说明的 proof-bundle 长尾被删除
- `references/archive/changelog/pre-v2.3.53.md` 及其必要导航继续保留
- `references/proof-bundles/**` 只保留当前 tests / replay / verify / manifest contract 需要的 live bundle surface
- `references/overlays/**` 与 `references/fixtures/**` 若无安全删除空间，则明确标注为本波保留面，不做破坏性精简
- `git diff --check` 通过

## Primary Objective

在保证功能与治理契约不退化的前提下，实质性缩小根部低价值目录与历史 references 长尾。

## Non-Objective Proxy Signals

- 不是为了删除数量而删除 live contract 文件
- 不是把仍有消费者的 proof / overlay / fixture 误判为噪音
- 不是把 archive 说明面整体迁移成另一组新的冗余说明文件

## Validation Material Role

验证材料用于证明“保留面仍活着、删除面确实无消费者、导航已同步”，不用于制造新的工作日志。

## Anti-Proxy-Goal-Drift Tier

Tight

## Intended Scope

`platform/`、`references/archive/**`、`references/proof-bundles/**`、`references/overlays/**`、`references/fixtures/**`，以及必要的 README / index / governance navigation 修补。

## Abstraction Layer Target

Repository root surface, reference taxonomy, live proof contracts, and retained baseline fixtures.

## Completion State

当 `platform/` 空壳已清除、`references/archive/**` 长尾明显收缩、且 live proof / overlay / fixture contracts 仍可验证成立时，本波视为完成。

## Generalization Evidence Bundle

- exact-path consumer scan
- manifest contract scan
- `git diff --check`
- targeted tests around proof-bundles and fixtures boundaries

## Non-Goals

- 不重构 proof-bundle manifest schema
- 不重写 overlay 与 fixture 的上游治理模型
- 不对 `references/` 做整目录删除

## Autonomy Mode

interactive_governed

## Assumptions

- 用户更重视根目录与 reference surface 的可维护性，而不是保留所有历史说明性叶子
- `references/proof-bundles/**` 中的 manifest 及其声明的 run artifacts 属于高优先级保留面
- `references/overlays/**` 与 `references/fixtures/**` 当前更适合作为受保护面，而不是本波主删减对象

## Evidence Inputs

- `platform/.gitkeep`
- `references/archive/**`
- `references/proof-bundles/**`
- `references/overlays/**`
- `references/fixtures/**`
- `tests/integration/test_proof_bundle_manifest_contract.py`
- `tests/runtime_neutral/test_outputs_boundary_migration.py`
