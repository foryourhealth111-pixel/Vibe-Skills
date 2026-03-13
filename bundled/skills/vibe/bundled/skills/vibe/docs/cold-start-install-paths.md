# 冷启动安装路径

这份文档是给第一次接触 `vco-skills-codex` 的用户和团队看的。

目标不是把所有人都推向同一条安装路径，而是先回答四个现实问题：

- 你只是想尽快跑起来，还是要尽量接近满血版
- 你是否能接受 `manual_actions_pending`
- 你是否已经具备宿主侧插件、MCP 和 provider secret 的 provision 能力
- 你当前是在个人机器、共享团队环境，还是企业治理环境中部署

如果你只记一句话：

`最小可用` 追求尽快跑通。  
`推荐满血` 追求仓库负责部分的完整闭环。  
`企业治理` 追求可审计、可复现、可回滚的长期交付。

## 路径一：最小可用

### 适合谁

- 第一次体验 VibeSkills 的普通用户
- 只想先看 VCO、router、docs 和本地 shipped payload 是否能跑起来的人
- 不准备在当前阶段补齐所有 host plugins / MCP / API keys 的人

### 目标

把仓库内负责的最小运行面安装起来，确认核心脚本和本地治理面可工作。

### 前置条件

- `git`
- `python3` 或 `python`
- Windows：`powershell` 或 `pwsh`
- Linux / macOS：`bash`

### 推荐命令

Windows：

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1 -SkipExternalInstall
```

Linux / macOS：

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --skip-external-install
```

### 你会得到什么

- shipped runtime payload 安装到目标 Codex 根目录
- active MCP profile 被物化
- 基础 doctor 流程被执行
- 你能知道缺的是“宿主侧能力”还是“仓库自身闭环”

### 你不要期待什么

- 不保证外部 CLI 已装好
- 不保证 plugin-backed MCP 已可用
- 不保证 online provider 已就绪

### 验收标准

- 安装命令退出码为 `0`
- `check.ps1` / `check.sh` 能跑完
- 如果缺 host plugins、MCP 或密钥，状态允许落在 `manual_actions_pending`
- 不应出现 `core_install_incomplete`

### Stop Rules

如果你只是第一次看仓库，到这里就可以停。

只有在你确认“仓库自身闭环没有问题”之后，才值得进入下一条路径。

## 路径二：推荐满血

### 适合谁

- 想真正把仓库负责的 shipped payload 和治理面一次性装全的重度用户
- 想要更完整 doctor / gate 结果的个人开发者
- 想进入“尽量接近满血体验”的团队负责人

### 目标

把仓库负责交付的内容全部安装、同步并验证完成，同时如实暴露剩余的宿主侧手工动作。

### 前置条件

- `git`
- `node` 和 `npm`
- `python3` 或 `python`
- Windows：`powershell` 或 `pwsh`
- Linux / macOS：`bash`
- Linux / macOS 强烈推荐额外安装 `pwsh`，这样可以进入权威 PowerShell doctor 路径

### 推荐命令

Windows：

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
```

Linux / macOS：

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

### 现实边界

这里的“满血版”是仓库治理意义上的满血，不是整个平台 magically fully ready。

仓库会尽量自动完成：

- shipped payload 安装
- bundled mirror 对齐
- MCP active profile 物化
- deep doctor 与 runtime coherence 检查
- 可脚本化的部分外部 CLI 安装

仓库不会伪装自动完成：

- host plugins 的平台侧 provision
- plugin-backed MCP 的宿主注册与授权
- 你的 `OPENAI_API_KEY` 等 provider secrets

### 验收标准

- 安装命令退出码为 `0`
- deep doctor 可执行完成
- repo-governed surfaces 不应出现虚假 warning 或假失败
- 如果仍缺宿主侧条件，最终状态允许是 `manual_actions_pending`
- 只有在所有宿主侧条件也补齐后，才应该追求 `fully_ready`

### 常见误判

- `claude-flow` 的 `npm install` 很慢，不等于挂了
- `npm` 的 deprecated warnings 很吵，不等于失败
- Linux / macOS 没有 `pwsh` 时出现 shell warning，不等于仓库闭环失败
- bootstrap 复用目标 `settings.json` 中已有 provider key 是正常行为，不是“配置丢失”

## 路径三：企业治理

### 适合谁

- 团队负责人
- 平台工程 / DevOps / 内部 AI 基础设施维护者
- 需要把安装、验证、升级、回滚变成制度化流程的组织

### 目标

不仅安装可用，还要做到：

- 安装路径可重复
- 版本边界清晰
- 手工动作可审计
- 升级与回滚可证明

### 推荐做法

1. 固定 release 版本，不要直接追 `main`
2. 在标准目标根目录执行 one-shot bootstrap
3. 运行 deep doctor，并保存输出 artifacts
4. 建立宿主侧 provision checklist
5. 只在 checklist 全部完成后，将环境标记为可投产

### 最低治理清单

- 记录当前使用的版本号与提交号
- 记录目标安装目录
- 记录安装命令与 doctor 命令
- 记录缺失的 host plugins、MCP、provider secrets
- 记录谁在什么时候完成了这些手工 provision

### 推荐验收命令

Windows：

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
pwsh -File .\scripts\verify\vibe-version-consistency-gate.ps1
pwsh -File .\scripts\verify\vibe-offline-skills-gate.ps1
pwsh -File .\scripts\verify\vibe-version-packaging-gate.ps1
```

Linux / macOS：

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

### 企业环境下的 stop rules

- 如果 `core_install_incomplete`，立即停止推广
- 如果版本一致性、离线闭包、打包治理 gate 失败，立即停止升级
- 如果宿主侧 provision 责任不清晰，不要宣称“团队已 ready”
- 如果没有产出可回看的 doctor artifacts，不要把这次安装当成正式交付

## 三条路径怎么选

| 你的目标 | 推荐路径 | 核心判断 |
| --- | --- | --- |
| 我只想先看它能不能跑 | 最小可用 | 接受 `manual_actions_pending` |
| 我想拿到仓库负责部分的完整闭环 | 推荐满血 | 能接受较慢安装与更完整校验 |
| 我要给团队或组织交付 | 企业治理 | 需要可审计、可复现、可回滚 |

## 安装后的统一判断口径

安装完成后，不要只问“命令有没有报错”。

你应该问：

- repo-governed surfaces 是否已经闭环
- deep doctor 是否明确给出了剩余人工动作
- 当前状态应该是 `fully_ready`、`manual_actions_pending`，还是 `core_install_incomplete`

这个判断口径，比“看起来差不多装好了”更重要。

## 相关入口

- [`../README.md`](../README.md)
- [`one-shot-setup.md`](./one-shot-setup.md)
- [`runtime-freshness-install-sop.md`](./runtime-freshness-install-sop.md)
- [`external-tooling/README.md`](./external-tooling/README.md)
