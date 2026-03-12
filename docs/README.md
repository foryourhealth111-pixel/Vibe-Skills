# VCO Docs

该目录承载 VCO 的治理正文、能力平面集成说明、运行时/打包规则、执行计划与 release 证据入口。

## Start Here

- [`manifesto.md`](manifesto.md)：VibeSkills 对外宣言与技术承诺；说明我们为什么做这件事、反对什么、建设什么。
- [`docs-information-architecture.md`](docs-information-architecture.md)：`docs/` 的正式信息架构、命名约定与导航规则。
- [`repo-cleanliness-governance.md`](repo-cleanliness-governance.md)：cleanup-first 基线，定义 local noise / governed workset / mirror pressure 的边界。
- [`output-artifact-boundary-governance.md`](output-artifact-boundary-governance.md)：`outputs/**` 的长期资产 / 运行产物分层规则。
- [`runtime-freshness-install-sop.md`](runtime-freshness-install-sop.md)：canonical -> installed runtime 的 freshness/install SOP。
- [`../references/index.md`](../references/index.md)：reference 资产导航入口。
- [`../scripts/README.md`](../scripts/README.md)：scripts 根入口；统一跳转到 governance / verify / common surfaces.
- [`../scripts/verify/README.md`](../scripts/verify/README.md)：gate 运行入口；[`../scripts/verify/gate-family-index.md`](../scripts/verify/gate-family-index.md) 提供 verify family 索引。
- [`../scripts/governance/README.md`](../scripts/governance/README.md)：governance operator surface（sync / rollout / release / audit）。
- [`../config/index.md`](../config/index.md)：machine-readable policy / routing / release / cleanliness 配置入口。
- [`plans/2026-03-08-repo-full-cleanup-master-plan.md`](plans/2026-03-08-repo-full-cleanup-master-plan.md)：repo cleanup umbrella plan；统一 Batch0-9 的收口顺序与 definition of done。
- [`external-tooling/README.md`](external-tooling/README.md)：MCP / skill / manual 边界与外部工具职责说明。
- [`../scripts/common/README.md`](../scripts/common/README.md)：shared helpers / wave runner / UTF-8 no BOM 写入约束。

## Governance Spine

- [`ecosystem-absorption-dedup-governance.md`](ecosystem-absorption-dedup-governance.md)：生态吸收、去冗余、owner 分层总纲。
- [`absorption-admission-matrix.md`](absorption-admission-matrix.md)：上游项目准入与吸收状态矩阵。
- [`promotion-board-governance.md`](promotion-board-governance.md) / [`promotion-board-v2-governance.md`](promotion-board-v2-governance.md)：promotion board、entry/exit evidence 规则。
- [`observability-consistency-governance.md`](observability-consistency-governance.md)：telemetry、一致性、rollback 与 promotion-aware observability。
- [`release-train-v2-governance.md`](release-train-v2-governance.md) / [`release-evidence-bundle-v3-governance.md`](release-evidence-bundle-v3-governance.md)：release 证据、cut、closure 合同。
- [`manual-apply-policy-governance.md`](manual-apply-policy-governance.md) / [`subagent-handoff-governance.md`](subagent-handoff-governance.md)：人工补丁与多 agent handoff 约束。

## Capability Planes

- **Memory / Prompt**：[`memory-governance-integration.md`](memory-governance-integration.md)、[`memory-runtime-v2-integration.md`](memory-runtime-v2-integration.md)、[`memory-runtime-v3-governance.md`](memory-runtime-v3-governance.md)、[`mem0-optin-backend-integration.md`](mem0-optin-backend-integration.md)、[`letta-policy-integration.md`](letta-policy-integration.md)、[`prompt-overlay-integration.md`](prompt-overlay-integration.md)、[`prompt-intelligence-governance.md`](prompt-intelligence-governance.md)、[`prompt-intelligence-productization.md`](prompt-intelligence-productization.md)。
- **Browser / Desktop / Conflict**：[`turix-cua-overlay.md`](turix-cua-overlay.md)、[`browserops-provider-integration.md`](browserops-provider-integration.md)、[`browserops-scorecard-governance.md`](browserops-scorecard-governance.md)、[`agent-s-shadow-integration.md`](agent-s-shadow-integration.md)、[`desktopops-replay-governance.md`](desktopops-replay-governance.md)、[`cross-plane-conflict-governance.md`](cross-plane-conflict-governance.md)、[`cross-plane-replay-governance.md`](cross-plane-replay-governance.md)、[`cross-plane-task-contract-governance.md`](cross-plane-task-contract-governance.md)。
- **Document / Connector / Upstream**：[`docling-document-plane-integration.md`](docling-document-plane-integration.md)、[`docling-contract-v2-governance.md`](docling-contract-v2-governance.md)、[`document-plane-benchmark-governance.md`](document-plane-benchmark-governance.md)、[`connector-admission-governance.md`](connector-admission-governance.md)、[`connector-scorecard-governance.md`](connector-scorecard-governance.md)、[`connector-action-ledger-governance.md`](connector-action-ledger-governance.md)、[`upstream-corpus-governance.md`](upstream-corpus-governance.md)、[`upstream-eval-pilot-scenarios.md`](upstream-eval-pilot-scenarios.md)。
- **Role / Capability Productization**：[`role-pack-governance.md`](role-pack-governance.md)、[`role-pack-v2-governance.md`](role-pack-v2-governance.md)、[`role-pack-distillation-governance.md`](role-pack-distillation-governance.md)、[`capability-dedup-graph-governance.md`](capability-dedup-graph-governance.md)、[`capability-lifecycle-governance.md`](capability-lifecycle-governance.md)、[`continuous-value-extraction-operations.md`](continuous-value-extraction-operations.md)。

## Runtime / Packaging / Freshness

- [`version-packaging-governance.md`](version-packaging-governance.md)：canonical version、mirror topology、packaging source-of-truth。
- [`frontmatter-bom-governance.md`](frontmatter-bom-governance.md)：byte-0 frontmatter / UTF-8 BOM stop-ship 治理。
- [`runtime-freshness-install-sop.md`](runtime-freshness-install-sop.md)：install 后 freshness gate、receipt 与 install SOP。
- [`repo-cleanliness-governance.md`](repo-cleanliness-governance.md) / [`output-artifact-boundary-governance.md`](output-artifact-boundary-governance.md)：cleanup-first 与 outputs boundary。
- [`rollback-drill-governance.md`](rollback-drill-governance.md) / [`gate-reliability-governance.md`](gate-reliability-governance.md)：回滚演练、gate 可靠性与 stop-ship 约束。

## Plans / Releases / Status

- [`plans/README.md`](plans/README.md)：执行计划、triage、阶段状态文档入口；planning 与治理正文分层存放，避免混入 root docs。
- [`releases/README.md`](releases/README.md)：release notes、installed runtime 验证与 release closure 入口。
- 重点执行文档：
  - [`plans/2026-03-08-vco-wave121-140-operatorized-value-extraction-plan.md`](plans/2026-03-08-vco-wave121-140-operatorized-value-extraction-plan.md)
  - [`plans/2026-03-08-vco-wave101-120-value-extraction-plan.md`](plans/2026-03-08-vco-wave101-120-value-extraction-plan.md)
  - [`plans/2026-03-07-vco-wave40-63-execution-plan.md`](plans/2026-03-07-vco-wave40-63-execution-plan.md)
  - [`plans/2026-03-07-vco-wave64-82-execution-plan.md`](plans/2026-03-07-vco-wave64-82-execution-plan.md)
  - [`plans/2026-03-07-vco-wave83-100-execution-plan.md`](plans/2026-03-07-vco-wave83-100-execution-plan.md)
  - [`plans/2026-03-07-vco-wave83-100-execution-status.md`](plans/2026-03-07-vco-wave83-100-execution-status.md)
  - [`plans/2026-03-08-repo-cleanliness-batch2-4-triage.md`](plans/2026-03-08-repo-cleanliness-batch2-4-triage.md)

## Cleanup-First Rules

- 不通过 mass rename 制造新漂移；优先补索引、taxonomy、README 锚点。
- 新增 `docs/*.md` 必须同时进入本 README；若对应脚本 / reference 存在，也要补双向链接。
- `plans/` 只放执行与状态文档；`releases/` 只放 release evidence；root `docs/` 保持治理 / 集成正文。
- 镜像整理不在 `bundled/` 独立进行；必须走 canonical edit -> sync -> parity gates。
