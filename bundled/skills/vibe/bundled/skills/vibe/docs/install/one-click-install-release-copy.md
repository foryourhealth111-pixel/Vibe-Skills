# 一键安装发布文案

这份文档是给普通用户、围观用户、社区帖、README 首屏、发布帖直接复用的。

当前对外推荐版本：[`v2.3.40`](../releases/v2.3.40.md)

它比 operator 文档更短、更适合传播，但不会夸大能力边界。

适合人群：

- 想先把 VibeSkills 用起来的普通重度大模型用户
- 想低成本围观、评估、再决定是否推广给团队的负责人
- 想发社区帖、发 README 首屏、发群公告的人

## 一句话版本

`VibeSkills v2.3.40` 是当前推荐的对外版本。它不是另一个 skills 列表，而是一套把 skills 路由、治理、组合、验证起来的通用基座，让通用大模型更稳定地完成任务。先来用，先来围观，觉得方向对就先 Star。

## 社区短版文案

VibeSkills `v2.3.40` 现在是当前推荐的公开版本。

如果你是重度 AI 用户，这是现在最适合上手的一版：

- 一条受治理的推荐安装路径
- Windows / Linux 都有清晰入口
- `scrapling` 已进入默认 full lane
- `Cognee` 被明确定位为默认长期增强层
- `Composio / Activepieces` 作为外部操作能力预留，但保持 setup-required

它不是“什么都自动装好”的神话版本，而是当前最清晰、最诚实、最适合普通用户开始体验的 repo-governed 安装面。

先来用，先来围观，觉得这套方向值得做大，就先 Star。

## 发布长版文案

VibeSkills `v2.3.40` 是当前对外推荐版本。

这一版的重点不是再堆更多零散 skills，而是把“普通用户如何真正开始用”这件事讲清楚：

- 当前推荐版本被明确标出来
- 标准推荐安装路径更清楚
- Windows 和 Linux 都有可见入口
- 默认增强层和外部操作层的边界更清楚

你应该期待的是：

- 一次性 bootstrap repo 负责交付的内容
- 一次 truth-first 的 doctor / readiness 结果
- 清楚知道哪些部分已经闭环，哪些部分还属于宿主侧手工 provision

你不应该期待的是：

- 明明缺 host plugins / provider secrets，还被包装成 fully ready
- 所有外部 MCP 和宿主插件都被静默自动装好

如果你要的不是另一个 skills 仓库，而是一套更稳定、更可治理、更适合长期演进的 skills 基座，就从 `v2.3.40` 开始。

## 复制给 AI 助手的一键安装提示词

```text
请按当前平台的最强推荐 VibeSkills 安装路径帮我完成安装。

要求：
1. 先识别当前系统是 Windows 还是 Linux。
2. 如果是 Windows，优先执行：
   - `pwsh -File .\scripts\bootstrap\one-shot-setup.ps1`
   - `pwsh -File .\check.ps1 -Profile full -Deep`
   - 只有在 `pwsh` 不可用时才回退到 Windows PowerShell
3. 如果是 Linux，执行：
   - `bash ./scripts/bootstrap/one-shot-setup.sh`
   - `bash ./check.sh --profile full --deep`
   - 并明确告诉我当前 Linux 是否具备 `pwsh`，因为没有 `pwsh` 的 Linux 只应被视为 degraded-but-supported，而不是最强 full lane
4. 如实报告最终 `readiness_state`。
5. 不要把 host plugins、外部 MCP、provider secrets 伪装成已经自动安装完成。
6. 如果结果是 `manual_actions_pending`，把剩余人工动作明确列出来。
7. 默认先建议我补 `superpowers` 和 `hookify`，不要默认要求第一天就把 5 个宿主插件全部装满。
```

## 直接命令版

Windows：

```powershell
pwsh -File .\scripts\bootstrap\one-shot-setup.ps1
pwsh -File .\check.ps1 -Profile full -Deep
```

Linux：

```bash
bash ./scripts/bootstrap/one-shot-setup.sh
bash ./check.sh --profile full --deep
```

## 必须说清楚的现实边界

对外传播时，最重要的一句边界说明是：

- `v2.3.40` 是当前推荐的受治理安装面
- 它尽可能闭环 repo 自己负责交付的安装链路
- 它不会假装替你自动完成所有宿主插件、provider secrets、外部 MCP 集成

因此，对普通用户来说，`manual_actions_pending` 是一个正常、诚实、可接受的结果，不应该被误读成安装失败。

## 如果用户想继续增强

- 先补 provider secrets，例如 `OPENAI_API_KEY`
- 再补推荐的宿主插件，优先 `superpowers`、`hookify`
- 再补 `github`、`context7`、`serena` 等 plugin-backed MCP surfaces
- 把 `Composio / Activepieces` 视为外部操作能力扩展层，有需要再 setup，并保持治理与确认门禁

## 相关文档

- [`recommended-full-path.md`](./recommended-full-path.md)
- [`full-featured-install-prompts.md`](./full-featured-install-prompts.md)
- [`../cold-start-install-paths.md`](../cold-start-install-paths.md)
- [`../releases/v2.3.40.md`](../releases/v2.3.40.md)
