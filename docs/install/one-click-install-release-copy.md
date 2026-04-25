# 安装 VibeSkills

这是对外公开的安装入口。第一次使用时，直接按默认选择：

- 宿主：你实际使用的 AI 客户端
- 动作：`install`
- 版本：`全量版本 + 可自定义添加治理`

## 开始前

你需要：

- PowerShell 7（`pwsh`），并确保 `pwsh` 在 `PATH` 中，用于完整 governed verification
- Python 3.10+（`python3` / `python`），用于 wrapper 驱动的安装面
- 能访问这个 GitHub 仓库

Linux 和 macOS 仍然可以使用 `bash` 安装入口。推荐安装 PowerShell 7，是因为完整验证面会用到它。

> 想自己运行命令？直接看 [`recommended-full-path.md`](./recommended-full-path.md)。本页是提示词安装路径。

## 先选三件事

| 选择 | 可选项 | 默认建议 |
|:---|:---|:---|
| 宿主 | `codex`、`claude-code`、`cursor`、`windsurf`、`openclaw`、`opencode` | 你正在用的客户端 |
| 动作 | `install`、`update` | `install` |
| 版本 | `全量版本 + 可自定义添加治理`、`仅核心框架 + 可自定义添加治理` | `全量版本 + 可自定义添加治理` |

公开版本映射：

- `全量版本 + 可自定义添加治理` -> `full`
- `仅核心框架 + 可自定义添加治理` -> `minimal`

普通用户直接选 `full`。只有你明确想先装轻量框架时，再选 `minimal`。

## 复制一段提示词

按你的动作和版本选择一份，然后粘贴到 AI 客户端里：

| 需求 | 提示词 |
|:---|:---|
| 第一次安装，推荐路径 | [`prompts/full-version-install.md`](./prompts/full-version-install.md) |
| 第一次安装，仅核心框架 | [`prompts/framework-only-install.md`](./prompts/framework-only-install.md) |
| 更新已有全量安装 | [`prompts/full-version-update.md`](./prompts/full-version-update.md) |
| 更新已有框架安装 | [`prompts/framework-only-update.md`](./prompts/framework-only-update.md) |

## 提示词会做什么

它会要求安装助手：

1. 先确认宿主和公开版本，再执行安装命令；
2. 默认安装到真实宿主根目录，比如 Codex 使用 `~/.codex`，这样安装后 `$vibe` 能直接发现；
3. 执行对应的 install 和 check；
4. 不要求你把密钥、URL 或 model 粘贴到聊天里；
5. 不引导配置暂未开放的内置在线增强能力；
6. 分开报告这些状态：`installed locally`、`vibe host-ready`、`mcp native auto-provision attempted`、每个 MCP 的 `host-visible readiness`、`online-ready`。

`$vibe` 或 `/vibe` 只说明 governed runtime 入口可用，**不等于 MCP 完成**，也不能证明每个 MCP 已经进入宿主原生 MCP 配置面。

## 需要时再看

- 不确定宿主根目录：[`../cold-start-install-paths.md`](../cold-start-install-paths.md)
- 想直接看命令：[`recommended-full-path.md`](./recommended-full-path.md)
- OpenClaw 细节：[`openclaw-path.md`](./openclaw-path.md)
- OpenCode 细节：[`opencode-path.md`](./opencode-path.md)
- 离线/手动安装：[`manual-copy-install.md`](./manual-copy-install.md)
- 安装后接自定义 Skills：[`custom-workflow-onboarding.md`](./custom-workflow-onboarding.md)
- 安装后配置边界：[`configuration-guide.md`](./configuration-guide.md)

## 卸载

使用仓库根目录下的卸载入口：

- Windows：`uninstall.ps1 -HostId <host>`
- Linux / macOS：`uninstall.sh --host <host>`

卸载只清理 Vibe 自己管理的内容，默认不会回滚宿主登录态、provider 凭证、插件状态或你自己维护的配置。
