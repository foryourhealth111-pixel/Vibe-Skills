# 2026-03-07 Repo Cleanliness First Plan

- Up: [../README.md](../README.md)
- Index: [README.md](README.md)

## Objective

先把仓库卫生收口到“本地噪声不再污染工作区、镜像漂移不被放大、后续 wave 能在清晰基线上继续推进”的状态，再进入下一轮吸收/融合执行。

## Audit Snapshot

基于 2026-03-07 的审计，当前 dirty state 需要拆成两类：

1. **必须立即收口的噪声层**
   - `.serena/`
   - `.tmp/`
   - 根目录 planning scratch（`task_plan.md` / `findings.md` / `progress.md`）
   - 未被引用的一次性 patch 残留
2. **不能粗暴删除的真实工作集层**
   - `config/`, `docs/`, `references/`, `scripts/`, `protocols/`
   - `bundled/skills/vibe/**` 及 nested bundled mirror

因此，当前阶段的目标不是“伪装成 zero-dirty”，而是先完成 **noise separation**。

## Phase Plan

### Phase A — Hygiene Baseline (now)
- 共享 `.gitignore` 收口 `.serena/` 与 `.tmp/`。
- 安装 `.git/info/exclude` 的 local scratch block。
- 删除未引用的一次性 patch 残留。
- 引入 repo cleanliness policy + gate + governance doc。
- 输出 cleanliness evidence。

### Phase B — Canonical Workset Triage (next)
- 将剩余 dirty 项按四类拆批：
  1. `config/*`
  2. `docs/* + references/*`
  3. `scripts/*`
  4. `bundled mirror parity backlog`
- 每批只处理一个主题，不把治理、功能、release 证据混在同一轮里。
- 对 `outputs/**` 中已被跟踪的少量历史资产，决定“迁移为 fixture”还是“停止继续版本化”。

### Phase C — Drift Closure (next)
- 继续执行 mirror topology / nested parity / runtime freshness 的组合治理。
- 把“工作集 backlog”与“运行态证据目录”彻底解耦。
- 收口 `outputs/verify`, `outputs/external-corpus`, `outputs/retro/compare` 中历史遗留的资产边界问题。

### Phase D — Resume Feature Waves (after cleanliness baseline)
- 只有在 local hygiene gate 稳定通过后，再继续新的生态吸收 wave。
- 后续 wave 默认采用：先 canonical 实现 -> 再 sync bundled -> 再跑 parity / runtime / cleanliness gates。

## Backlog After Cleanup Baseline

1. **Workset Batch 1**: `config/*` 与 shared governance JSON 收口。
2. **Workset Batch 2**: `docs/* + references/*` 的正式化、去重复、导航修正。
3. **Workset Batch 3**: `scripts/*` 的 verify/governance/runtime 工具链再整理。
4. **Workset Batch 4**: bundled / nested bundled backlog 的成批 parity 校准。
5. **Wave Resume**: 在清洁基线上恢复后续 value-extraction / absorption waves。

## Exit Criteria

本轮 cleanup-first 视为完成，需要同时满足：

- `vibe-repo-cleanliness-gate.ps1 -WriteArtifacts` 通过；
- `.serena/` / `.tmp/` / root planning scratch 不再出现在默认 `git status`；
- 未引用的 patch 残留已删除；
- 已形成正式治理说明与后续 triage 计划。

## Explicit Non-Goals

- 本轮不尝试把整个仓库直接压成 `git status == clean`；
- 本轮不对历史真实工作集做大规模回滚；
- 本轮不把真实 backlog 通过 ignore 规则“藏起来”。

## 2026-03-08 Batch 1 Progress

### Completed
- Local hygiene baseline 已建立：shared ignore / local exclude / repo cleanliness gate 已落地。
- `outputs/**` 的历史被跟踪资产已转为显式 policy 管理，而不是继续处于“被忽略但又被提交”的灰区。
- 新增 `config/outputs-boundary-policy.json`、`docs/governance/output-artifact-boundary-governance.md`、`scripts/verify/vibe-output-artifact-boundary-gate.ps1`。

### Batch 1 Exit Criteria
- `vibe-repo-cleanliness-gate.ps1` 通过；
- `vibe-output-artifact-boundary-gate.ps1` 通过；
- `outputs/**` 的历史被跟踪资产全部命中 allowlist；
- 新的 runtime output 不再可以静默进入版本控制。

### Next Focus
- Batch 2: `docs/* + references/*` 正式化、去重与导航清理。
- Batch 3: `scripts/*` 与 bundled/nested mirror backlog 的主题化整理。
