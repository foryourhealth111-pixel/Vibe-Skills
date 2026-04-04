# One-Shot Full Setup Closure Plan

> Goal: 判断 `vco-skills-codex` 是否已经达到“用户用一条命令即可把本仓库可分发的功能、依赖、MCP 物料、运行时配置尽可能一次性安装好”的状态；若未达到，则以不破坏现有 install/check/runtime contract 为前提，补齐 bootstrap、doctor、MCP 物化与入口文档，并用验证链证明没有功能退化。

## Baseline Conclusion

当前仓库已经具备：

- canonical -> bundled -> installed runtime 的强一致安装与 freshness/coherence gate
- `full` / `minimal` profile 安装面
- `settings.template.codex.json`、`plugins-manifest.codex.json`、`mcp/servers.template.json`、`mcp/profiles/*.json`
- `install.ps1` / `check.ps1`、可选 `-InstallExternal`

但当前仓库还 **不等于真正的一次性全量安装**，原因是：

1. 核心 Codex plugin 仍是 `manual-codex`，无法由 repo 脚本安全地完全自动安装。
2. MCP 目前是“模板随仓库分发”，不是“激活后的单一可消费 profile 文件 + readiness 报告”。
3. API key / provider secret 必须人工提供，不能被 repo 自动生成或静默持久化。
4. README / deployment 入口仍把用户引向不完整的一键路径，且 `check.ps1 -Deep` 文档与实际实现漂移。

因此，本计划把目标定义为：

- **自动闭环部分**：repo-owned runtime、vendored skills、可脚本安装的外部 CLI、MCP profile 物化、设置文件种子、深度 readiness 报告。
- **不可全自动部分**：平台插件 provisioning、用户 secret 输入、host 级 MCP 注册。
- **最终交付标准**：用户运行一个 bootstrap 命令后，能得到一个机器可读且人可读的 setup report，明确哪些能力已经 ready、哪些仍需人工一步完成，而不是靠猜。

## Hard Constraints

1. 不重写现有 router contract。
2. 不破坏 `install.*` / `check.*` 的现有可用路径，只做兼容增强。
3. 不把 secret 自动写入仓库，也不默认把空 placeholder 当作成功配置。
4. 不把 plugin lifecycle 假装成 repo 可控；对不可自动化部分必须显式暴露。
5. 所有新增 operator 必须有 machine-readable 输出，并接入现有 scripts/docs 导航。
6. 每个阶段结束后必须执行 phase-end cleanup，保持 `.tmp`、node audit、repo cleanliness 收口。

## Target State

完成后，一次性 setup 体验应具备以下性质：

1. 用户可以运行单一 bootstrap 命令完成“可自动化”的全部动作。
2. bootstrap 结束后会自动生成：
   - setup summary
   - MCP active profile 文件
   - plugin/manual follow-up checklist
   - 深度 doctor 报告
3. `check.ps1 -Deep` 成为正式支持的深度自检入口。
4. README / README.en / docs/deployment 只保留一条明确的一键路径，不再要求用户自己拼接 install + setup + verify。
5. 若存在人工未完成项，报告会给出分类：
   - `ready`
   - `ready_with_optional_gaps`
   - `manual_action_required`
   - `secret_required`
   - `platform_plugin_required`

## Execution Batches

### Batch 0: Formalize the Installability Boundary

Output:

- 本计划文档
- one-shot baseline conclusion 固化

Actions:

- 统一结论：当前状态是“核心安装一键 + 外部能力手工补齐”，不是“全量一键完成”
- 明确自动化边界、不可自动化边界、验收标准

### Batch 1: Bootstrap and Doctor Surface

Files:

- `scripts/bootstrap/one-shot-setup.ps1`
- `scripts/verify/vibe-bootstrap-doctor-gate.ps1`

Actions:

- 新增单一 bootstrap 入口
- 新增深度 doctor gate，输出 JSON + Markdown
- doctor 需要覆盖：
  - installed runtime freshness/coherence
  - settings/env readiness
  - plugin manifest readiness classification
  - external CLI readiness classification
  - selected MCP profile readiness classification

### Batch 2: MCP Profile Materialization

Files:

- `scripts/setup/materialize-codex-mcp-profile.ps1`

Actions:

- 从 `settings.json` 的 `vco.mcp_profile` 和 `mcp/profiles/*.json` 解析启用项
- 生成 `${TARGET_ROOT}/mcp/servers.active.json`
- 为每个启用 server 输出激活状态、依赖状态、下一步动作

### Batch 3: Deep Check Compatibility

Files:

- `check.ps1`
- `check.sh`

Actions:

- 正式支持 `-Deep` / `--deep`
- 让深度检查调用 bootstrap doctor
- 保持原有基础健康检查不退化

### Batch 4: Docs Convergence

Files:

- `README.md`
- `README.en.md`
- `docs/archive/root-docs/deployment.md`
- `scripts/README.md`
- `scripts/verify/README.md`
- `docs/one-shot-setup.md`

Actions:

- 收敛为单一路径：install / bootstrap / doctor / manual follow-up
- 修复 `check.ps1 -Deep` 文档漂移
- 明确“平台插件与 secret 不能被 repo 完全自动化”

### Batch 5: Verification and Phase Hygiene

Required checks:

- `git diff --check`
- `pwsh -File .\check.ps1 -Profile full -TargetRoot "$env:USERPROFILE\.codex"`
- `pwsh -File .\check.ps1 -Profile full -TargetRoot "$env:USERPROFILE\.codex" -Deep`
- `pwsh -File .\scripts\verify\vibe-offline-skills-gate.ps1`
- `pwsh -File .\scripts\verify\vibe-installed-runtime-freshness-gate.ps1 -TargetRoot "$env:USERPROFILE\.codex"`
- `pwsh -File .\scripts\verify\vibe-release-install-runtime-coherence-gate.ps1 -TargetRoot "$env:USERPROFILE\.codex"`
- `pwsh -File .\scripts\governance\phase-end-cleanup.ps1 -WriteArtifacts`

Success criteria:

1. 新 bootstrap 命令可执行。
2. `check.ps1 -Deep` 可执行且输出明确的 readiness classification。
3. 文档入口与脚本实现一致。
4. phase-end cleanup 后 repo cleanliness 不退化。
5. 不新增 runtime contract 回归。

## Proof Standard

只有当以下条件同时成立，才算本计划闭环：

1. 单命令 bootstrap 存在且可跑通。
2. 深度 doctor 明确区分自动化完成项与人工待完成项。
3. MCP active profile 物化成功。
4. 基础 check 与 deep check 都通过。
5. phase-end cleanup 后没有引入新的脏工作区或临时文件泄漏。
