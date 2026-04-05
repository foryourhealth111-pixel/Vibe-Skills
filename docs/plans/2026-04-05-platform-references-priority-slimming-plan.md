# 2026-04-05 Platform And References Priority Slimming Plan

## Execution Summary

按“冻结文档 -> 删除空壳 -> 清理 archive 长尾 -> 评估 live families -> 验证与阶段清理”的顺序，执行一次受治理的 references 精简波次。

## Frozen Inputs

- `docs/requirements/2026-04-05-platform-references-priority-slimming.md`
- current repo state on branch `chore/non-bundled-surface-slimming`

## Anti-Proxy-Goal-Drift Controls

### Primary Objective

删除低信号 root/reference 长尾，同时保住 proof / overlay / fixture 的真实活跃契约。

### Non-Objective Proxy Signals

- 不以“目录更空”代替“契约仍成立”
- 不把 manifest 引用的 run artifacts 当作普通说明文件删掉
- 不因为 archive 零消费者而误伤 live proof bundles

### Validation Material Role

验证只用于证明删减后契约仍可消费、导航未漂移、仓库未遗留本轮临时垃圾。

### Declared Tier

Tight

### Intended Scope

`platform/` 与 `references/` 的 archive / proof-bundles / overlays / fixtures 四家族。

### Abstraction Layer Target

Repository root surface and governed reference surfaces.

### Completion State Target

完成后，空壳目录消失，archive 长尾被收缩，live proof / overlay / fixture 面只保留必要契约。

### Generalization Evidence Plan

- exact-path consumer scans
- manifest-path contract checks
- `git diff --check`
- targeted proof-bundle + fixture boundary tests

## Internal Grade Decision

XL

## Wave Plan

1. 冻结本波 requirement / plan，记录删减优先级与保留边界。
2. 删除 `platform/` 空壳目录，并同步确认无实际消费者。
3. 精简 `references/archive/**`，优先删除 archive proof-bundle 长尾与零消费者 README，保留仍被 changelog 导航消费的历史 changelog volume。
4. 审视 `references/proof-bundles/**` 的 live contract；仅在不触发 manifest/test 回归时做保守收缩，否则保留现状并明确理由。
5. 对 `references/overlays/**` 与 `references/fixtures/**` 形成“本波保留”结论，不做会引发 contract regression 的删除。
6. 运行 targeted verification，清理 `.pytest_cache/`、`.tmp/` 与 repo-owned zombie node 残留。

## Ownership Boundaries

- root lane: requirement/plan freeze、删除清单决策、README 修补、验证与 cleanup
- child lanes: 消费者审计与家族级保留/删除建议，不创建新的 canonical requirement 或 plan

## Verification Commands

```bash
git diff --check
pytest tests/integration/test_proof_bundle_manifest_contract.py -q
pytest tests/runtime_neutral/test_outputs_boundary_migration.py -q
rg -n "references/archive/proof-bundles|references/archive/changelog/README.md|platform/" docs references scripts config tests README.md CONTRIBUTING.md .github .internal -g '!outputs/**'
```

## Rollback Plan

- 若删除后出现 manifest / test / replay 断链，先恢复被删文件或同步修正消费者，再继续收缩
- 若 archive navigation 指向失效，优先修正 README / index，不留下半断裂状态

## Phase Cleanup Contract

- 清理 `.pytest_cache/`
- 清理 `.tmp/` 下本轮临时产物
- 审计并结束 repo-owned zombie node 进程
- 确认仓库不残留仅供本轮分析使用的临时文件
