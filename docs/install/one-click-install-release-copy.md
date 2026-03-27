# 安装入口（唯一公开入口）

这是当前唯一公开安装入口。

普通用户只需要使用这一页。
这页会把你路由到保留的 4 份基础安装提示词文档。

## 先选两件事

1. 先确认宿主：`codex`、`claude-code`、`cursor`、`windsurf`、`openclaw`、`opencode`
2. 再确认动作与版本：
   - 安装：`全量版本 + 可自定义添加治理`
   - 安装：`仅核心框架 + 可自定义添加治理`
   - 更新：`全量版本 + 可自定义添加治理`
   - 更新：`仅核心框架 + 可自定义添加治理`

公开版本映射到：

- `全量版本 + 可自定义添加治理` -> `full`
- `仅核心框架 + 可自定义添加治理` -> `minimal`

## 复制对应提示词

这里保留 4 份基础提示词文档，覆盖安装 / 更新 与 full / minimal 四种场景。
除这 4 份外，其他页面都不再作为公开安装提示词入口。

- [`prompts/full-version-install.md`](./prompts/full-version-install.md)
- [`prompts/framework-only-install.md`](./prompts/framework-only-install.md)
- [`prompts/full-version-update.md`](./prompts/full-version-update.md)
- [`prompts/framework-only-update.md`](./prompts/framework-only-update.md)

## 需要时再继续看

- 宿主补充说明：
  - [`openclaw-path.md`](./openclaw-path.md)
  - [`opencode-path.md`](./opencode-path.md)
- 仅核心框架命令路径：
  - [`minimal-path.md`](./minimal-path.md)
- 更多安装命令和宿主细节：
  - [`recommended-full-path.md`](./recommended-full-path.md)
  - [`manual-copy-install.md`](./manual-copy-install.md)
  - [`host-plugin-policy.md`](./host-plugin-policy.md)
- 后续接自己的 workflow / skill：
  - [`custom-workflow-onboarding.md`](./custom-workflow-onboarding.md)
  - [`custom-skill-governance-rules.md`](./custom-skill-governance-rules.md)

## 关于补充配置

- 基础安装完成后即可直接使用
- 如果你还想补在线 provider、MCP、宿主本地 settings 或插件联动，这些都属于增强建议，不是基础安装的前置门槛
- 各宿主哪些内容仍由宿主侧本地维护，会在对应提示词和参考文档中如实说明

## 安装后如果要补 AI 治理在线配置，只按 OpenAI-compatible 这组键名

常见 OpenAI-compatible 路径：

- `OPENAI_API_KEY`
- 可选：`OPENAI_BASE_URL` 或 `OPENAI_API_BASE`
- `VCO_RUCNLPIR_MODEL`

补充说明：

- 内置 AI 治理层当前只支持 OpenAI-compatible 接入
- 当前安装说明不再把 `VCO_AI_PROVIDER_URL` / `VCO_AI_PROVIDER_API_KEY` 当成默认主路径
- 详细说明见 [`configuration-guide.md`](./configuration-guide.md)

## 安装后快速检查 AI 治理是否已配置好

如果你想快速确认“路由里的 AI 治理 advice 是否已经配通”，可以在仓库根目录运行：

- Windows：
  - `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-ai-connectivity-gate.ps1 -TargetRoot "<目标宿主根目录>" -WriteArtifacts`
- Linux / macOS：
  - `python3 ./scripts/verify/runtime_neutral/router_ai_connectivity_probe.py --target-root "<目标宿主根目录>" --write-artifacts`

如果你本机已经装了 PowerShell 7，也可以把 `powershell.exe` 换成 `pwsh`。

常见默认根目录：

- `codex` -> `~/.codex`
- `claude-code` -> `~/.claude`
- `cursor` -> `~/.cursor`
- `windsurf` -> `~/.codeium/windsurf`
- `openclaw` -> `~/.openclaw`
- `opencode` -> `~/.config/opencode`

结果说明：

- `ok`：AI 治理 advice 已连通
- `missing_credentials` / `missing_model`：本地配置还不完整
- `provider_rejected_request` / `provider_unreachable`：已经尝试在线调用，但当前没有成功
