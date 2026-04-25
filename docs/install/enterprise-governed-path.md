# 安装路径：企业治理（可审计 / 可复现 / 可回滚）

本路径用于团队/组织交付：不仅要“装好了”，还要 **能证明这次安装是什么、缺口是什么、谁负责补、如何回滚**。

对应分发面：

- `dist/manifests/vibeskills-codex.json`（Codex lane，supported-with-constraints）
- `dist/manifests/vibeskills-core.json`（contract layer）

补充说明：

- `opencode` 现在已有 preview adapter lane，但还不属于这份 enterprise-governed 主路径
- 如果组织要评估 OpenCode，请先从 [`opencode-path.md`](./opencode-path.md) 和对应 proof artifacts 开始，而不是把它当成 Codex 等价交付

并且必须遵守 `docs/universalization/platform-parity-contract.md` 的反过度承诺规则。

## 适合谁

- 平台工程 / DevOps / 内部 AI 基础设施维护者
- 需要把安装、验证、升级、回滚变成制度化流程的组织
- 需要对 host-managed surfaces 的缺口做责任划分与审计的团队

## 企业路径的核心原则（truth-first）

1. 固定版本边界：不要把 `main` 当成可投产交付物。
2. 记录证据：每次安装必须保存可回看的输出（日志 / 状态 / 版本信息）。
3. 分离责任：repo-governed surfaces 的闭环与 host-managed surfaces 的 provision 必须拆开验收。
4. 平台不等价：Windows 权威 lane 与 Linux/macOS 降级 lane 必须写进交付口径。

## 推荐执行顺序（Codex lane）

### Step 0：记录版本与环境信息

```powershell
git rev-parse HEAD
git status -sb
```

### Step 1：执行推荐满血安装与 deep check

Windows：

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
```

Linux/macOS：

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

> 重要：Linux/macOS 若没有 `pwsh`，权威 PowerShell gates 可能无法执行，此时交付口径必须承认“降级”。

### Step 2：运行治理类 gate（建议在 Windows 或具备 pwsh 的 Linux 上）

```powershell
pwsh -File .\scripts\verify\vibe-version-consistency-gate.ps1
pwsh -File .\scripts\verify\vibe-offline-skills-gate.ps1
pwsh -File .\scripts\verify\vibe-version-packaging-gate.ps1
```

其中 `vibe-version-packaging-gate.ps1` 虽然保留 legacy 名称，但当前验证的是 canonical-only 打包治理与生成式兼容链路，而不是 repo-tracked mirror parity。

## Host-managed surfaces（必须纳入企业 checklist）

根据 `docs/universalization/host-capability-matrix.md` 与 `adapters/*/host-profile.json` 的口径，至少要把以下条目纳入你的内部 checklist，并明确 owner：

- 宿主侧插件是否启用、版本是否受控
- MCP 是否注册/授权完成（尤其是 plugin-backed MCP）
- provider secrets 的分发/轮换/权限策略
- 外部 CLI（node/npm/gh 等）是否在目标机器/镜像中一致

这些未完成时，最终状态合理地落在 `manual_actions_pending`；不要把它写成“已 fully ready”。

## Stop Rules（企业环境必须更严格）

- 出现 `core_install_incomplete`：立即停止推广
- 版本一致性 / 离线闭包 / 打包治理 gate 失败：立即停止升级并回滚
- 文档或对外口径把 `supported-with-constraints` / `preview` 说成 `full-authoritative`：立即撤回承诺并修订发布说明
