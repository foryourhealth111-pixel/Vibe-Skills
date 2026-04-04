# Docs Information Architecture

## Why This Exists

`docs/` 已经从少量治理说明扩展为 VCO 的正式知识平面：既包含长期治理合同，也包含当前状态、执行计划、release 说明与专题集成文档。

cleanup-first 的目标不是一次性大搬家，而是在不引入额外漂移的前提下，先稳定目录语义与导航入口。

## Directory Contract

| Path | Role | What Belongs Here |
| --- | --- | --- |
| `docs/*.md` | 稳定入口 / 顶层治理正文 | 面向 docs landing 的少量长期入口、总纲和 high-signal governance 文档 |
| `docs/governance/*.md` | 专题治理 | scorecard、boundedness、proof、rollout、evaluation 等治理专题 |
| `docs/design/*.md` | 设计说明 / playbook | 结构设计、建模、reusable engineering playbook |
| `docs/status/*.md` | 当前运行态 | live status、阻塞项、operator 回执、短期 supporting baseline |
| `docs/plans/*.md` | 时间绑定执行材料 | active remediation plan、triage、wave horizon、closure report、阶段性设计稿 |
| `docs/releases/*.md` | Release evidence | release notes、cut 记录、installed runtime 检查说明 |
| `docs/external-tooling/*` | 外部边界说明 | MCP / skill / provider / manual 等职责边界说明 |
| `docs/archive/root-docs/*` | 历史专题 | 已退出 root 导航的 roadmap、matrix、playbook 和历史专题 |

## Document Type Taxonomy

| Pattern | Meaning | Example |
| --- | --- | --- |
| `*-governance.md` | 稳定治理合同、stop rules、entry/exit criteria | `repo-cleanliness-governance.md` |
| `*-integration.md` | 某能力 / 平面 / upstream 资源与 VCO 的集成设计 | `browserops-provider-integration.md` |
| `*-productization.md` | 从试点走向长期能力面的收口设计 | `prompt-intelligence-productization.md` |
| `design/*.md` / `architecture.md` | 结构设计、建模与分析 | `design/deep-discovery-mode-design.md` |
| `status/*.md` | 当前运行态与近期回执 | `status/current-state.md` |
| `plans/*.md` | 时间绑定的执行文档 | `plans/2026-03-08-repo-cleanliness-batch2-4-triage.md` |
| `releases/*.md` | release cut / note / install evidence | `releases/v2.3.31.md` |

## Navigation Rules

1. `docs/README.md` 是 `docs/` 的稳定 landing page，负责 stable spine、current ops 与 cross-layer index 的分层导航。
2. `docs/status/README.md`、`docs/plans/README.md`、`docs/releases/README.md` 分别承担各自目录的详细索引；不要把所有时间绑定材料重新铺回 root README。
3. root `docs/*.md` 的 canonical contract 必须尽量稳定；specialized governance、design、external-tooling leaf pages 和历史 reports 不应继续平铺在根层。
4. 若某文档存在对应 gate / config / reference，至少补一条反向锚点：
   - doc -> script/config/reference
   - README / index -> doc
5. 新增 root 级治理正文时必须更新 `docs/README.md`；新增时间绑定材料时，更新相应子目录 README 即可，不要求把所有 leaf 文档都塞回 root README。

## Cleanup-First Maintenance Rules

- 先补 README / taxonomy / index，再考虑 rename。
- 根层一旦出现 family-overview，可把弱引用 leaf doc 下沉到 `governance/`、`design/`、`external-tooling/` 或 `archive/root-docs/`。
- 同义文档允许暂时共存，但必须解释“谁是稳定入口、谁是运行态材料、谁是历史收据”。
- 阶段性报告不升级为治理总纲，除非明确被新的 governance 文档吸收。
- `current-state.md`、proof bundle 与 gate receipts 必须保持 artifact-backed，不再靠手工复制快照维持一致性。

## Cross-Layer Linkage

`docs/` 不是孤立层，需与以下层面保持可追踪关系：

- `references/`: contracts、matrix、registry、ledger 资产；
- `scripts/verify/`: 对治理合同的可执行 gate；
- `scripts/governance/`: sync / release / rollout / policy operator surface；
- `scripts/common/`: 共享 execution-context、wave runner、governance helper 原语；
- `config/`: machine-readable policy / planning board / rollout switch；
- `bundled/`: 仅通过 canonical sync 继承，不在 mirror 侧单独组织。

## Current Cleanup Focus

当前 cleanup-first 批次优先稳定五条主线：

1. `docs/README.md`: 把 stable spine 与 current ops 分层；
2. `docs/status/README.md` + `status/current-state.md`: 把 live 状态改成 artifact-backed；
3. `docs/plans/README.md`: 压缩 current 面，减少时间线噪音；
4. `docs/releases/README.md`: 用 gate family 替代大段 stop-ship 平铺；
5. `references/index.md`: 让 references 回到 contract-first 导航。
