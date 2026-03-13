# 安装路径：推荐满血（repo-governed closure + 显式宿主边界）

本路径追求的是：**仓库负责部分的更完整闭环**（deep doctor / coherence / packaging 等），同时仍然保持 truth-first：宿主侧能力缺失时，必须允许落在 `manual_actions_pending`，不能把缺口藏起来。

对应分发面：`dist/manifests/vibeskills-codex.json`（当前最强 lane）+ `dist/manifests/vibeskills-core.json`。

## 适合谁

- 想拿到更完整的 doctor / gate 结果的个人开发者
- 想确认 shipped payload、bundled mirror、MCP profile 物化、deep check 等 repo-governed surfaces 是否一致的人
- 能接受安装过程更慢、更重（尤其涉及 node/npm、bundled 同步等）的用户

## 重要边界（避免“满血”被误读）

这里的“满血”是 **仓库治理意义上的满血**，不是“平台 magically fully ready”。

根据 `docs/universalization/host-capability-matrix.md` 与 `docs/universalization/platform-parity-contract.md`：

- Codex 是当前最强参考 lane，但仍然存在 host-managed surfaces
- Windows 是当前权威参考路径
- Linux/macOS 只有在具备 `pwsh` 并能跑 PowerShell gates 时，才可能接近权威；否则属于 **degraded-but-supported**（或 `not-yet-proven`）
- Claude Code 仍是 `preview`：不要把模板存在误读为“安装闭环已存在”

## 推荐命令（Codex lane）

### Windows（权威参考路径）

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
```

### Linux / macOS（bash 路径；无 pwsh 时属于降级）

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

> Truth-first 提示：
>
> - Linux/macOS 如果没有 `pwsh`，出现 “authoritative PowerShell gates skipped / warn_and_skip” 类提示是预期降级行为。
> - 不要把 “bash 能跑” 宣称为 “与 Windows 完全等价”。

## 你仍然需要宿主侧完成的事情（host-managed surfaces）

即使本路径执行成功，以下仍可能属于宿主侧 responsibility（不会被 repo 伪装为自动完成）：

- plugin provisioning / enablement
- MCP registration 与授权（尤其是 plugin-backed MCP surfaces）
- `OPENAI_API_KEY` 等 provider secrets 的安全存储与可用性
- 某些外部 CLI 的安装与版本治理（视宿主与平台而定）

当这些未完成时，最终状态允许是 `manual_actions_pending`。

## 何时不该走这条路

- 你在 Claude Code / Generic Host 上，并期望本仓库提供与 Codex 等价的安装闭环：目前不成立（参见对应 dist manifest 的 `status` 与 `anti_overclaim`）
- 你在 Linux/macOS 上但无法 provision `pwsh`，却希望拿到“权威 gate 全量通过”的结论：这会被平台合同视为过度承诺

