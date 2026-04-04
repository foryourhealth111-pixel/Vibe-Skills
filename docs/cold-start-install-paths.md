# 冷启动安装路径

这份文档只回答冷启动阶段最重要的问题：当前支持哪个宿主，以及每个宿主最短的 truth-first 安装路径。

## 一句话结论

当前公开支持六个宿主：

- `codex`
- `claude-code`
- `cursor`
- `windsurf`
- `openclaw`
- `opencode`

其中：

- `codex`：strongest governed lane
- `claude-code`：supported install/use path with bounded managed closure
- `cursor`：preview-guidance path
- `windsurf`：runtime-core path
- `openclaw`：preview runtime-core adapter path
- `opencode`：preview-guidance adapter path；public docs 仍保留更薄的 direct install/check

其他宿主当前都不应被描述成“已支持安装”。

补充说明：`one-shot-setup.*` 现在是 registry-driven wrapper，可以覆盖当前六个宿主；只是 `opencode` 仍保留更薄的 direct install/check 作为默认命令路径。

## Codex

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host codex --profile full
bash ./check.sh --host codex --profile full --deep
```

你会得到：

- governed runtime payload
- 可选的 Codex 本地 settings / MCP guidance
- deep health check

你不会得到：

- hook 自动安装
- 自动完成治理 AI online readiness

## Claude Code

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host claude-code --profile full
bash ./check.sh --host claude-code --profile full --deep
```

你会得到：

- bounded managed `vibeskills` + write-guard hook surface
- install/check 对真实 `~/.claude/settings.json` 的增量合并与校验
- supported-with-constraints health check

你不会得到：

- full closure
- 覆盖真实 `~/.claude/settings.json`
- Claude 宿主更广泛插件 / MCP / 凭据面的自动代管

## Cursor

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host cursor --profile full
bash ./check.sh --host cursor --profile full --deep
```

你会得到：

- preview-guidance payload
- preview health check

你不会得到：

- full closure
- 覆盖真实 `~/.cursor/settings.json`
- Cursor host-native provider / MCP / hook closure

## Windsurf

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host windsurf --profile full
bash ./check.sh --host windsurf --profile full --deep
```

你会得到：

- shared runtime payload
- `~/.codeium/windsurf` 下的 runtime-core 安装结果
- `.vibeskills/host-settings.json` 与 `.vibeskills/host-closure.json`
- 只在显式调用 Vibe skill 时生效的 skill-only activation 路径

你不会得到：

- full closure
- 宿主侧本地配置文件的自动代管

## OpenClaw

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host openclaw --profile full
bash ./check.sh --host openclaw --profile full --deep
```

你会得到：

- shared runtime payload
- OpenClaw runtime-core 安装路径，默认目标根目录为 `OPENCLAW_HOME` 或 `~/.openclaw`
- `.vibeskills/host-settings.json` 与 `.vibeskills/host-closure.json`
- attach / copy / bundle 三路径口径：
  - attach：把已有 `OPENCLAW_HOME`（或 `~/.openclaw`）作为目标根目录进行接入与校验
  - copy：通过 install/check 入口把 runtime-core payload 复制到目标根目录
  - bundle：按 `dist/host-openclaw/manifest.json` 与 `dist/manifests/vibeskills-openclaw.json` 消费 runtime-core 分发清单
- 明确保持 host-managed 边界

你不会得到：

- full closure
- 自动代管 OpenClaw 宿主本地配置

## OpenCode

更薄的默认路径：

```bash
bash ./install.sh --host opencode --profile full
bash ./check.sh --host opencode --profile full
```

如果你想和其他宿主共用同一个 bootstrap wrapper，也可以：

```bash
bash ./scripts/bootstrap/one-shot-setup.sh --host opencode --profile full
bash ./check.sh --host opencode --profile full --deep
```

你会得到：

- preview-guidance adapter path
- runtime payload
- `.vibeskills/host-settings.json` 与 `.vibeskills/host-closure.json`
- `opencode.json.example`

你不会得到：

- 覆盖真实 `~/.config/opencode/opencode.json`
- 自动 plugin 安装
- 自动写入 provider 凭据
- 自动替你做 MCP 信任决策

后续动作：

- 默认目标根目录是 `OPENCODE_HOME`，否则是 `~/.config/opencode`
- 如果你要项目内隔离安装，改用 `--target-root ./.opencode`
- 继续看 [`install/opencode-path.md`](./install/opencode-path.md)

## 冷启动阶段必须守住的边界

- `HostId` / `--host` 决定宿主语义
- 当前公开支持面并不是“所有宿主都 full closure”
- 本地 provider 字段没配好时，不能说环境已 online ready
- 不要要求用户把密钥贴到聊天里
