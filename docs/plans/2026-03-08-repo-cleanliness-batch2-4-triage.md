# 2026-03-08 Repo Cleanliness Batch2-4 Triage

- Up: [../README.md](../README.md)
- Index: [README.md](README.md)

## Scope

本 triage 文档的目标不是直接消灭全部 dirty backlog，而是把 cleanup-first 之后剩余的真实工作集，拆成可执行、可验证、低冲突的批次。

当前基线：
- local hygiene 已通过；
- output artifact boundary 已通过；
- remaining dirty 主要是 canonical workset backlog + bundled mirror backlog。

## Quantified Snapshot

基于 2026-03-08 审计：

- `docs/*`: 79
- `references/*`: 47
- `scripts/*`: 83
- `config/*`: 47
- `bundled/*`: 534

其中：

- `scripts/verify/*`: 74（scripts backlog 的绝对主体）
- `scripts/governance/*`: 6
- `scripts/common/*`: 2
- `docs/plans/*`: 8
- `docs/releases/*`: 3
- 其余 `docs/*.md` 多数为治理/集成/吸收说明文档

## 2026-03-08 Execution Update

已完成本轮 cleanup-first 的首批结构化收口：

- **Batch 2A / 2B**：新增 `docs/docs-information-architecture.md`，并重写 `docs/README.md`，把 governance spine、capability planes、runtime/freshness、plans/releases 分层显式化。
- **Batch 2C**：新增 `references/reference-asset-taxonomy.md`，并重写 `references/index.md`，把 reference 资产整理为 contract / registry / matrix / ledger / overlay 五层。
- **Batch 3A**：新增 `scripts/verify/gate-family-index.md`，并在 `scripts/verify/README.md` 增加 start-here / cleanup-first run order / family 视图。

本批次刻意**不做 mass rename**；目标是先让新旧资产有稳定导航和 family-level 入口，减少继续整理时的漂移风险。
## Batch 2 — Docs + References Formalization

### Objective

把 `docs/*` 与 `references/*` 从“持续堆积的治理文本集合”整理为：

1. 导航更清晰；
2. 重复更少；
3. 与脚本/配置有明确锚点；
4. 可以按主题提交，而不是全量混杂。

### Recommended Split

#### Batch 2A — Governance Docs Spine
- `docs/*-governance.md`
- `docs/*-integration.md`
- `docs/governance/output-artifact-boundary-governance.md`
- `docs/repo-cleanliness-governance.md`

目标：建立治理主干、去掉平行重复说明、补索引。

#### Batch 2B — Plans / Releases / Status
- `docs/plans/*`
- `docs/releases/*`
- `references/release-ledger.jsonl`
- `references/changelog.md`

目标：把计划、执行、release 证据链分开，避免 planning 文档混进治理正文。

#### Batch 2C — References Registry Layer
- `references/*matrix*.md`
- `references/*catalog*.md`
- `references/*scorecard*.md`
- `references/index.md`
- `references/tool-registry.md`
- `references/conflict-rules.md`

目标：把 reference 资产从“散列文本”整理成 registry / matrix / handbook 三层。

### Exit Criteria
- `docs/index` / `references/index` 层级关系清晰；
- 关键治理 doc 可被对应脚本/配置反向定位；
- 不再新增同义治理文档而没有导航入口。

## Batch 3 — Scripts Canonical Toolchain Triage

### Objective

把 `scripts/*` 拆成更稳定的执行面，减少 verify/governance 工具链继续无序扩张。

### Quantified Focus

- `scripts/verify/*`: 74
- `scripts/governance/*`: 6
- `scripts/common/*`: 2
- `scripts/overlay/*`: 1

### Recommended Split

#### Batch 3A — Verify Gate Families
按治理主题分组，而不是按文件名逐个处理：

- packaging / runtime / freshness / frontmatter
- cleanliness / outputs / mirror hygiene
- memory / prompt / adaptive routing
- browserops / connector / discovery / docling
- release / promotion / board / scorecard

#### Batch 3B — Governance Operators
- `scripts/governance/*`
- `scripts/common/vibe-governance-helpers.ps1`
- `scripts/common/vibe-wave-gate-runner.ps1`

目标：把“写入 / 同步 / release / local exclude / upstream audit”聚成稳定 operator surface。

#### Batch 3C — Research / Overlay Sidecars
- `scripts/research/*`
- `scripts/overlay/*`

目标：把 research helper 和 route-time overlay sidecar 明确为非核心执行面，避免混入基础治理路径。

### Exit Criteria
- verify family 有清晰主题分层；
- governance operator surface 稳定；
- research / overlay 不再和基础 runtime gate 混淆。

## Batch 4 — Bundled / Nested Mirror Backlog

### Objective

`bundled/*` 的 534 dirty 项不能被当成独立 backlog 逐个修；它们本质上是 canonical backlog 的镜像压力。

### Rule

- 不直接在 `bundled/skills/vibe/**` 或 nested bundled 中做独立整理；
- 永远使用 `canonical edit -> sync-bundled-vibe -> parity gates`；
- mirror backlog 只作为压力指标，不作为独立开发面。

### Exit Criteria
- 每次 canonical 批次收口后，mirror hygiene 与 nested parity 都可恢复通过；
- 不出现 mirror-only edits。

## Recommended Execution Order

1. Batch 2A / 2B 先做 docs 主干与 planning/release 分层。
2. Batch 2C 再做 references registry 收口。
3. Batch 3A 先整理 verify gate 家族。
4. Batch 3B 再稳定 governance operator surface。
5. Batch 3C 最后处理 research / overlay sidecars。
6. 每个 canonical 批次结束后都执行 Batch 4 的 sync + parity 验证。

## Stop Rules

以下情况出现时，不继续加速推进，先停下来收口：

- 新增 canonical 文档没有导航入口；
- 新增脚本没有 README / policy / gate 锚点；
- mirror hygiene 失败；
- 又出现新的 local noise / outputs boundary 漂移。
