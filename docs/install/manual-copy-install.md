# 手动复制安装（离线 / 无管理员权限 / 其他代理）

这是当前第二条主安装路径。

适合这些情况：

- 你不想让 AI 直接执行安装命令
- 你的环境离线
- 你没有管理员权限
- 你的目标宿主不是 `codex` / `claude-code` / `opencode`
- 你只想先把 runtime-core 放进去，再自己接宿主

## 你会得到什么

手动复制安装得到的是 **runtime-core**，不是宿主闭环。

也就是说，你会得到：

- `skills/`
- `commands/`
- `config/upstream-lock.json`
- `config/skills-lock.json`（如果存在）
- `skills/vibe/` 这套 canonical runtime mirror

但你不会自动得到：

- 宿主插件 provision
- MCP 注册
- provider 凭据写入
- 宿主级 settings 闭环

## 手动复制步骤

假设目标目录是：`<TARGET_ROOT>`

1. 创建目标目录结构

```bash
mkdir -p <TARGET_ROOT>/skills <TARGET_ROOT>/commands <TARGET_ROOT>/config
```

2. 复制 runtime-core 技能

```bash
cp -R ./bundled/skills/. <TARGET_ROOT>/skills/
```

3. 复制命令目录

```bash
cp -R ./commands/. <TARGET_ROOT>/commands/
```

4. 复制锁文件

```bash
cp ./config/upstream-lock.json <TARGET_ROOT>/config/upstream-lock.json
cp ./config/skills-lock.json <TARGET_ROOT>/config/skills-lock.json
```

如果 `skills-lock.json` 不存在，就跳过它。

## 对其他代理最重要的一件事

如果你不是装到 `codex`，而是装到其他代理里，你必须自己补这 3 个值：

- `url`
- `apikey`
- `model`

如果这三项没有明确配置好，就不能把环境描述成“已完成 online readiness”。

## 给其他代理的最短提示词

你可以把下面这段放到目标代理的 system prompt / developer prompt 里：

```text
You are running with VibeSkills runtime-core.
Before claiming the environment is ready, check whether the user has explicitly provided:
- url
- apikey
- model
If any of them is missing, clearly remind the user to provide all three first.
Do not describe the environment as online-ready if they are missing.
```

## 什么时候不要走这条路

下面这些情况，优先走提示词安装：

- 你装的是 `codex`
- 你装的是 `claude-code`
- 你希望脚本自动做 install + check
- 你希望先由 AI 帮你判断 lane

对应主入口：

- [`one-click-install-release-copy.md`](./one-click-install-release-copy.md)
