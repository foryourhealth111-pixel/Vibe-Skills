# 满血版安装提示词

这份文档给的是**可直接复制给 AI 编码助手 / Agent 的安装提示词**，目标是让用户更容易完成 VibeSkills 的“推荐满血版”安装。

注意边界：

- 这里的“满血版”指 **repo-governed full closure**。
- Windows 是当前最强参考路径。
- Linux 只有在宿主已具备 `pwsh` 时，才可进入当前权威满血路径。
- Linux 如果没有 `pwsh`，仍可安装和使用，但属于 `degraded-but-supported`，不应被表述成等价满血。

## 通用主提示词

适合：

- 用户不想自己判断平台命令
- 希望 Agent 自动识别 Windows / Linux
- 希望一次性执行 one-shot + doctor + 边界说明

直接复制：

```text
请你把当前仓库按 VibeSkills 推荐满血路径安装好，并严格遵守 truth-first 原则：

1. 先识别当前系统是 Windows 还是 Linux。
2. 如果是 Windows：
   - 优先使用 `pwsh -File .\scripts\bootstrap\one-shot-setup.ps1`
   - 然后执行 `pwsh -File .\check.ps1 -Profile full -Deep`
   - 如果 `pwsh` 不可用，再回退到 Windows PowerShell。
3. 如果是 Linux：
   - 先检查是否有 `pwsh`
   - 如果有 `pwsh`，执行 `bash ./scripts/bootstrap/one-shot-setup.sh`，然后执行 `bash ./check.sh --profile full --deep`
   - 并额外说明当前是 Linux 满血权威路径
   - 如果没有 `pwsh`，仍执行 `bash ./scripts/bootstrap/one-shot-setup.sh` 和 `bash ./check.sh --profile full --deep`
   - 但必须明确告诉我：当前结果属于 degraded-but-supported，不要宣称等价满血
4. 安装完成后，给我一个简洁结论：
   - 当前平台
   - 执行过的命令
   - 最终 readiness_state
   - 还缺哪些 host-managed surfaces
   - 是否已经达到当前平台可宣称的“推荐满血”
5. 不要把宿主插件、外部 MCP、provider secrets 伪装成已经自动装好。
6. 如果结果是 `manual_actions_pending`，请继续列出剩余人工动作，不要把它说成失败。
7. 如果需要补宿主插件，遵守当前默认策略：
   - 优先建议 `superpowers`、`hookify`
   - 不要默认要求第一次就安装 `everything-claude-code`、`claude-code-settings`、`ralph-loop`
8. 在整个过程中，不要修改仓库运行时逻辑；只做安装、检查、结论整理。
```

## Windows 满血安装提示词

适合：

- 用户明确在 Windows
- 想走当前最强参考路径

直接复制：

```text
请你把当前仓库按 Windows 推荐满血路径安装好。

要求：

1. 使用 `pwsh` 优先执行：
   - `pwsh -File .\scripts\bootstrap\one-shot-setup.ps1`
   - `pwsh -File .\check.ps1 -Profile full -Deep`
2. 如果 `pwsh` 不可用，再使用：
   - `powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap\one-shot-setup.ps1`
   - `powershell -ExecutionPolicy Bypass -File .\check.ps1 -Profile full -Deep`
3. 安装后告诉我：
   - readiness_state
   - 是否属于当前 Windows 参考满血路径
   - 哪些 host-managed surfaces 还需要手工 provision
4. 不要把宿主插件、provider secrets、plugin-backed MCP 伪装成自动完成。
5. 如果是 `manual_actions_pending`，请把剩余动作列成清单。
6. 宿主插件默认策略遵守：
   - 优先建议 `superpowers`、`hookify`
   - 不默认要求第一次就安装 `everything-claude-code`、`claude-code-settings`、`ralph-loop`
```

## Linux 满血安装提示词

适合：

- 用户明确在 Linux
- 希望 Agent 自己处理 `pwsh` 检查

直接复制：

```text
请你把当前仓库按 Linux 推荐满血路径安装好，并先判断当前 Linux 是否具备 `pwsh`。

要求：

1. 先检查 `pwsh` 是否可用。
2. 执行：
   - `bash ./scripts/bootstrap/one-shot-setup.sh`
   - `bash ./check.sh --profile full --deep`
3. 如果系统具备 `pwsh`，请明确告诉我：当前结果属于 Linux 满血权威路径候选。
4. 如果系统不具备 `pwsh`，请明确告诉我：
   - 当前结果只能算 degraded-but-supported
   - 不要把它说成与 Windows 满血等价
5. 安装后总结：
   - readiness_state
   - 是否仍有 host-managed surfaces 未补齐
   - 是否建议我继续补 `pwsh`
   - 是否建议我继续补宿主插件
6. 默认宿主插件策略遵守：
   - 优先建议 `superpowers`、`hookify`
   - 不默认要求第一次就安装 `everything-claude-code`、`claude-code-settings`、`ralph-loop`
7. 如果结果为 `manual_actions_pending`，列出剩余人工动作，不要把它说成安装失败。
```

## 新手简版提示词

如果你只是想让用户“一句话开装”，可以给这个短版本：

```text
请按当前平台的 VibeSkills 推荐满血路径帮我完成安装：
自动识别 Windows / Linux，运行 one-shot bootstrap 和 deep doctor，并严格区分 fully_ready、manual_actions_pending、core_install_incomplete。
不要伪装宿主插件、MCP、provider secrets 已自动装好；如果仍需人工动作，请列出清单。默认优先建议 `superpowers`、`hookify`，不要默认要求第一次就把其他 3 个宿主插件全装上。
```

## 给用户的话术建议

如果你准备把这段发到 README、Issue 模板或社区帖子里，建议配一行说明：

> 复制下面提示词给你的 AI 编码助手，它会按当前平台自动选择 Windows / Linux 安装路径，并如实报告还需要你手工 provision 的宿主面。

## 相关文档

- [`recommended-full-path.md`](./recommended-full-path.md)
- [`host-plugin-policy.md`](./host-plugin-policy.md)
- [`../one-shot-setup.md`](../one-shot-setup.md)
- [`../cold-start-install-paths.md`](../cold-start-install-paths.md)
