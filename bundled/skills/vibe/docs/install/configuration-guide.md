# 配置指南

这份指南只澄清一件事：安装完成后，怎样把 AI 治理 advice 的在线配置补齐。

## 先分清两件事

- `本地安装完成`：脚本或复制动作已经把 VibeSkills 放进目标宿主根目录。
- `AI 治理 online-ready`：路由里的 advice 在线调用已经拿到本地凭据、模型名和可用的 provider 地址。

前者成立，不代表后者也成立。

## 快速检查实际读取哪里

当前快速检查会优先读取：

1. `<target-root>/settings.json` 里的 `env`
2. 当前 shell / process environment

也就是说：

- 如果宿主本地维护 `settings.json`，优先把变量放到那个 `env`
- 如果宿主不走这个文件面，或者你只是先做连通性验证，也可以先放到本地环境变量

不要把密钥贴到聊天里。

## 推荐路径 1：OpenAI-compatible

这是当前最常见、也最推荐的 AI 治理 online 配置路径。

### 推荐键名

```json
{
  "env": {
    "OPENAI_API_KEY": "<local-api-key>",
    "OPENAI_BASE_URL": "https://api.openai.com/v1",
    "VCO_RUCNLPIR_MODEL": "gpt-5.4-high"
  }
}
```

说明：

- `OPENAI_API_KEY`：必需
- `OPENAI_BASE_URL` 或 `OPENAI_API_BASE`：可选；不填时按 provider 默认值或策略配置处理
- `VCO_RUCNLPIR_MODEL`：推荐模型键名

## 当前公共口径

安装后做本地配置与快速检查时，当前公共安装口径统一使用：

- `OPENAI_API_KEY`
- 可选 `OPENAI_BASE_URL` / `OPENAI_API_BASE`
- `VCO_RUCNLPIR_MODEL`

## 内置治理层的 provider 边界

当前内置 AI 治理层只支持 OpenAI-compatible 接入。

这表示：

- advice 在线调用按 OpenAI-compatible Responses / Chat Completions / Embeddings 语义工作
- 安装说明、bootstrap 和快速检查不再给出 Ark-compatible 作为内置并行入口
- 如果你要走别的 provider 形态，不属于当前内置治理层的标准支持面

## 高级路径：策略文件里直接指定 provider

如果你已经在仓库策略里维护 provider，也可以继续保留：

- `config/llm-acceleration-policy.json` 的 `provider.base_url`
- `config/llm-acceleration-policy.json` 的 `provider.model`

这种情况下：

- base URL / model 可以来自策略文件
- 本地凭据仍建议放在 `OPENAI_API_KEY`

## 不同宿主通常放哪里

### Codex

- 目标根目录：`~/.codex`
- 常见位置：`~/.codex/settings.json` 的 `env`

### Claude Code

- 目标根目录：`~/.claude`
- 常见位置：`~/.claude/settings.json` 的 `env`

### Cursor

- 目标根目录：`~/.cursor`
- 常见位置：`~/.cursor/settings.json` 的 `env`

### Windsurf

- 目标根目录：`~/.codeium/windsurf`
- 如果宿主侧没有直接使用 `<target-root>/settings.json`，就在本地环境变量里配置再做检查

### OpenClaw

- 目标根目录：`OPENCLAW_HOME` 或 `~/.openclaw`
- 如果宿主侧没有直接使用 `<target-root>/settings.json`，就在本地环境变量里配置再做检查

### OpenCode

- 目标根目录：`OPENCODE_HOME` 或 `~/.config/opencode`
- 如果宿主侧没有直接使用 `<target-root>/settings.json`，就在本地环境变量里配置再做检查

## 快速检查命令

在仓库根目录运行：

### Windows

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\verify\vibe-router-ai-connectivity-gate.ps1 -TargetRoot "<目标宿主根目录>" -WriteArtifacts
```

如果本机已经安装了 PowerShell 7，也可以改成 `pwsh`。

### Linux / macOS

```bash
python3 ./scripts/verify/runtime_neutral/router_ai_connectivity_probe.py --target-root "<目标宿主根目录>" --write-artifacts
```

常见默认根目录：

- `codex` -> `~/.codex`
- `claude-code` -> `~/.claude`
- `cursor` -> `~/.cursor`
- `windsurf` -> `~/.codeium/windsurf`
- `openclaw` -> `~/.openclaw`
- `opencode` -> `~/.config/opencode`

## 结果怎么看

- `ok`：AI 治理 advice 已连通
- `missing_credentials`：缺本地密钥，优先补 `OPENAI_API_KEY`
- `missing_model`：缺模型名，优先补 `VCO_RUCNLPIR_MODEL`
- `missing_base_url`：需要补 provider base URL，或在策略文件里补 `provider.base_url`
- `provider_rejected_request`：密钥、模型名或 endpoint 兼容性有问题
- `provider_unreachable`：网络、DNS、base URL 可达性或超时有问题
- `prefix_required`：当前策略要求在 `/vibe` 显式作用域下再检查 advice

## 最短实践结论

如果你只想最快补齐常见 OpenAI-compatible 在线能力：

1. 在本地 `settings.json` 的 `env`，或本地环境变量里配置 `OPENAI_API_KEY`
2. 如有自定义网关，再补 `OPENAI_BASE_URL` 或 `OPENAI_API_BASE`
3. 配置 `VCO_RUCNLPIR_MODEL`
4. 跑一次快速检查

这样就够了。
