# 简化安装

公开安装使用发布版本 zip。请从[最新稳定版 Release](https://github.com/foryourhealth111-pixel/Vibe-Skills/releases/latest) 下载名称以 `-public.zip` 结尾的安装包，解压到受管 Skills 目录之外，然后从解压目录运行脚本。

请使用 GitHub Release 页面为该资源显示的 SHA-256 校验下载后的 ZIP。

## 一种安装模型

VibeSkills 在所有 AI 应用中都使用同一份安装包和同一种目录结构：

1. 选择当前应用能够扫描的 `SkillsDir`。
2. 对这个目录运行 `install`。
3. 通过当前应用的 Skills 入口调用 `vibe`。

安装器始终把同一份运行时写入 `<SkillsDir>/vibe`。不同应用只会改变
`SkillsDir` 的路径和调用语法，不会选择另一份 VibeSkills 安装包或运行时。

默认目录是 `~/.agents/skills`。如果某个宿主或你自己的工作流需要别的 skills 目录，也可以显式传入，例如 `~/.codex/skills` 或 `~/.claude/skills`。

## 安装

```powershell
pwsh -NoProfile -File .\install.ps1 -SkillsDir "$HOME\.agents\skills"
pwsh -NoProfile -File .\check.ps1 -SkillsDir "$HOME\.agents\skills"
```

```bash
bash ./install.sh --skills-dir "$HOME/.agents/skills"
bash ./check.sh --skills-dir "$HOME/.agents/skills"
```

使用其他 Skills 目录时，只替换 `SkillsDir` 的值。安装内容和运行时保持完全一致。

安装后，受管目录是 `<SkillsDir>/vibe`。安装收据位于 `<SkillsDir>/vibe/.vibeskills/install-receipt.json`。

安装包必须包含根目录的 `SKILL.md`，打包清单也必须选择该入口文件。
缺少入口的安装或更新会在创建安装目录和准备文件事务前被拒绝，已有安装和用户文件保持原样。
修复源包后可以直接重试。安装收据必须登记 `SKILL.md`；缺少该记录时，检查、安装、更新和卸载都会拒绝处理。

收据登记的文件保持完整且内容未改变时，可以再次运行 `install`。
若登记文件已被修改或缺失，`install` 和 `update` 都会拒绝替换已有安装。
请先检查并保留本地修改，再重试安装或更新。
安装会在事务准备阶段，以及每次替换或删除文件前复核收据哈希。
请先停止其他程序对受管目录的写入；最终哈希检查与文件替换之间仍存在并发窗口。
应用文件变更时检测到冲突，事务会标记为 `conflicted`，保留用户的修改或删除状态，以及恢复日志和备份。
冲突解决前，安装、更新和卸载都会停止自动恢复。事务中较早处理的文件可能已被替换，
请先检查保留的恢复日志，再使用或修复该安装。

事务处于 `conflicted` 状态时，请完整保留 `<SkillsDir>/vibe` 目录及其中的备份，
以及 `<SkillsDir>/.vibeskills/vibe-install-state.json` 恢复日志。
检查冲突期间若需要可用的安装，可以选择另一个 `SkillsDir` 安装。恢复日志应与恢复证据一同保留。

`check` 只检查收据登记的文件是否仍然完整。
`check` 证明的是 `installed locally`。它不证明 `runtime coherent`，也不证明 `delivery accepted`。

## 更新已安装版本

先下载更新的已发布 ZIP，解压后，从新的发布目录对同一个 `SkillsDir` 运行：

```powershell
pwsh -NoProfile -File .\update.ps1 -SkillsDir "$HOME\.agents\skills"
pwsh -NoProfile -File .\check.ps1 -SkillsDir "$HOME\.agents\skills"
```

```bash
bash ./update.sh --skills-dir "$HOME/.agents/skills"
bash ./check.sh --skills-dir "$HOME/.agents/skills"
```

不要把新版本解压到受管目录 `<SkillsDir>/vibe` 里面。`update` 发现收据登记文件被修改时会拒绝覆盖。

## 移除

确认安装事务处于正常状态后，可以删除安装位置中的 `<SkillsDir>/vibe` 文件夹来移除 VibeSkills。
`conflicted` 事务应按上文保留目录、恢复日志和备份。

## 替换旧版本

确认安装事务处于正常状态后，可以删除原来的 `<SkillsDir>/vibe` 文件夹，再按上面的安装命令安装当前版本。
`conflicted` 事务应先保留现场并检查冲突。

v4 不会自动安装或推荐 `chrome`、`chrome-devtools`、`playwright`、`context7` 或 `claude-flow` MCP。安装器也不会替用户修改这些 MCP 的主机配置。

安装器不会改 Codex、Claude 或 Agents 的设置，也不会写入系统提示词或命令包装文件。额外 skill 扫描目录由运行时配置管理：

- 用户级：`~/.vibeskills/skill-roots.json`
- 项目级：`<workspace>/.vibeskills/skill-roots.json`

仓库 checkout 安装只用于开发。
