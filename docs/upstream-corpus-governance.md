# Upstream Corpus Governance

## Scope

Wave34 把 `third_party/vco-ecosystem-mirror` 的 15 个镜像来源纳入 **upstream corpus governance**。Wave121 在不改变单控制面的前提下，把 `mem0`、`letta`、`browser-use`、`agent-s` 也正式纳入同一条 canonical source registry，因此当前登记总数提升为 **19**。

这层治理只回答五个问题：

- 哪些上游项目被正式登记；
- 它们当前处在什么 `lane` / `status`；
- 谁负责下一步制度化动作；
- 哪个镜像根可作为 freshness gate 的 authoritative baseline；
- board / manifest / ledger / matrix 使用什么 **canonical slug**，以及哪些别名只允许出现在 intake 层。

## Canonical Assets

- `config/upstream-corpus-manifest.json`：19 项上游来源的 canonical 登记册；
- `config/upstream-source-aliases.json`：source alias -> canonical slug 的唯一登记表；
- `docs/upstream-corpus-governance.md`：字段与流程约束；
- `docs/governance/upstream-source-alias-governance.md`：别名治理与 intake 规范；
- `references/upstream-value-ledger.md`：逐项价值与 next action 账本；
- `references/upstream-reaudit-matrix-v2.md`：remaining value / ceiling / no-go 矩阵；
- `scripts/governance/audit-upstream.ps1`：辅助审计与摘要导出，只提供证据，不授予自动升级权；
- `scripts/verify/vibe-upstream-corpus-manifest-gate.ps1`：结构 / 字段 / alias / canonical slug gate；
- `scripts/verify/vibe-upstream-mirror-freshness-gate.ps1`：镜像完整度与 HEAD 对齐 gate，仅作为辅助证据。

## Manifest Structure

顶层字段最少包括：

| Field | Meaning |
|---|---|
| `version` / `updated` | manifest 版本与更新时间 |
| `governance_plane` | 固定为 `upstream_corpus` |
| `summary` | 19 项资源的 lane / status / owner 汇总 |
| `schema` | required fields 与 allowed vocab |
| `alias_config` | source alias registry 的 canonical 路径 |
| `freshness_policy` | freshness pass rule 与 live-root 特殊说明 |
| `mirror_roots` | 可验证的镜像根列表 |
| `entries` | 每个上游项目一条记录 |

每个 entry 都必须包含：

| Field | Meaning |
|---|---|
| `slug` | canonical lower-kebab-case source slug |
| `repo_url` | authoritative upstream repo |
| `default_branch` / `license` | 审计时保留的基础元数据 |
| `lane` | 进入哪条制度化吸收通道 |
| `status` | 当前治理成熟度 |
| `owner` | canonical owner / governance owner |
| `integration_role` | 该项目对 VCO 的价值定位 |
| `next_action` | 当前最重要的收口动作 |
| `observed_head_sha` | 审计时锁定的 upstream HEAD |
| `canonical_assets` | 当前已经绑定的 canonical asset 落点 |

## Canonical Slug Rule

- board / manifest / ledger / matrix 一律使用 **canonical slug**；
- GitHub 仓库名、目录名大小写、历史计划表中的展示名都只能通过 `config/upstream-source-aliases.json` 映射到 canonical slug；
- `Prompt-Engineering-Guide`、`Letta`、`Agent-S` 这类展示名不得再直接写入 board / matrix / ledger；
- alias 只能服务 intake / import / 对账，不能制造第二套命名真相。

## Lane Vocabulary

| Lane | Meaning |
|---|---|
| `connector_admission` | 连接器目录、provider candidate、allowlist / denylist 治理 |
| `document_plane_contract` | 文档解析 contract / provider policy |
| `prompt_contract_source` | prompt intelligence / review heuristics 的吸收源 |
| `role_pack_source` | 角色包、subagent 组织模式参考源 |
| `skill_catalog_source` | skill catalog / skill harvest 参考源 |
| `discovery_eval_corpus` | discovery / eval / workflow 观察样本层 |
| `memory_policy_source` | memory preference / policy / retention contract 吸收源 |
| `browserops_provider_source` | BrowserOps provider candidate / open-world eval 吸收源 |
| `desktopops_shadow_source` | DesktopOps shadow / replay / failure taxonomy 吸收源 |

## Status Vocabulary

| Status | Meaning |
|---|---|
| `tracked_corpus` | 已登记、已镜像，但仍以参考素材为主 |
| `catalog_governed` | 目录类来源已进入明确 admission policy |
| `shadow_governed` | provider / backend / shadow candidate 已被制度化，但未升格为默认执行面 |
| `partial_absorption` | 已有部分 canonical 吸收，但仍需继续收口 |
| `canonical_contract` | 已经形成正式 contract / policy / gate |

## Freshness Policy

`upstream_corpus` 的 freshness 与 canonical packaging parity 分离：

- freshness 只覆盖 `freshness_policy.scope_slugs` 中声明的 **15 个 mirror-managed sources**；
- `agent-s`、`browser-use`、`letta`、`mem0` 继续保留在 manifest，但属于 shadow / policy source，不要求存在于 mirror root；
- `workspace_live`（`third_party/vco-ecosystem-mirror`）是当前唯一 authoritative freshness baseline；
- gate 的 pass rule 是 `at_least_one_required_root_with_scope_coverage_and_matching_heads`；
- 如果 required root 缺项、不是 git repo、无法解析 HEAD、或与 manifest 的 `observed_head_sha` 漂移，freshness gate 必须 fail。
- 如果当前环境没有 materialized required root，freshness gate 只保留 advisory 记录，不应单独阻断 release cut。

## Audit Workflow

建议顺序：

1. 更新 `config/upstream-source-aliases.json` 与 `config/upstream-corpus-manifest.json`；
2. 运行 `pwsh -File .\scripts\governance\audit-upstream.ps1 -WriteJson`，生成辅助审计证据；
3. 运行 `pwsh -File .\scripts\verify\vibe-upstream-corpus-manifest-gate.ps1 -WriteArtifacts`；
4. 运行 `pwsh -File .\scripts\verify\vibe-upstream-mirror-freshness-gate.ps1 -WriteArtifacts`；
5. 先进行 manual upstream-by-upstream intake 判断；只有判断完成后，才更新 `references/upstream-value-ledger.md` 与 `references/upstream-reaudit-matrix-v2.md`。

## Operator Rules

- upstream corpus 只记录“上游价值与治理位置”，不授予第二控制面；
- 任何 entry 从 `tracked_corpus` 升格前，必须先有 docs + config + gate；
- `mem0`、`browser-use`、`agent-s` 即使被登记，也仍然只能停留在 governed optional / shadow posture；
- `letta` 与 `prompt-engineering-guide` 即使产出高价值资产，也不能改写 VCO router / execution ownership；
- mirror freshness 允许有 working root 与 backup root，但必须明确哪个 root 对 gate authoritative；
- canonical repo 之外的 runtime-only 资产，不得再作为唯一事实来源。
