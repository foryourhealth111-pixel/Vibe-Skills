# OpenCode 安装与使用说明

## 为什么有这份专页

- 通用安装提示词同样可以安装 `opencode`
- 这份专页不是替代通用安装提示词，而是补充 OpenCode 宿主特有说明
- 单独拆出本页，是因为 OpenCode 还需要展开 direct install/check、默认目标根目录、项目内隔离安装、实际写入内容与宿主侧本地边界；这些内容如果全部塞进公共安装文档，会让多宿主安装入口变得过重

## 当前仓库会安装

- 仓库分发内容
- Vibe-Skills 技能内容
- OpenCode 命令包装器
- OpenCode agent 包装器
- `opencode.json` 示例配置

## 仍由宿主本地完成

- 真正的 `~/.config/opencode/opencode.json`
- provider 凭证
- plugin 安装
- MCP 信任决策

## 全局安装

Shell：

```bash
./install.sh --host opencode
./check.sh --host opencode
```

PowerShell：

```powershell
pwsh -NoProfile -File ./install.ps1 -HostId opencode
pwsh -NoProfile -File ./check.ps1 -HostId opencode
```

默认目标根目录：

- 若设置了 `OPENCODE_HOME`，使用该目录
- 否则使用 `~/.vibeskills/targets/opencode`

这里的默认目标根目录是隔离安装根，不等于真实宿主配置目录 `~/.config/opencode`。

默认示例省略 `--profile`，等价于 `full`。
如果你要安装“仅核心框架 + 可自定义添加治理”，请在 install/check 命令后显式追加 `--profile minimal`。

## 项目内安装

如果希望把安装结果隔离在项目内部：

```bash
./install.sh --host opencode --target-root ./.opencode
./check.sh --host opencode --target-root ./.opencode
```

PowerShell 对应参数为 `-TargetRoot .\.opencode`。
如果你要安装“仅核心框架 + 可自定义添加治理”，同样显式追加 `-Profile minimal`。

## 安装内容

当前安装会写入：

- `skills/**`
- `commands/*.md`
- `command/*.md`
- `agents/*.md`
- `agent/*.md`
- `opencode.json.example`

当前会同时写入 plural 和 singular 的 command/agent 目录，因为 OpenCode 官方配置文档以 plural 目录为主，同时说明 singular 目录仍保留向后兼容支持。

## 使用方式

安装后的推荐入口：

- `/vibe`
- `/vibe-implement`
- `/vibe-review`

也可以直接在对话里显式要求：

- `Use the vibe skill to plan this change.`
- `Use the vibe skill to implement the approved plan.`

安装后的自定义 agent：

- `vibe-plan`
- `vibe-implement`
- `vibe-review`

## 验证方式

先跑仓库自带健康检查：

```bash
./check.sh --host opencode
```

再跑专用 smoke verifier：

```bash
python3 ./scripts/verify/runtime_neutral/opencode_preview_smoke.py --repo-root . --write-artifacts
```

## 当前校验记录

仓库内置的 smoke verifier 已经在本地 OpenCode CLI `1.2.27` 上验证：

- `opencode debug paths` 能正确解析隔离的 OpenCode 根目录
- `opencode debug skill` 能识别安装后的 `vibe` skill
- `opencode debug agent vibe-plan` 能识别安装后的 agent

如果你需要查看更细的适配契约和 proof 信息，可继续看 `dist/*`、`adapters/*` 与 `docs/universalization/*`。
