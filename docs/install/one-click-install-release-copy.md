# 提示词安装（默认推荐）

这是当前面向大多数用户的默认安装方式。

核心思路很简单：

1. 把下面这段提示词复制给你的 AI 助手
2. 让它先问你要安装到哪个代理
3. 再按对应代理选择正确的安装路径

## 复制给 AI 的提示词

```text
你现在是我的 VibeSkills 安装助手。
仓库地址：https://github.com/foryourhealth111-pixel/Vibe-Skills

在执行任何安装命令前，你必须先问我：
“你要把 VibeSkills 安装到什么代理里？可选：codex、claude-code、opencode、其他代理（generic）。”

规则：
1. 在我明确回答目标代理之前，不要开始安装。
2. 先判断当前系统是 Windows 还是 Linux / macOS，并使用对应命令格式。
3. 如果我选择 `codex`：
   - Linux / macOS 使用 `bash ./scripts/bootstrap/one-shot-setup.sh --host codex`
   - 然后执行 `bash ./check.sh --host codex --profile full --deep`
   - Windows 使用对应的 `pwsh` 命令。
4. 如果我选择 `claude-code`：
   - Linux / macOS 使用 `bash ./scripts/bootstrap/one-shot-setup.sh --host claude-code`
   - 然后执行 `bash ./check.sh --host claude-code --profile full --deep`
   - Windows 使用对应的 `pwsh` 命令。
   - 明确告诉我：这只是 preview scaffold，不是 full closure。
5. 如果我选择 `opencode`：
   - Linux / macOS 使用 `bash ./scripts/bootstrap/one-shot-setup.sh --host opencode`
   - 然后执行 `bash ./check.sh --host opencode --profile full --deep`
   - Windows 使用对应的 `pwsh` 命令。
   - 明确告诉我：这是 runtime-core 路径，不是宿主闭环。
6. 如果我选择“其他代理”或不在支持列表内：
   - 优先使用 `generic` lane，或者改为指导我走手动复制安装
   - 不要伪装成已经完成宿主级接入。
7. 对于 `claude-code`、`opencode`、`generic` 这些非 Codex lane，你必须先明确提醒我：
   - 需要我自己提供 `url`
   - 需要我自己提供 `apikey`
   - 需要我自己提供 `model`
   - 如果这三项没有明确提供，不能把环境描述成已完成 online readiness。
8. 安装完成后，请用简洁中文告诉我：
   - 目标代理
   - 实际执行的命令
   - 已完成的部分
   - 仍需我手动处理的部分
9. 不要把宿主插件、MCP 注册、provider 凭据伪装成已经自动完成。
```

## 这条路径适合谁

- 想让 AI 帮你判断安装路径的人
- 不想先研究 install matrix 的人
- 想先装起来，再看哪些能力还要自己补的人

## 这条路径会帮你做到什么

- 先确认目标代理，避免默认装错 lane
- 自动选择 `codex` / `claude-code` / `opencode` / `generic`
- 跑安装和检查命令
- 诚实告诉你哪些还是宿主侧工作

## 它不会假装替你完成什么

下面这些仍然可能是用户侧或宿主侧动作：

- 宿主插件 provision
- MCP 注册与授权
- `url` / `apikey` / `model` 填写
- 非 Codex lane 的宿主级闭环接入

## 第二条主路径

如果你不想让 AI 执行安装，或者当前环境离线、无管理员权限、宿主不在支持列表里，请改看：

- [`manual-copy-install.md`](./manual-copy-install.md)

## 高级参考

如果你要看更细的 lane truth 和高级安装边界，再看：

- [`recommended-full-path.md`](./recommended-full-path.md)
- [`../cold-start-install-paths.md`](../cold-start-install-paths.md)
