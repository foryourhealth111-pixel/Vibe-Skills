# Governed Requirements

This directory stores the frozen requirement document for each governed `vibe` run.

Rules:

- one requirement document per governed run
- execution plans must trace back to the requirement document, not raw chat history
- benchmark mode must record inferred assumptions explicitly
- execution should not widen scope without updating the frozen requirement

Filename contract:

- `YYYY-MM-DD-<topic>.md`

Primary policy:

- `config/requirement-doc-policy.json`

## Current Entry

- [`2026-04-04-comprehensive-repo-slimming-refresh.md`](./2026-04-04-comprehensive-repo-slimming-refresh.md): 基于当前最新仓库体量与 live/archive 结构，对文档、proof bundles、fixtures、辅助脚本与 bundled payload 做一次更强的精简规划刷新；明确哪些可以先归档、哪些必须先做 consumer mapping、哪些暂时受保护。
- [`2026-04-04-strong-repo-slimming-program.md`](./2026-04-04-strong-repo-slimming-program.md): 冻结“强精简方案”需求；聚焦在保持 install、runtime、release、verify 行为不退化的前提下，对历史文档、参考资产、脚本与 payload 进行分层瘦身、归档与保留策略设计。
- [`2026-04-04-install-docs-registry-alignment.md`](./2026-04-04-install-docs-registry-alignment.md): 冻结安装入口文档与公开提示词对齐需求；聚焦把 README、安装索引、one-shot、cold-start 与 prompt surfaces 收口到 adapter registry 的真实宿主模式。
- [`2026-04-04-remaining-architecture-closure.md`](./2026-04-04-remaining-architecture-closure.md): 当前剩余架构收口 root requirement；约束 owner-consumer 对齐、状态脊柱一致性和 release/runtime truth。
- [`2026-04-04-final-architecture-consistency-proof.md`](./2026-04-04-final-architecture-consistency-proof.md): 当前 final proof-wave requirement；定义 owner-consumer sign-off、status wording 对齐和 closure-language honesty 的最后收口范围。

## Still-Live Baseline Families

- hierarchy / governance baseline:
  - [`2026-03-28-root-child-vibe-hierarchy-governance.md`](./2026-03-28-root-child-vibe-hierarchy-governance.md)
  - [`2026-03-27-ai-governance-consolidation.md`](./2026-03-27-ai-governance-consolidation.md)
- runtime contract baseline:
  - [`2026-03-30-runtime-contract-baseline-docs-and-goldens.md`](./2026-03-30-runtime-contract-baseline-docs-and-goldens.md)
  - [`2026-03-30-runtime-contract-host-adapter-projection.md`](./2026-03-30-runtime-contract-host-adapter-projection.md)
  - [`2026-03-30-runtime-contract-hierarchy-projection.md`](./2026-03-30-runtime-contract-hierarchy-projection.md)
  - [`2026-03-30-runtime-contract-authority-projection.md`](./2026-03-30-runtime-contract-authority-projection.md)
  - [`2026-03-30-runtime-summary-projection.md`](./2026-03-30-runtime-summary-projection.md)
- release / migration baseline:
  - [`2026-03-30-release-operator-closure-implementation.md`](./2026-03-30-release-operator-closure-implementation.md)
  - [`2026-03-30-outputs-boundary-routing-stability-migration.md`](./2026-03-30-outputs-boundary-routing-stability-migration.md)
  - [`2026-03-30-non-regression-technical-debt-remediation.md`](./2026-03-30-non-regression-technical-debt-remediation.md)
  - [`2026-03-30-project-technical-debt-review.md`](./2026-03-30-project-technical-debt-review.md)

## Historical Archive

- 已关闭、已发布或零消费者的 requirement packets 已迁入 [`../archive/requirements/README.md`](../archive/requirements/README.md)。
- 其余 dated requirement 若仍留在 live 目录，表示它们暂时仍承担 baseline、governance 或 traceability 角色，而不是因为首页需要继续展开长列表。

## Reading Boundary

- 当前 governed run 先看本节 `Current Entry`。
- 需要底层 contract 或治理基线时，再看 `Still-Live Baseline Families`。
- 历史需求包默认从 archive 进入。
