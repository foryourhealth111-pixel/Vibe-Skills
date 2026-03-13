# 宿主插件安装策略

这份文档回答一个很实际的问题：

`vco-skills-codex` 到底哪些宿主插件应该默认安装，哪些不应该默认安装，哪些必须等到出现真实缺口再安装。

先说结论：

- 仓库不会假装自己能一键安装所有 `manual-codex` 插件。
- 第一次安装时，不建议把所有宿主插件一口气全装上。
- 默认策略应该是：先把 repo-governed surfaces 装好并跑完 doctor，再按缺口逐项补宿主插件。

## 先认清边界

当前 `config/plugins-manifest.codex.json` 里的以下插件都被标记为 `manual-codex`：

- `superpowers`
- `everything-claude-code`
- `claude-code-settings`
- `hookify`
- `ralph-loop`

这表示：

- 仓库可以报告这些面是否仍然缺失。
- 仓库可以为这些面准备兼容层、bundled mirror、fallback 技能或配置。
- 仓库**不能**诚实地宣称自己已经通过统一 shell 命令把这些宿主插件自动装好。

所以，这里给出的不是“伪自动安装方案”，而是一套**默认安装策略**。

## 我建议的默认策略

### 第一层：第一次安装默认不要求

第一次安装 VibeSkills 时，**不要把这 5 个宿主插件都视为前置必装项**。

先执行：

Windows:

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
```

Linux / macOS:

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

如果此时结果落在 `manual_actions_pending`，这是允许且诚实的。

### 第二层：作者级 / 参考 Windows Codex 环境，优先安装

如果你的目标不是“先跑起来”，而是“尽量接近作者参考环境”，我建议优先装：

- `superpowers`
- `hookify`

原因很简单：

- `superpowers` 更接近工作流硬门禁与开发习惯入口。
- `hookify` 更接近宿主侧 hook 执行与治理编排的承载面。

这两个面比另外三个更值得优先补齐。

### 第三层：先不要默认装，出现真实缺口再装

以下三个插件，我不建议在第一次安装时默认装上：

- `everything-claude-code`
- `claude-code-settings`
- `ralph-loop`

原因不是它们“没价值”，而是：

- 仓库里已经吸收或兼容了一部分相关能力。
- 它们更容易和现有 fallback、镜像、宿主已有配置产生重叠。
- 如果没有明确缺口，先装上只会增加冲突面与排障成本。

## 分项决策表

| 插件 | 默认策略 | 什么时候再装 | 为什么不建议第一次全装 |
| --- | --- | --- | --- |
| `superpowers` | 推荐安装 | 想进入作者级 / 参考 Codex 工作流时 | 价值高，冲突面相对可控 |
| `hookify` | 推荐安装 | 需要宿主级 hook 编排和 hook 治理时 | 价值高，但要避免多套 hook 规则并存 |
| `everything-claude-code` | 默认不装 | 明确缺失其上游插件原生能力时 | 容易和仓库已吸收能力重叠 |
| `claude-code-settings` | 默认不装 | 明确要把其上游 settings 面作为宿主权威层时 | 容易和现有本地 settings / fallback 混叠 |
| `ralph-loop` | 默认不装 | 明确需要上游 Ralph loop 原生工作流或后端时 | 仓库已有兼容 / fallback 面，先装收益不高 |

## 推荐安装路径

### 路径 A：普通用户默认路径

适合：

- 第一次试用 VibeSkills
- 先追求稳定、少冲突、好解释
- 愿意接受 `manual_actions_pending`

做法：

1. 不默认安装上述 5 个宿主插件。
2. 先跑 one-shot + deep doctor。
3. 只在 doctor 报出真实缺口，且你确实要用那项能力时，再补对应插件。

### 路径 B：Windows / Codex 参考环境路径

适合：

- 重度用户
- 作者级环境复现
- 希望尽量接近当前参考 lane

做法：

1. 先安装 `superpowers`
2. 再安装 `hookify`
3. 重跑 deep doctor
4. 只有当缺口仍然明确指向它们时，再考虑 `everything-claude-code`、`claude-code-settings`、`ralph-loop`

### 路径 C：问题驱动补装路径

适合：

- 已经能跑
- 不想引入额外重叠面
- 只对某个缺失能力补洞

做法：

1. 记录 doctor 报出的缺项。
2. 只补装与当前任务直接相关的插件。
3. 每安装一个，就重跑一次 doctor。
4. 不做“为了看起来完整”而一次性全装。

## 这些插件怎么安装

这里必须实话实说：

**当前仓库没有提供一条统一 shell 命令来安装这 5 个 `manual-codex` 插件。**

正确做法是：

1. 在你的 Codex 宿主环境中打开插件 / MCP / integration 管理入口。
2. 按插件名逐项 provision 或 enable。
3. 确认插件已在宿主侧启用，而不是只把文件拷到某个目录。
4. 回到仓库，重跑 deep doctor。

也就是说，安装说明的准确表述应当是：

- `superpowers`、`everything-claude-code`、`claude-code-settings`、`hookify`、`ralph-loop`
  通过 **Codex-native plugin / MCP tooling** 在宿主侧 provision。
- 本仓库只负责：
  - 暴露缺口
  - 提供兼容与 fallback
  - 在 doctor 报告里标出剩余人工动作

## 可脚本化安装的可选增强项

下面这些不是上面的 5 个宿主插件，但如果你要增强体验，可以按需安装：

### `claude-flow`

```bash
npm install -g claude-flow
```

### `xan`（Windows 推荐）

```powershell
scoop install xan
```

### `ivy`

```bash
pip install ivy
```

这些都属于**可选增强**，不是第一次安装的默认前置。

## 如何避免冲突

为了避免“装得越多越乱”，建议遵守下面几条：

1. 一次只新增一个宿主插件，然后立刻重跑 doctor。
2. 不要同时启用多套来源不清晰的 hook / settings / router 层。
3. 不要把“本地某台机器手工组装成功过”误当成“仓库通用默认策略”。
4. 如果某个能力仓库内已经有 bundled mirror 或 fallback，就先验证它是否已经够用，再决定要不要装上游宿主插件。

## 最终推荐

如果让我替一个新用户定默认策略，我会这样定：

- 默认不要求第一次就安装全部 5 个宿主插件。
- 推荐优先安装：`superpowers`、`hookify`
- 默认延后：`everything-claude-code`、`claude-code-settings`、`ralph-loop`
- 其余 MCP / CLI / provider secrets 全部按真实需求补齐

这套策略的目标不是“看起来最满”，而是：

- 冲突最少
- 解释最清楚
- 排障最容易
- 不夸大仓库实际自动化边界
