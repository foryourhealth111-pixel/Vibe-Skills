# VCO Status

`docs/status/` 只放当前状态入口、proof contract 和必要 guardrails，不承担完整历史归档。

## Start Here

- live summary: [`current-state.md`](current-state.md)
- current closure receipt: [`closure-audit.md`](closure-audit.md)
- architecture sign-off proof: [`../proof/2026-04-04-owner-consumer-consistency-proof.md`](../proof/2026-04-04-owner-consumer-consistency-proof.md)
- batch order / next hop: [`roadmap.md`](roadmap.md)
- minimum proof contract: [`non-regression-proof-bundle.md`](non-regression-proof-bundle.md)
- historical phase-end dry run: [`operator-dry-run.md`](operator-dry-run.md)
- protected surfaces: [`protected-capability-baseline.md`](protected-capability-baseline.md)
- transitional blockers: [`path-dependency-census.md`](path-dependency-census.md)
- slimming inventory freeze: [`repo-slimming-path-role-matrix.md`](./repo-slimming-path-role-matrix.md)
- slimming refresh inventory: [`repo-slimming-refresh-path-role-matrix.md`](./repo-slimming-refresh-path-role-matrix.md)
- historical dated material: [`history-index.md`](./history-index.md)

## Cross-Layer Handoff

- plans and historical batch context: [`../plans/README.md`](../plans/README.md)
- operator scripts: [`../../scripts/README.md`](../../scripts/README.md)
- verify run order: [`../../scripts/verify/gate-family-index.md`](../../scripts/verify/gate-family-index.md)
- long-term promotion contracts: [`../universalization/platform-promotion-criteria.md`](../universalization/platform-promotion-criteria.md)

## Reading Boundary

- [`current-state.md`](current-state.md)、[`closure-audit.md`](closure-audit.md)、[`../proof/2026-04-04-owner-consumer-consistency-proof.md`](../proof/2026-04-04-owner-consumer-consistency-proof.md) 是当前优先阅读面。
- [`operator-dry-run.md`](operator-dry-run.md) 是 2026-03-12 的历史 dry-run 回执，只保留审计价值，不再承担当前批次回执角色。
- 其余带日期的 baseline、ledger、closure 文件统一经 [`history-index.md`](./history-index.md) 进入，并默认按 archival-by-default 读取。
- 这些 dated 文件保留是为了 auditability，不代表它们仍然是 active state。

## Rules

- [`current-state.md`](current-state.md) 是唯一 live summary；数值和 PASS/FAIL 必须回指 `outputs/verify/**`、回归结果或当前 closure receipt。
- [`closure-audit.md`](closure-audit.md) 是当前批次回执；[`operator-dry-run.md`](operator-dry-run.md) 只是历史证据，不维护平行摘要。
- 结构性 sign-off 证明统一收束到 [`../proof/2026-04-04-owner-consumer-consistency-proof.md`](../proof/2026-04-04-owner-consumer-consistency-proof.md)。
- dated baselines 只保留 guardrail 或 blocker 作用；历史批次正文放回 `docs/plans/`。
