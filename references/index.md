# VCO References Index

`references/` 是长期 contracts、registries、ledgers 和 playbooks 的入口，不是 operator console。

## Start Here

### Contracts

- [unified-task-contract.md](./unified-task-contract.md)
- [tool-rule-contract.md](./tool-rule-contract.md)
- [mirror-topology.md](./mirror-topology.md)
- [release-evidence-bundle-contract.md](./release-evidence-bundle-contract.md)
- [runtime-contract-field-contract.md](./runtime-contract-field-contract.md)
- [reference-asset-taxonomy.md](./reference-asset-taxonomy.md)

### Registries / Catalogs

- [tool-registry.md](./tool-registry.md)
- [capability-catalog.md](./capability-catalog.md)
- [role-pack-catalog-v2.md](./role-pack-catalog-v2.md)
- [connector-capability-matrix.md](./connector-capability-matrix.md)

### Evidence / Ledgers

- [release-ledger.jsonl](./release-ledger.jsonl)
- [cross-plane-replay-ledger.md](./cross-plane-replay-ledger.md)
- [connector-action-ledger.md](./connector-action-ledger.md)
- [upstream-value-ledger.md](./upstream-value-ledger.md)
- [changelog.md](./changelog.md)
- [proof-bundles/README.md](./proof-bundles/README.md)
- [archive/README.md](./archive/README.md)

### Playbooks / Fixtures

- [memory-eval-scenarios.md](./memory-eval-scenarios.md)
- [prompt-eval-scenarios.md](./prompt-eval-scenarios.md)
- [document-golden-corpus.md](./document-golden-corpus.md)
- [fixtures/README.md](./fixtures/README.md)

## Adjacent Surfaces

这些入口保持可达，但不属于 `references/` spine：

- [`../docs/status/current-state.md`](../docs/status/current-state.md)
- [`../docs/status/non-regression-proof-bundle.md`](../docs/status/non-regression-proof-bundle.md)
- [`../scripts/verify/gate-family-index.md`](../scripts/verify/gate-family-index.md)
- [`../docs/plans/README.md`](../docs/plans/README.md)
- [`../docs/requirements/README.md`](../docs/requirements/README.md)

## Reading Order

1. 先看 contracts。
2. 再看 registries / catalogs。
3. 需要长期证据时进入 ledgers。
4. 需要场景化参考时再读 playbooks / fixtures / overlays。

## Rules

- 新增长期 reference 资产必须更新本页。
- time-bound execution 正文不进 `references/`；若某批次材料不再承担契约作用，应优先退出 GitHub 可见 `docs/` 面，而不是长期堆在 `references/`。
- reference 资产新增后至少补一条 docs 或 gate 锚点。
- 稳定路径如果因为历史长尾而需要瘦身，应优先拆成 current + archive volume，而不是让 stable path 消失。
