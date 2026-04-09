# Quick Start

如果你是第一次来到这个仓库，先不用把所有文档都看一遍。

按你现在的目的，直接走对应入口就可以。

## 我只想快速明白这是什么

先看：

- [`../README.md`](../README.md)

它会先告诉你这个项目是做什么的、解决什么问题，以及为什么它不是另一个普通 skills 仓库。

## 我想马上开始用

直接看：

- [`install/one-click-install-release-copy.md`](./install/one-click-install-release-copy.md)

这里的主入口不是一堆命令，而是一段可以直接复制给 AI 的安装提示词。

当前公开投影出来的宿主可见入口固定是这四个 wrapper：

- `vibe`
- `vibe-want`
- `vibe-how`
- `vibe-do`

如果宿主支持菜单化展示，它通常会把它们显示成这几种标签：

- `Vibe`
- `Vibe: What Do I Want?`
- `Vibe: How Do We Do It?`
- `Vibe: Do It`

它们都还是同一个 `vibe` governed runtime，只是默认停靠点不同：

- `vibe` / `Vibe`：走完整受管流程
- `vibe-want` / `Vibe: What Do I Want?`：先把目标、边界、验收标准说清楚，并冻结 requirement 后停止
- `vibe-how` / `Vibe: How Do We Do It?`：冻结 requirement 和 plan 后停止
- `vibe-do` / `Vibe: Do It`：执行完整流程，但不会跳过 requirement / plan

如果你希望提高执行强度，只用：

- `--l`
- `--xl`

不要再记 `vibe-l`、`vibe-xl` 这种组合入口，系统不支持这类别名。

如果你的目标宿主是 OpenCode，也可以直接看：

- [`install/opencode-path.md`](./install/opencode-path.md)

## 我想理解这个项目为什么会做出来

看：

- [`manifesto.md`](./manifesto.md)

这份文档不会再讲一大套宏大宣言，而是更直接地解释：这个项目是怎么从真实问题里长出来的，它坚持什么，也不想变成什么。

## 我已经是重度用户，想看更完整的安装说明

看这两份：

- [`install/recommended-full-path.md`](./install/recommended-full-path.md)
- [`cold-start-install-paths.md`](./cold-start-install-paths.md)
- [`install/opencode-path.md`](./install/opencode-path.md)

它们比公开入口更完整，也更偏 operator / heavy-user 视角。

## 我应该怎么理解 `VibeSkills` 和 `VCO`

最简单的理解是：

- `VibeSkills` 是你在公开入口里看到的项目名字
- `VCO` 是它背后的核心运行时

前者更像你要使用的整套系统，后者更像这套系统让 AI 按受管流程工作的核心骨架。

## 推荐阅读顺序

如果你不想走错路，建议顺序就是：

1. [`../README.md`](../README.md)
2. [`install/one-click-install-release-copy.md`](./install/one-click-install-release-copy.md)
3. [`manifesto.md`](./manifesto.md)

这三步读完，你基本就知道：它是什么、怎么开始、它为什么会是现在这个样子。
