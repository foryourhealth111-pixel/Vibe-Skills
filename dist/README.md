# dist/ — Distribution Surface (Truth-First)

本目录是 **Batch D** 的分发面落地：用 *machine-readable* 的 manifest，把 “我们到底支持什么 / 不支持什么 / 需要宿主自己 provision 什么 / 哪些情况下会降级” 说清楚。

这些 `dist/*` manifest 现在是 **生成产物**，唯一人工维护源收口在 `config/distribution-manifest-sources.json`，由 `tools/build/sync_dist_release_manifests.py` 统一物化。

它的定位是 **分发描述与契约**，而不是新的官方运行时，也不是对 `install.*` / `check.*` 主链的替代。

补充边界：`dist/*` 这些 checked-in manifest 是 **public release manifests**，用于说明对外发布 lane 的能力、边界与不承诺项。它们**不**承载内部运行时 payload 角色投影。内部的运行时 payload 证明链，仍由 `tools/build/assemble_distribution.py` 生成的 distribution manifest，以及 `tools/release/build_release_bundle.py` 生成的 release bundle 表达。

## dist 是什么

- **分发 lane 的声明层**：把 `core`、各宿主 adapter（Codex / Claude Code / Generic）拆成不同“消费层”的分发物（manifest），避免 README 叙事把所有宿主揉成一个“全都差不多”的假等价。
- **truth-first 的防过度承诺层**：显式写出：
  - host-managed surfaces（哪些事情是宿主侧负责的，不要伪装成 repo 已闭环）
  - degraded states（哪些情况下仍可用但必须降级、必须提示）
  - platform parity 规则（Windows / Linux / macOS 不被假设为等价）

## dist 不是什么

- 不是新的“官方满血运行时”。
- 不接管也不改写官方安装与体检主链：
  - `install.ps1` / `install.sh`
  - `check.ps1` / `check.sh`
  - 以及它们串联的 verify/doctor 主链
- 不承诺 “Claude Code / Generic Host” 已经具备与 Codex 相同的闭环能力。

## Manifest 入口

`dist/manifests/` 下的文件是当前的分发面声明：

- `dist/manifests/vibeskills-core.json`：跨宿主可消费的 core contract（**不**做运行时承诺）
- `dist/manifests/vibeskills-codex.json`：Codex lane（当前最强、但仍有 host-managed 与降级边界）
- `dist/manifests/vibeskills-claude-code.json`：Claude Code lane（`supported-with-constraints`，但不可宣传为 official runtime / full）
- `dist/manifests/vibeskills-opencode.json`：OpenCode lane（preview，仍保留 host-managed 边界与 proof blocker）
- `dist/manifests/vibeskills-generic.json`：Generic lane（advisory-only，只能消费契约）

每个 manifest 都必须与以下 truth sources **一致**：

- `docs/plans/2026-03-13-universal-vibeskills-execution-program.md`（Batch D / Task 7-8 的边界）
- `docs/universalization/host-capability-matrix.md`（宿主支持等级词汇表与晋升规则）
- `docs/universalization/platform-parity-contract.md`（平台不等价与降级规则）
- `README.md` 的安装叙事（尤其是 `manual_actions_pending` / `core_install_incomplete` 的现实口径）

## 安装路径文档（对应分发面）

为避免把“能跑”写成“等价满血”，安装路径按目标与治理强度拆分为三条：

- `docs/install/minimal-path.md`
- `docs/install/recommended-full-path.md`
- `docs/install/enterprise-governed-path.md`

注意：这些文档会明确区分 **repo-governed surfaces** 与 **host-managed surfaces**，并把 Windows/Linux 的降级状态写清楚（尤其是 Linux 无 `pwsh` 的情况）。
