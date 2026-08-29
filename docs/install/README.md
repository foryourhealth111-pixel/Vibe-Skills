# 简化安装

公开安装应从发布版本 zip 开始，不要直接从仓库 checkout 安装。下载当前的 [vibe-skills-4.1.0-public.zip](https://github.com/foryourhealth111-pixel/Vibe-Skills/releases/download/v4.1.0/vibe-skills-4.1.0-public.zip)，解压到受管 Skills 目录之外，然后从解压目录运行脚本。

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

要移除 VibeSkills，直接删除安装位置中的 `<SkillsDir>/vibe` 文件夹。

## 替换旧版本

删除原来的 `<SkillsDir>/vibe` 文件夹，再按上面的安装命令安装当前版本。

v4 不会自动安装或推荐 `chrome`、`chrome-devtools`、`playwright`、`context7` 或 `claude-flow` MCP。安装器也不会替用户修改这些 MCP 的主机配置。

安装器不会改 Codex、Claude 或 Agents 的设置，也不会写入系统提示词或命令包装文件。额外 skill 扫描目录由运行时配置管理：

- 用户级：`~/.vibeskills/skill-roots.json`
- 项目级：`<workspace>/.vibeskills/skill-roots.json`

仓库 checkout 安装只用于开发。
