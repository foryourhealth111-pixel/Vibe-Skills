# VCO Docs

`docs/` 是 VCO 的长期治理与说明文档入口。这里按“当前执行入口、运行态入口、开发者入口、长期治理正文”分层，避免把计划、证明和制度混在一起。

## Start Here

### Current Entry

- [`plans/README.md`](./plans/README.md)：当前 active plan、支撑材料、时间线索引与历史背景入口。
- [`plans/2026-03-11-vco-repo-simplification-remediation-plan.md`](./plans/2026-03-11-vco-repo-simplification-remediation-plan.md)：当前 repo 收敛主执行计划。
- [`plans/2026-03-13-distribution-governance-plan.md`](./plans/2026-03-13-distribution-governance-plan.md)：分发治理总计划。
- [`plans/2026-03-13-post-upstream-governance-repo-convergence-plan.md`](./plans/2026-03-13-post-upstream-governance-repo-convergence-plan.md)：上游治理后的仓库收敛计划。
- [`plans/2026-03-13-post-upstream-governance-developer-entry-plan.md`](./plans/2026-03-13-post-upstream-governance-developer-entry-plan.md)：上游治理后的开发者入口计划。

### Runtime Entry

- [`install/one-click-install-release-copy.md`](./install/one-click-install-release-copy.md)：面向普通用户的一键安装发布文案与 AI 助手复制提示词
- [`install/one-click-install-release-copy.en.md`](./install/one-click-install-release-copy.en.md)：ordinary-user public release copy and copy-paste onboarding prompt

- [`status/README.md`](./status/README.md)：当前运行态、proof 入口与阶段回执总索引。
- [`status/current-state.md`](./status/current-state.md)：当前 closure batch 的 runtime summary。
- [`status/non-regression-proof-bundle.md`](./status/non-regression-proof-bundle.md)：minimum closure proof contract。
- [`releases/README.md`](./releases/README.md)：受治理的 release surface 与历史 release packetization。
- [`cold-start-install-paths.md`](./cold-start-install-paths.md)：新人冷启动安装路径，区分最小可用、推荐满血与企业治理三条入口。
- [`one-shot-setup.md`](./one-shot-setup.md)：one-shot bootstrap、readiness states 与 deep doctor 口径。

### Developer Entry

- [`../CONTRIBUTING.md`](../CONTRIBUTING.md)：开发者总入口、禁止随意开发区域与 proof 预期。
- [`developer-change-governance.md`](./developer-change-governance.md)：开发者变更治理规则。
- [`distribution-governance.md`](./distribution-governance.md)：canonical truth surface 与 stop rules。
- [`upstream-distribution-governance.md`](./upstream-distribution-governance.md)：upstream truth、披露和本地保留规则。
- [`origin-provenance-policy.md`](./origin-provenance-policy.md)：repo-local retained upstream assets 的溯源策略。
- [`../references/contributor-zone-decision-table.md`](../references/contributor-zone-decision-table.md)：可改区 / 受保护区判定表。
- [`../references/change-proof-matrix.md`](../references/change-proof-matrix.md)：变更类型与验证负担矩阵。
- [`../references/developer-entry-contract.md`](../references/developer-entry-contract.md)：开发者入口契约。

### Background / Governance Entry

- [`docs-information-architecture.md`](./docs-information-architecture.md)：`docs/` 目录语义、索引规则与维护约束。
- [`architecture.md`](./architecture.md)：VCO 总体结构、边界与主执行面。
- [`repo-cleanliness-governance.md`](./repo-cleanliness-governance.md)：canonical / mirror / runtime / archive cleanliness contract。
- [`version-packaging-governance.md`](./version-packaging-governance.md)：canonical / bundled / nested / installed runtime packaging topology。
- [`runtime-freshness-install-sop.md`](./runtime-freshness-install-sop.md)：install -> freshness -> coherence operator SOP。
- [`output-artifact-boundary-governance.md`](./output-artifact-boundary-governance.md)：`outputs/**` 与 `references/fixtures/**` 的长期边界。
- [`observability-consistency-governance.md`](./observability-consistency-governance.md)：可观测性与一致性治理。
- [`external-tooling/README.md`](./external-tooling/README.md)：外部 tooling / provider / MCP 边界说明。

## Cross-Layer Handoff

- [`../config/index.md`](../config/index.md)：machine-readable policy、routing、packaging 与 cleanliness 配置入口。
- [`../scripts/README.md`](../scripts/README.md)：governance、verify、router、overlay 与 common script entrypoints。
- [`../references/index.md`](../references/index.md)：contracts、matrices、ledgers、fixtures 与 overlays 导航入口。

## Status Evidence Added In This Phase

- [`status/distribution-governance-baseline-2026-03-13.md`](./status/distribution-governance-baseline-2026-03-13.md)
- [`status/distribution-governance-closure-report-2026-03-13.md`](./status/distribution-governance-closure-report-2026-03-13.md)
- [`status/repo-convergence-baseline-2026-03-13.md`](./status/repo-convergence-baseline-2026-03-13.md)
- [`status/repo-convergence-closure-report-2026-03-13.md`](./status/repo-convergence-closure-report-2026-03-13.md)
- [`status/developer-entry-baseline-2026-03-13.md`](./status/developer-entry-baseline-2026-03-13.md)
- [`status/developer-entry-canary-report-2026-03-13.md`](./status/developer-entry-canary-report-2026-03-13.md)
- [`status/developer-entry-closure-report-2026-03-13.md`](./status/developer-entry-closure-report-2026-03-13.md)

## Rules

- root `docs/*.md` 只放长期治理正文、集成说明和稳定 operator SOP，不把 dated plan 或 batch report 升格成 canonical contract。
- `docs/plans/` 负责当前执行入口与时间绑定计划；`docs/status/` 负责当前运行态与 proof；`docs/releases/` 负责 release surface 与 release history。
- `status/current-state.md` 只做 artifact-backed 状态摘要；truth source 在 `outputs/verify/**` 与运行态回执中，而不是这份文档本身。
- 新增 root 级治理正文时，必须更新本索引；新增时间绑定材料时，更新对应子目录的 `README.md` 即可。
